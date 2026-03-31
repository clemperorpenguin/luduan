--[[
    Luduan Audiobook Plugin - Main Entry Point
    KOReader plugin for synchronized audio playback with translations
]]

local logger = require("logger")
local UIManager = require("ui/uimanager")
local ReaderMenu = require("apps/reader/readermenu")
local DataStore = require("datastore")

-- Import plugin modules
local Config = require("config")
local AudioPlayer = require("audioplayer")
local Translator = require("translator")
local Highlighter = require("highlighter")
local Sync = require("sync")

-- Import language strings
local I18N = {}
setmetatable(I18N, {
    __index = function(t, key)
        return function(lang_code)
            local lang_file = "lang/" .. (lang_code or "en")
            local success, lang = pcall(require, lang_file)
            if success and lang[key] then
                return lang[key]
            end
            -- Fallback to English
            local en = require("lang/en")
            return en[key] or key
        end
    end
})

-- Plugin state
local Luduan = {
    enabled = false,
    initialized = false,
    config = nil,
    audio_player = nil,
    translator = nil,
    highlighter = nil,
    sync = nil,
    ui = nil,
    reader_view = nil,
    translation_panel = nil,
    control_panel = nil,
    current_book = nil,
    current_paragraph = nil,
    strings = nil,
}

-- Initialize plugin
function Luduan:init()
    logger.info("[Luduan] Initializing plugin")
    
    -- Load configuration
    self.config = Config:new()
    
    -- Load language strings
    local ui_lang = self.config:get("ui_language")
    self.strings = require("lang/" .. ui_lang)
    
    -- Initialize components
    self.audio_player = AudioPlayer:new()
    self.translator = Translator:new()
    
    logger.info("[Luduan] Plugin initialized")
    self.initialized = true
end

-- Enable plugin
function Luduan:enable()
    logger.info("[Luduan] Enabling plugin")
    
    if not self.initialized then
        self:init()
    end
    
    self.enabled = true
    self:_setup_gestures()
    self:_add_menu_items()
    
    -- Check for Luduan files in current book
    self:_check_current_book()
    
    logger.info("[Luduan] Plugin enabled")
end

-- Disable plugin
function Luduan:disable()
    logger.info("[Luduan] Disabling plugin")
    
    self.enabled = false
    self:_remove_gestures()
    self:_remove_menu_items()
    self:stop()
    
    logger.info("[Luduan] Plugin disabled")
end

-- Toggle enabled state
function Luduan:toggle()
    if self.enabled then
        self:disable()
    else
        self:enable()
    end
end

-- Check current book for Luduan files
function Luduan:_check_current_book()
    """Check if current book has Luduan audio files."""
    if not self.reader_view or not self.reader_view.document then
        return
    end
    
    local doc = self.reader_view.document
    local file_path = doc:getFilePath()
    if not file_path then
        return
    end
    
    -- Get book directory and base name
    local base_name = file_path:match("(.+)/[^/]+$")
    local dir_path = file_path:match("(.+)/[^/]+%.[^/]+$") or file_path:match("(.+)/[^/]+$")
    
    if not base_name or not dir_path then
        return
    end
    
    -- Look for Luduan files
    local manifest_path = dir_path .. "/" .. base_name .. ".audio.json"
    local audio_path = dir_path .. "/" .. base_name .. ".opus"
    
    logger.dbg("[Luduan] Checking for files:", manifest_path, audio_path)
    
    if file_exists(manifest_path) and file_exists(audio_path) then
        logger.info("[Luduan] Found Luduan files for:", base_name)
        self.current_book = base_name
        self:_load_luduan_files(manifest_path, audio_path)
    else
        logger.dbg("[Luduan] No Luduan files found")
        self.current_book = nil
    end
end

-- Load Luduan files
function Luduan:_load_luduan_files(manifest_path, audio_path)
    """Load Luduan manifest and audio files."""
    -- Load manifest
    if not self.translator:load_manifest(manifest_path) then
        self:_show_notification(self.strings.status_no_audio("en"))
        return
    end
    
    -- Load audio
    if not self.audio_player:load(audio_path) then
        self:_show_notification(self.strings.error_audio_load("en"))
        return
    end
    
    -- Initialize highlighter with UI
    if self.ui then
        self.highlighter = Highlighter:new(self.ui)
        
        -- Update highlight config
        self.highlighter:update_config({
            enabled = self.config:get("enable_highlight"),
            color = self.config:get("highlight_color"),
            opacity = self.config:get("highlight_opacity"),
            animate = self.config:get("animate_highlight"),
        })
    end
    
    -- Create sync manager
    self.sync = Sync:new(self.audio_player, self.translator, self.highlighter)
    
    -- Set up sync callbacks
    self.sync:set_callback("on_position_update", function(pos, duration, segment)
        self:_on_position_update(pos, duration, segment)
    end)
    
    self.sync:set_callback("on_segment_end", function(segment)
        self:_on_segment_end(segment)
    end)
    
    self.sync:set_callback("on_state_change", function(state)
        self:_on_state_change(state)
    end)
    
    -- Show ready notification
    self:_show_notification(self.strings.menu_enable("en"))
    
    -- Create UI panels
    if self.config:get("show_translation") then
        self:_create_translation_panel()
    end
    self:_create_control_panel()
end

-- Handle tap on passage
function Luduan:on_tap_paragraph(paragraph_index, paragraph_node)
    """Handle tap gesture on a paragraph."""
    logger.dbg("[Luduan] Tap on paragraph:", paragraph_index)
    
    if not self.enabled or not self.current_book then
        return false
    end
    
    self.current_paragraph = paragraph_index
    
    -- Check if translation exists
    if self.translator:has_translation(paragraph_index) then
        -- Play audio with translation
        if self.config:get("auto_play") then
            self:play_paragraph(paragraph_index, paragraph_node)
        else
            -- Just show translation
            self:_show_translation(paragraph_index)
            self:_highlight_paragraph(paragraph_node)
        end
    else
        -- No translation - use TTS mode
        if self.config:get("tts_fallback") then
            self:_tts_mode(paragraph_index, paragraph_node)
        else
            self:_show_notification(self.strings.status_no_translation("en"))
        end
    end
    
    return true
end

-- Play paragraph
function Luduan:play_paragraph(paragraph_index, paragraph_node)
    """Play audio for a paragraph."""
    logger.info("[Luduan] Play paragraph:", paragraph_index)
    
    -- Show translation
    self:_show_translation(paragraph_index)
    
    -- Highlight paragraph
    self:_highlight_paragraph(paragraph_node)
    
    -- Start playback
    if self.sync:play_segment(paragraph_index) then
        self:_update_status(self.strings.status_playing("en"))
    else
        self:_show_notification(self.strings.error_playback("en"))
    end
end

-- Stop playback
function Luduan:stop()
    """Stop current playback."""
    logger.dbg("[Luduan] Stop")
    
    if self.sync then
        self.sync:stop()
    end
    
    if self.audio_player then
        self.audio_player:stop()
    end
    
    self:_hide_translation_panel()
    self:_hide_control_panel()
    self:_clear_highlight()
    self:_update_status("")
end

-- Toggle play/pause
function Luduan:toggle_play_pause()
    """Toggle playback pause state."""
    if self.sync then
        self.sync:toggle_play_pause()
    end
end

-- Show translation for paragraph
function Luduan:_show_translation(paragraph_index)
    """Show translation in the panel."""
    if not self.translation_panel then
        return
    end
    
    local translation = self.translator:get_translation(paragraph_index)
    local original = self.translator:get_original_text(paragraph_index)
    
    if translation then
        self.translation_panel:set_text(translation, original)
        self.translation_panel:show()
    end
end

-- Highlight paragraph
function Luduan:_highlight_paragraph(paragraph_node)
    """Apply highlight to paragraph."""
    if self.highlighter and paragraph_node then
        self.highlighter:highlight_paragraph(paragraph_node, {
            id = "current_para",
        })
    end
end

-- Clear highlight
function Luduan:_clear_highlight()
    """Remove all highlights."""
    if self.highlighter then
        self.highlighter:clear_all()
    end
end

-- TTS mode (no translation available)
function Luduan:_tts_mode(paragraph_index, paragraph_node)
    """Handle TTS mode when no translation exists."""
    logger.info("[Luduan] TTS mode for paragraph:", paragraph_index)
    
    self:_update_status(self.strings.status_tts_mode("en"))
    self:_highlight_paragraph(paragraph_node)
    
    -- In a real implementation, this would use KOReader's TTS engine
    -- For now, just highlight the text
    self:_show_notification(self.strings.status_tts_mode("en"))
end

-- Position update callback
function Luduan:_on_position_update(pos, duration, segment)
    """Handle playback position update."""
    if self.translation_panel then
        self.translation_panel:update_progress(pos, duration)
    end
end

-- Segment end callback
function Luduan:_on_segment_end(segment)
    """Handle segment playback completion."""
    logger.dbg("[Luduan] Segment ended")
    
    self:_clear_highlight()
    
    if self.config:get("close_on_complete") then
        self:_hide_translation_panel()
    end
    
    self:_update_status(self.strings.status_stopped("en"))
end

-- State change callback
function Luduan:_on_state_change(state)
    """Handle sync state change."""
    if state == Sync.STATE_PLAYING then
        self:_update_status(self.strings.status_playing("en"))
    elseif state == Sync.STATE_PAUSED then
        self:_update_status(self.strings.status_paused("en"))
    elseif state == Sync.STATE_IDLE then
        self:_update_status("")
    end
end

-- Create translation panel
function Luduan:_create_translation_panel()
    """Create the translation display panel."""
    local Blitbuffer = require("fb")
    local Geom = require("geom")
    local Font = require("ui/font")
    local UIManager = require("ui/uimanager")
    local WidgetContainer = require("ui/widget/container/widgetcontainer")
    local VerticalGroup = require("ui/widget/verticalgroup")
    local HorizontalGroup = require("ui/widget/horizontalgroup")
    local TextBoxWidget = require("ui/widget/textboxwidget")
    local ProgressWidget = require("ui/widget/progresswidget")
    
    local font_size = self.config:get("font_size")
    local font = Font:getFont("cfont", font_size)
    
    -- Translation text box
    self.translation_text = TextBoxWidget:new{
        text = "",
        font = font,
        width = "100%",
        max_width = "100%",
        padding = 10,
        alignment = "left",
    }
    
    -- Original text box (smaller, optional)
    self.original_text = TextBoxWidget:new{
        text = "",
        font = Font:getFont("cfont", font_size - 2),
        width = "100%",
        max_width = "100%",
        padding = 5,
        alignment = "left",
        dimed = true,
    }
    
    -- Progress bar
    self.progress_bar = ProgressWidget:new{
        width = "100%",
        height = 4,
        percentage = 0,
    }
    
    -- Main panel
    self.translation_panel = WidgetContainer:new{
        layout = VerticalGroup:new{
            self.original_text,
            self.translation_text,
            self.progress_bar,
        },
        show = false,
    }
    
    -- Add to UI
    if self.ui then
        self.ui:insertWidget(self.translation_panel)
    end
end

-- Hide translation panel
function Luduan:_hide_translation_panel()
    """Hide the translation panel."""
    if self.translation_panel then
        self.translation_panel:hide()
        if self.ui then
            self.ui:removeWidget(self.translation_panel)
        end
    end
end

-- Create control panel
function Luduan:_create_control_panel()
    """Create the playback control panel."""
    local WidgetContainer = require("ui/widget/container/widgetcontainer")
    local HorizontalGroup = require("ui/widget/horizontalgroup")
    local ButtonWidget = require("ui/widget/buttonwidget")
    
    -- Control buttons
    local play_pause_btn = ButtonWidget:new{
        text = self.strings.control_pause("en"),
        callback = function()
            self:toggle_play_pause()
        end,
    }
    
    local stop_btn = ButtonWidget:new{
        text = self.strings.control_stop("en"),
        callback = function()
            self:stop()
        end,
    }
    
    local prev_btn = ButtonWidget:new{
        text = "◀",
        callback = function()
            if self.sync then
                self.sync:play_prev_segment()
            end
        end,
    }
    
    local next_btn = ButtonWidget:new{
        text = "▶",
        callback = function()
            if self.sync then
                self.sync:play_next_segment()
            end
        end,
    }
    
    local close_btn = ButtonWidget:new{
        text = "✕",
        callback = function()
            self:stop()
        end,
    }
    
    -- Control panel
    self.control_panel = WidgetContainer:new{
        layout = HorizontalGroup:new{
            prev_btn,
            play_pause_btn,
            stop_btn,
            next_btn,
            close_btn,
        },
        show = false,
    }
    
    -- Add to UI
    if self.ui then
        self.ui:insertWidget(self.control_panel)
    end
end

-- Hide control panel
function Luduan:_hide_control_panel()
    """Hide the control panel."""
    if self.control_panel then
        self.control_panel:hide()
        if self.ui then
            self.ui:removeWidget(self.control_panel)
        end
    end
end

-- Set up gestures
function Luduan:_setup_gestures()
    """Register tap gesture handler."""
    if self.reader_view then
        -- Hook into existing tap handler
        local original_tap = self.reader_view.onTap
        self.reader_view.onTap = function(view, tap)
            -- Check if tap is on a paragraph
            local para_index, para_node = self:_get_tapped_paragraph(tap)
            if para_index then
                if self:on_tap_paragraph(para_index, para_node) then
                    return true
                end
            end
            return original_tap(view, tap)
        end
    end
end

-- Remove gestures
function Luduan:_remove_gestures()
    """Remove gesture handlers."""
    -- Restore original handlers if needed
end

-- Get tapped paragraph
function Luduan:_get_tapped_paragraph(tap)
    """Get paragraph index and node from tap coordinates."""
    -- This requires integration with KOReader's DOM
    -- Simplified implementation
    if self.reader_view and self.reader_view.view then
        local page = self.reader_view.view:getCurrentPage()
        if page then
            -- Find node at tap position
            local node = page:getNodeFromPosition(tap.x, tap.y)
            if node then
                -- Get paragraph index (simplified)
                return 0, node
            end
        end
    end
    return nil, nil
end

-- Add menu items
function Luduan:_add_menu_items()
    """Add plugin menu items to reader menu."""
    if ReaderMenu then
        ReaderMenu:registerMenuOption({
            id = "luduan_toggle",
            text = self.strings.menu_enable("en"),
            callback = function()
                self:toggle()
            end,
        })
        
        ReaderMenu:registerMenuOption({
            id = "luduan_settings",
            text = self.strings.menu_settings("en"),
            callback = function()
                self:_show_settings()
            end,
        })
    end
end

-- Remove menu items
function Luduan:_remove_menu_items()
    """Remove plugin menu items."""
    if ReaderMenu then
        ReaderMenu:unregisterMenuOption("luduan_toggle")
        ReaderMenu:unregisterMenuOption("luduan_settings")
    end
end

-- Show settings dialog
function Luduan:_show_settings()
    """Show settings dialog."""
    -- Would create a settings dialog
    self:_show_notification("Settings (not implemented)")
end

-- Show notification
function Luduan:_show_notification(message)
    """Show a brief notification."""
    if UIManager then
        UIManager:show(Notification:new{
            text = message,
        })
    end
end

-- Update status
function Luduan:_update_status(message)
    """Update status bar message."""
    if self.ui and self.ui.status_bar then
        self.ui.status_bar:setMessage(message)
    end
end

-- Plugin cleanup
function Luduan:cleanup()
    """Clean up plugin resources."""
    logger.info("[Luduan] Cleanup")
    
    self:stop()
    
    if self.audio_player then
        self.audio_player:unload()
    end
    
    if self.translator then
        self.translator:unload()
    end
    
    self.initialized = false
end

-- Helper: Check if file exists
function file_exists(path)
    local file = io.open(path, "r")
    if file then
        file:close()
        return true
    end
    return false
end

-- Export plugin interface
return {
    name = "Luduan Audiobook",
    description = "Play synchronized audio with translations",
    init = function(ui, reader_view)
        Luduan.ui = ui
        Luduan.reader_view = reader_view
        return Luduan
    end,
    enable = function() Luduan:enable() end,
    disable = function() Luduan:disable() end,
    toggle = function() Luduan:toggle() end,
    cleanup = function() Luduan:cleanup() end,
}
