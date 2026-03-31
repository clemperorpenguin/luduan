--[[
    Luduan Audiobook Plugin - Configuration Module
    Handles plugin settings and persistence
]]

local DataStore = require("datastore")
local logger = require("logger")

local Config = {}
Config.__index = Config

-- Default configuration
Config.DEFAULTS = {
    -- Playback settings
    auto_play = true,               -- Auto-play on tap
    playback_speed = 1.0,           -- Playback speed multiplier
    volume_boost = 1.0,             -- Volume boost multiplier
    bluetooth_only = false,         -- Only play over Bluetooth
    
    -- Display settings
    show_translation = true,        -- Show translation overlay
    translation_position = "bottom",-- "overlay", "bottom", "top"
    translation_opacity = 0.95,     -- Overlay opacity (0-1)
    font_size = 18,                 -- Translation font size
    font_family = "Noto Sans",      -- Font family
    
    -- Highlight settings
    enable_highlight = true,        -- Highlight current passage
    highlight_color = "#FFFF00",    -- Highlight color (yellow)
    highlight_opacity = 0.3,        -- Highlight opacity
    animate_highlight = true,       -- Pulse animation
    
    -- Language settings
    ui_language = "en",             -- UI language code
    preferred_translation = "en",   -- Preferred translation language
    
    -- TTS fallback
    tts_fallback = true,            -- Use TTS if no translation
    tts_voice = "default",          -- TTS voice name
    
    -- Behavior
    tap_to_pause = true,            -- Tap to pause/resume
    auto_scroll = true,             -- Auto-scroll to keep highlight in view
    close_on_complete = false,      -- Close overlay when segment ends
    show_progress_bar = true,       -- Show playback progress
    
    -- Advanced
    cache_manifest = true,          -- Cache manifest in memory
    preload_next_segment = false,   -- Preload next segment audio
    debug_mode = false,             -- Enable debug logging
}

function Config:new()
    local obj = {
        settings = {},
        store = DataStore:open("luduan.settings"),
    }
    setmetatable(obj, self)
    obj:load()
    return obj
end

function Config:load()
    -- Load from datastore or use defaults
    local saved = self.store:load()
    self.settings = {}
    
    -- Merge saved settings with defaults
    for key, value in pairs(self.DEFAULTS) do
        if saved and saved[key] ~= nil then
            self.settings[key] = saved[key]
        else
            self.settings[key] = value
        end
    end
    
    logger.dbg("[Luduan] Configuration loaded")
end

function Config:save()
    self.store:save(self.settings)
    logger.dbg("[Luduan] Configuration saved")
end

function Config:get(key)
    if self.settings[key] ~= nil then
        return self.settings[key]
    end
    return self.DEFAULTS[key]
end

function Config:set(key, value)
    self.settings[key] = value
    self:save()
end

function Config:reset()
    self.settings = {}
    for key, value in pairs(self.DEFAULTS) do
        self.settings[key] = value
    end
    self:save()
    logger.info("[Luduan] Configuration reset to defaults")
end

function Config:getAll()
    local result = {}
    for key, _ in pairs(self.DEFAULTS) do
        result[key] = self.settings[key]
    end
    return result
end

function Config:setAll(settings)
    for key, value in pairs(settings) do
        self.settings[key] = value
    end
    self:save()
end

-- Language helpers
Config.SUPPORTED_LANGUAGES = {
    { code = "en", name = "English", native = "English" },
    { code = "zh", name = "Chinese", native = "中文" },
    { code = "ja", name = "Japanese", native = "日本語" },
    { code = "vi", name = "Vietnamese", native = "Tiếng Việt" },
    { code = "ko", name = "Korean", native = "한국어" },
    { code = "ru", name = "Russian", native = "Русский" },
}

function Config:getLanguageName(code)
    for _, lang in ipairs(self.SUPPORTED_LANGUAGES) do
        if lang.code == code then
            return lang.name
        end
    end
    return code
end

function Config:getNativeLanguageName(code)
    for _, lang in ipairs(self.SUPPORTED_LANGUAGES) do
        if lang.code == code then
            return lang.native
        end
    end
    return code
end

return Config
