--[[
    Luduan Audiobook Plugin - Synchronization Module
    Coordinates audio playback with highlighting and translation display
]]

local logger = require("logger")
local Device = require("device")

local Sync = {}
Sync.__index = Sync

-- Sync states
Sync.STATE_IDLE = "idle"
Sync.STATE_PLAYING = "playing"
Sync.STATE_PAUSED = "paused"
Sync.STATE_SEEKING = "seeking"
Sync.STATE_COMPLETE = "complete"

function Sync:new(audio_player, translator, highlighter)
    local obj = {
        state = self.STATE_IDLE,
        audio = audio_player,
        translator = translator,
        highlighter = highlighter,
        
        current_segment = nil,
        current_segment_index = 0,
        current_paragraph_index = 0,
        
        start_time = 0,
        end_time = 0,
        
        update_timer = nil,
        update_interval = 50,  -- ms
        
        callbacks = {
            on_segment_start = nil,
            on_segment_end = nil,
            on_position_update = nil,
            on_complete = nil,
            on_state_change = nil,
        },
    }
    setmetatable(obj, self)
    obj:_setup_audio_callbacks()
    return obj
end

function Sync:_setup_audio_callbacks()
    """Set up audio player callbacks."""
    if not self.audio then
        return
    end
    
    self.audio:set_callback("on_position", function(pos, duration)
        self:_on_position_update(pos, duration)
    end)
    
    self.audio:set_callback("on_complete", function()
        self:_on_segment_complete()
    end)
end

function Sync:play_segment(paragraph_index)
    """Play a specific paragraph segment."""
    logger.dbg("[Luduan Sync] Play segment:", paragraph_index)
    
    if not self.translator or not self.audio then
        logger.err("[Luduan Sync] Not initialized")
        return false
    end
    
    -- Get segment data
    local segment = self.translator:get_segment(paragraph_index)
    if not segment then
        logger.err("[Luduan Sync] Segment not found:", paragraph_index)
        return false
    end
    
    -- Store current segment info
    self.current_segment = segment
    self.current_segment_index = paragraph_index
    self.current_paragraph_index = paragraph_index
    self.start_time = segment.start_time or 0
    self.end_time = segment.end_time or 0
    
    -- Seek and play
    self.state = self.STATE_SEEKING
    self:_change_state(self.STATE_PLAYING)
    
    if self.audio:play(self.start_time) then
        logger.info("[Luduan Sync] Playing segment:", paragraph_index,
                    "Time:", self.start_time, "-", self.end_time)
        return true
    else
        logger.err("[Luduan Sync] Failed to play")
        self.state = self.STATE_IDLE
        return false
    end
end

function Sync:play_from_time(time_seconds)
    """Play from a specific time position."""
    logger.dbg("[Luduan Sync] Play from time:", time_seconds)
    
    local segment = self.translator:get_segment_by_time(time_seconds)
    if segment then
        local para_idx = segment.index or segment.paragraph_index
        return self:play_segment(para_idx)
    end
    
    -- No segment found, just play from time
    if self.audio:play(time_seconds) then
        self:_change_state(self.STATE_PLAYING)
        return true
    end
    
    return false
end

function Sync:pause()
    """Pause playback."""
    logger.dbg("[Luduan Sync] Pause")
    
    if self.audio:pause() then
        self:_change_state(self.STATE_PAUSED)
        return true
    end
    return false
end

function Sync:resume()
    """Resume playback."""
    logger.dbg("[Luduan Sync] Resume")
    
    if self.audio:resume() then
        self:_change_state(self.STATE_PLAYING)
        return true
    end
    return false
end

function Sync:toggle_play_pause()
    """Toggle between play and pause."""
    if self.state == self.STATE_PLAYING then
        return self:pause()
    else
        return self:resume()
    end
end

function Sync:stop()
    """Stop playback."""
    logger.dbg("[Luduan Sync] Stop")
    
    self.audio:stop()
    self:_change_state(self.STATE_IDLE)
    self:_clear_current_segment()
end

function Sync:seek_to_time(time_seconds)
    """Seek to a specific time."""
    logger.dbg("[Luduan Sync] Seek to:", time_seconds)
    
    if self.audio:seek(time_seconds) then
        return true
    end
    return false
end

function Sync:seek_relative(offset_seconds)
    """Seek relative to current position."""
    local current = self.audio:get_position()
    local new_pos = current + offset_seconds
    return self:seek_to_time(math.max(0, new_pos))
end

function Sync:play_next_segment()
    """Play the next segment."""
    local next_idx = self.translator:get_next_segment_index(self.current_segment_index)
    if next_idx ~= nil then
        return self:play_segment(next_idx)
    end
    return false
end

function Sync:play_prev_segment()
    """Play the previous segment."""
    local prev_idx = self.translator:get_prev_segment_index(self.current_segment_index)
    if prev_idx ~= nil then
        return self:play_segment(prev_idx)
    end
    return false
end

function Sync:get_current_position()
    """Get current playback position."""
    return self.audio:get_position()
end

function Sync:get_current_segment()
    """Get current segment data."""
    return self.current_segment
end

function Sync:get_state()
    """Get current sync state."""
    return self.state
end

function Sync:is_playing()
    """Check if currently playing."""
    return self.state == self.STATE_PLAYING
end

function Sync:_change_state(new_state)
    """Change sync state and notify callback."""
    if self.state ~= new_state then
        logger.dbg("[Luduan Sync] State change:", self.state, "->", new_state)
        self.state = new_state
        
        if self.callbacks.on_state_change then
            self.callbacks.on_state_change(new_state)
        end
    end
end

function Sync:_on_position_update(position, duration)
    """Handle position update from audio player."""
    -- Update current segment if time moved outside current segment
    if self.current_segment then
        if position > self.end_time then
            self:_on_segment_complete()
            return
        end
    end
    
    -- Notify position update
    if self.callbacks.on_position_update then
        self.callbacks.on_position_update(position, duration, self.current_segment)
    end
end

function Sync:_on_segment_complete()
    """Handle segment playback completion."""
    logger.dbg("[Luduan Sync] Segment complete")
    
    if self.callbacks.on_segment_end then
        self.callbacks.on_segment_end(self.current_segment)
    end
    
    self:_clear_current_segment()
    self:_change_state(self.STATE_IDLE)
end

function Sync:_clear_current_segment()
    """Clear current segment data."""
    self.current_segment = nil
    self.start_time = 0
    self.end_time = 0
end

function Sync:set_callback(event, callback)
    """Set a callback for an event."""
    if self.callbacks[event] ~= nil then
        self.callbacks[event] = callback
    end
end

-- Helper for highlighting during playback
function Sync:update_highlight(highlighter, paragraph_node)
    """Update highlight based on current position."""
    if not self.current_segment or not highlighter then
        return
    end
    
    -- Calculate progress within segment
    local pos = self.audio:get_position()
    local progress = (pos - self.start_time) / (self.end_time - self.start_time)
    progress = math.max(0, math.min(1, progress))
    
    -- Could use progress for partial highlighting effects
    -- For now, just ensure the paragraph is highlighted
    if paragraph_node then
        highlighter:highlight_paragraph(paragraph_node, {
            id = "sync_" .. tostring(self.current_paragraph_index),
        })
    end
end

return Sync
