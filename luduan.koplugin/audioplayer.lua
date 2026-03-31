--[[
    Luduan Audiobook Plugin - Audio Player Module
    Handles Opus audio playback with precise timestamp seeking
]]

local logger = require("logger")
local Device = require("device")
local Sound = require("sound")

local AudioPlayer = {}
AudioPlayer.__index = AudioPlayer

-- Audio state constants
AudioPlayer.STATE_IDLE = "idle"
AudioPlayer.STATE_LOADING = "loading"
AudioPlayer.STATE_PLAYING = "playing"
AudioPlayer.STATE_PAUSED = "paused"
AudioPlayer.STATE_STOPPED = "stopped"
AudioPlayer.STATE_ERROR = "error"

function AudioPlayer:new()
    local obj = {
        state = self.STATE_IDLE,
        current_file = nil,
        current_position = 0,
        current_duration = 0,
        playback_speed = 1.0,
        volume = 1.0,
        sound_handle = nil,
        callbacks = {
            on_play = nil,
            on_pause = nil,
            on_stop = nil,
            on_seek = nil,
            on_complete = nil,
            on_error = nil,
            on_position = nil,
        },
        position_timer = nil,
    }
    setmetatable(obj, self)
    return obj
end

function AudioPlayer:load(file_path)
    """Load an audio file (Opus format)."""
    logger.dbg("[Luduan AudioPlayer] Loading:", file_path)
    
    self.state = self.STATE_LOADING
    
    -- Check if file exists
    if not file_exists(file_path) then
        logger.err("[Luduan AudioPlayer] File not found:", file_path)
        self.state = self.STATE_ERROR
        if self.callbacks.on_error then
            self.callbacks.on_error("file_not_found")
        end
        return false
    end
    
    self.current_file = file_path
    
    -- KOReader uses ffmpeg for audio decoding
    -- We'll use the Sound module which handles audio playback
    self.sound_handle = Sound:new{
        file = file_path,
        rate = 24000,  -- Qwen TTS sample rate
        channels = 1,  -- Mono
    }
    
    if not self.sound_handle:open() then
        logger.err("[Luduan AudioPlayer] Failed to open audio file")
        self.state = self.STATE_ERROR
        if self.callbacks.on_error then
            self.callbacks.on_error("audio_load_failed")
        end
        return false
    end
    
    -- Get duration
    self.current_duration = self.sound_handle:get_duration()
    self.current_position = 0
    
    self.state = self.STATE_IDLE
    logger.dbg("[Luduan AudioPlayer] Loaded:", file_path, 
               "Duration:", self.current_duration)
    return true
end

function AudioPlayer:play(start_time)
    """Start or resume playback, optionally seeking to start_time."""
    logger.dbg("[Luduan AudioPlayer] Play, start_time:", start_time)
    
    if not self.sound_handle then
        logger.err("[Luduan AudioPlayer] No audio loaded")
        return false
    end
    
    -- Seek to start position if specified
    if start_time and start_time > 0 then
        self:seek(start_time)
    end
    
    -- Start playback
    if self.sound_handle:play() then
        self.state = self.STATE_PLAYING
        self:_start_position_timer()
        
        if self.callbacks.on_play then
            self.callbacks.on_play()
        end
        
        logger.dbg("[Luduan AudioPlayer] Playing")
        return true
    else
        logger.err("[Luduan AudioPlayer] Play failed")
        self.state = self.STATE_ERROR
        return false
    end
end

function AudioPlayer:pause()
    """Pause playback."""
    logger.dbg("[Luduan AudioPlayer] Pause")
    
    if not self.sound_handle then
        return false
    end
    
    if self.sound_handle:pause() then
        self.state = self.STATE_PAUSED
        self:_stop_position_timer()
        
        if self.callbacks.on_pause then
            self.callbacks.on_pause()
        end
        
        logger.dbg("[Luduan AudioPlayer] Paused at:", self.current_position)
        return true
    end
    
    return false
end

function AudioPlayer:resume()
    """Resume playback from paused state."""
    logger.dbg("[Luduan AudioPlayer] Resume")
    
    if self.state ~= self.STATE_PAUSED then
        return self:play()
    end
    
    if self.sound_handle:resume() then
        self.state = self.STATE_PLAYING
        self:_start_position_timer()
        
        if self.callbacks.on_play then
            self.callbacks.on_play()
        end
        
        logger.dbg("[Luduan AudioPlayer] Resumed")
        return true
    end
    
    return false
end

function AudioPlayer:stop()
    """Stop playback and reset position."""
    logger.dbg("[Luduan AudioPlayer] Stop")
    
    if not self.sound_handle then
        return false
    end
    
    self.sound_handle:stop()
    self.state = self.STATE_STOPPED
    self.current_position = 0
    self:_stop_position_timer()
    
    if self.callbacks.on_stop then
        self.callbacks.on_stop()
    end
    
    logger.dbg("[Luduan AudioPlayer] Stopped")
    return true
end

function AudioPlayer:seek(time_seconds)
    """Seek to a specific time position."""
    logger.dbg("[Luduan AudioPlayer] Seek to:", time_seconds)
    
    if not self.sound_handle then
        return false
    end
    
    -- Clamp to valid range
    time_seconds = math.max(0, math.min(time_seconds, self.current_duration))
    
    if self.sound_handle:seek(time_seconds) then
        self.current_position = time_seconds
        
        if self.callbacks.on_seek then
            self.callbacks.on_seek(time_seconds)
        end
        
        logger.dbg("[Luduan AudioPlayer] Seeked to:", time_seconds)
        return true
    end
    
    return false
end

function AudioPlayer:set_speed(speed)
    """Set playback speed (0.5x - 2.0x)."""
    logger.dbg("[Luduan AudioPlayer] Set speed:", speed)
    
    self.playback_speed = math.max(0.5, math.min(2.0, speed))
    
    if self.sound_handle and self.sound_handle:set_speed then
        return self.sound_handle:set_speed(self.playback_speed)
    end
    
    return true
end

function AudioPlayer:set_volume(volume)
    """Set volume (0.0 - 1.0)."""
    logger.dbg("[Luduan AudioPlayer] Set volume:", volume)
    
    self.volume = math.max(0, math.min(1.0, volume))
    
    if self.sound_handle and self.sound_handle:set_volume then
        return self.sound_handle:set_volume(self.volume)
    end
    
    return true
end

function AudioPlayer:get_position()
    """Get current playback position in seconds."""
    if self.sound_handle then
        self.current_position = self.sound_handle:get_position() or self.current_position
    end
    return self.current_position
end

function AudioPlayer:get_duration()
    """Get total duration in seconds."""
    return self.current_duration
end

function AudioPlayer:get_remaining()
    """Get remaining time in seconds."""
    return math.max(0, self.current_duration - self.current_position)
end

function AudioPlayer:is_playing()
    """Check if currently playing."""
    return self.state == self.STATE_PLAYING
end

function AudioPlayer:is_paused()
    """Check if currently paused."""
    return self.state == self.STATE_PAUSED
end

function AudioPlayer:unload()
    """Unload audio and release resources."""
    logger.dbg("[Luduan AudioPlayer] Unload")
    
    self:_stop_position_timer()
    
    if self.sound_handle then
        self.sound_handle:close()
        self.sound_handle = nil
    end
    
    self.current_file = nil
    self.state = self.STATE_IDLE
end

function AudioPlayer:set_callback(event, callback)
    """Set a callback for an event."""
    if self.callbacks[event] ~= nil then
        self.callbacks[event] = callback
    end
end

function AudioPlayer:_start_position_timer()
    """Start timer to poll playback position."""
    self:_stop_position_timer()
    
    self.position_timer = Device:set_timeout(function()
        if self.state == self.STATE_PLAYING then
            local pos = self:get_position()
            
            -- Notify position update
            if self.callbacks.on_position then
                self.callbacks.on_position(pos, self.current_duration)
            end
            
            -- Check for completion
            if pos >= self.current_duration - 0.1 then
                self:_on_complete()
            else
                self:_start_position_timer()
            end
        end
    end, 100)  -- Poll every 100ms
end

function AudioPlayer:_stop_position_timer()
    """Stop position polling timer."""
    if self.position_timer then
        Device:clear_timeout(self.position_timer)
        self.position_timer = nil
    end
end

function AudioPlayer:_on_complete()
    """Handle playback completion."""
    logger.dbg("[Luduan AudioPlayer] Playback complete")
    
    self.state = self.STATE_STOPPED
    self:_stop_position_timer()
    
    if self.callbacks.on_complete then
        self.callbacks.on_complete()
    end
end

-- Check if Bluetooth is connected (for bluetooth_only mode)
function AudioPlayer:is_bluetooth_connected()
    """Check if Bluetooth audio is connected."""
    -- This would use platform-specific APIs
    -- For now, return false (plugin will handle this)
    return false
end

return AudioPlayer
