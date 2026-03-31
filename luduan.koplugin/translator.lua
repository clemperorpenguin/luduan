--[[
    Luduan Audiobook Plugin - Translator Module
    Handles translation lookup and display from Luduan manifest
]]

local logger = require("logger")
local json = require("json")
local utf8 = require("utf8")

local Translator = {}
Translator.__index = Translator

function Translator:new()
    local obj = {
        manifest = nil,
        manifest_path = nil,
        book_name = nil,
        segments = {},
        segment_index = {},  -- Quick lookup by paragraph index
        current_segment = nil,
        callbacks = {
            on_translation_found = nil,
            on_translation_missing = nil,
            on_display_update = nil,
        },
    }
    setmetatable(obj, self)
    return obj
end

function Translator:load_manifest(manifest_path)
    """Load the Luduan audio manifest JSON."""
    logger.dbg("[Luduan Translator] Loading manifest:", manifest_path)
    
    if not file_exists(manifest_path) then
        logger.err("[Luduan Translator] Manifest not found:", manifest_path)
        return false
    end
    
    self.manifest_path = manifest_path
    
    -- Read and parse JSON
    local content = self:_read_file(manifest_path)
    if not content then
        return false
    end
    
    local success, data = pcall(json.decode, content)
    if not success then
        logger.err("[Luduan Translator] Failed to parse manifest:", data)
        return false
    end
    
    self.manifest = data
    self.book_name = data.book_title or "Unknown"
    
    -- Index segments for quick lookup
    self:_index_segments()
    
    logger.info("[Luduan Translator] Loaded manifest for:", self.book_name,
                "Segments:", #self.segments)
    return true
end

function Translator:_read_file(path)
    """Read file content."""
    local file = io.open(path, "r")
    if not file then
        return nil
    end
    
    local content = file:read("*all")
    file:close()
    return content
end

function Translator:_index_segments()
    """Build index for quick segment lookup."""
    self.segments = {}
    self.segment_index = {}
    
    if not self.manifest or not self.manifest.segments then
        return
    end
    
    for i, segment in ipairs(self.manifest.segments) do
        self.segments[i] = segment
        
        -- Index by paragraph index
        local para_idx = segment.index or segment.paragraph_index or i - 1
        self.segment_index[para_idx] = segment
    end
end

function Translator:get_segment(paragraph_index)
    """Get segment data for a paragraph index."""
    return self.segment_index[paragraph_index]
end

function Translator:get_segment_by_time(time_seconds)
    """Find segment that contains the given time."""
    if not self.segments then
        return nil
    end
    
    for _, segment in ipairs(self.segments) do
        if time_seconds >= segment.start_time and time_seconds <= segment.end_time then
            return segment
        end
    end
    
    return nil
end

function Translator:get_translation(paragraph_index)
    """Get translation text for a paragraph."""
    local segment = self:get_segment(paragraph_index)
    
    if segment then
        return segment.translated_text or segment.text
    end
    
    return nil
end

function Translator:get_original_text(paragraph_index)
    """Get original text for a paragraph."""
    local segment = self:get_segment(paragraph_index)
    
    if segment then
        return segment.text
    end
    
    return nil
end

function Translator:get_segment_times(paragraph_index)
    """Get start and end times for a paragraph."""
    local segment = self:get_segment(paragraph_index)
    
    if segment then
        return segment.start_time, segment.end_time, segment.duration
    end
    
    return nil, nil, nil
end

function Translator:has_translation(paragraph_index)
    """Check if translation exists for a paragraph."""
    local segment = self:get_segment(paragraph_index)
    return segment ~= nil and segment.translated_text ~= nil
end

function Translator:get_text_start(paragraph_index, max_length)
    """Get first N characters of text (for fuzzy matching)."""
    max_length = max_length or 50
    local segment = self:get_segment(paragraph_index)
    
    if segment then
        local text = segment.text_start or segment.text or ""
        return utf8.sub(text, 1, max_length)
    end
    
    return ""
end

function Translator:get_total_duration()
    """Get total audio duration."""
    if self.manifest and self.manifest.total_duration then
        return self.manifest.total_duration
    end
    
    -- Calculate from segments
    if #self.segments > 0 then
        local last = self.segments[#self.segments]
        return last.end_time or 0
    end
    
    return 0
end

function Translator:get_segment_count()
    """Get number of segments."""
    return #self.segments
end

function Translator:get_next_segment_index(current_index)
    """Get the next segment index."""
    if current_index < #self.segments - 1 then
        return current_index + 1
    end
    return nil
end

function Translator:get_prev_segment_index(current_index)
    """Get the previous segment index."""
    if current_index > 0 then
        return current_index - 1
    end
    return nil
end

function Translator:find_segment_by_text(search_text)
    """Find segment by matching text (fuzzy)."""
    if not self.segments then
        return nil
    end
    
    search_text = search_text:lower()
    
    for i, segment in ipairs(self.segments) do
        local text = (segment.text or ""):lower()
        local translated = (segment.translated_text or ""):lower()
        local text_start = (segment.text_start or ""):lower()
        
        -- Check for exact match or contains
        if text == search_text or translated == search_text then
            return segment, i
        end
        
        if text:find(search_text) or translated:find(search_text) 
           or text_start:find(search_text) then
            return segment, i
        end
    end
    
    return nil
end

function Translator:get_metadata()
    """Get manifest metadata."""
    if not self.manifest then
        return {}
    end
    
    return {
        book_title = self.manifest.book_title,
        source_file = self.manifest.source_file,
        audio_file = self.manifest.audio_file,
        language = self.manifest.language,
        created_at = self.manifest.created_at,
        version = self.manifest.version,
        segment_count = #self.segments,
        total_duration = self:get_total_duration(),
    }
end

function Translator:unload()
    """Unload manifest and free resources."""
    logger.dbg("[Luduan Translator] Unload")
    
    self.manifest = nil
    self.segments = {}
    self.segment_index = {}
    self.current_segment = nil
end

function Translator:set_callback(event, callback)
    """Set a callback for an event."""
    if self.callbacks[event] ~= nil then
        self.callbacks[event] = callback
    end
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

return Translator
