--[[
    Luduan Audiobook Plugin - Highlighter Module
    Handles text highlighting for synchronized passages
]]

local logger = require("logger")
local Draw = require("draw")
local Geom = require("geom")

local Highlighter = {}
Highlighter.__index = Highlighter

-- Highlight types
Highlighter.TYPE_UNDERLINE = "underline"
Highlighter.TYPE_BACKGROUND = "background"
Highlighter.TYPE_BORDER = "border"
Highlighter.TYPE_GLOW = "glow"

function Highlighter:new(ui)
    local obj = {
        ui = ui,
        highlights = {},
        animation_timer = nil,
        animation_phase = 0,
        config = {
            enabled = true,
            color = "#FFFF00",  -- Yellow
            opacity = 0.3,
            type = Highlighter.TYPE_BACKGROUND,
            animate = true,
            animation_speed = 0.1,  -- Seconds per frame
            border_width = 2,
            corner_radius = 4,
        },
    }
    setmetatable(obj, self)
    return obj
end

function Highlighter:highlight_paragraph(paragraph_node, options)
    """Apply highlight to a paragraph DOM node."""
    logger.dbg("[Luduan Highlighter] Highlight paragraph")
    
    if not self.config.enabled then
        return false
    end
    
    options = options or {}
    
    -- Get node position
    local node_pos = self:_get_node_position(paragraph_node)
    if not node_pos then
        logger.err("[Luduan Highlighter] Could not get node position")
        return false
    end
    
    -- Create highlight
    local highlight = {
        id = options.id or "para_" .. tostring(paragraph_node),
        area = node_pos,
        color = options.color or self.config.color,
        opacity = options.opacity or self.config.opacity,
        type = options.type or self.config.type,
        border_width = options.border_width or self.config.border_width,
        corner_radius = options.corner_radius or self.config.corner_radius,
        created_at = os.time(),
    }
    
    table.insert(self.highlights, highlight)
    
    -- Start animation if enabled
    if self.config.animate then
        self:_start_animation()
    end
    
    -- Request UI refresh
    self:_refresh_ui()
    
    logger.dbg("[Luduan Highlighter] Highlighted:", highlight.id)
    return true
end

function Highlighter:highlight_area(area, options)
    """Apply highlight to a specific rectangular area."""
    logger.dbg("[Luduan Highlighter] Highlight area")
    
    if not self.config.enabled then
        return false
    end
    
    options = options or {}
    
    local highlight = {
        id = options.id or "area_" .. tostring(#self.highlights),
        area = area,
        color = options.color or self.config.color,
        opacity = options.opacity or self.config.opacity,
        type = options.type or self.config.type,
        border_width = options.border_width or self.config.border_width,
        corner_radius = options.corner_radius or self.config.corner_radius,
    }
    
    table.insert(self.highlights, highlight)
    self:_refresh_ui()
    
    return true
end

function Highlighter:remove_highlight(id)
    """Remove a specific highlight by ID."""
    logger.dbg("[Luduan Highlighter] Remove highlight:", id)
    
    for i, highlight in ipairs(self.highlights) do
        if highlight.id == id then
            table.remove(self.highlights, i)
            self:_refresh_ui()
            return true
        end
    end
    
    return false
end

function Highlighter:clear_all()
    """Remove all highlights."""
    logger.dbg("[Luduan Highlighter] Clear all highlights")
    
    self.highlights = {}
    self:_stop_animation()
    self:_refresh_ui()
end

function Highlighter:update_config(new_config)
    """Update highlight configuration."""
    for key, value in pairs(new_config) do
        self.config[key] = value
    end
end

function Highlighter:set_color(color)
    """Set highlight color."""
    self.config.color = color
end

function Highlighter:set_opacity(opacity)
    """Set highlight opacity."""
    self.config.opacity = math.max(0, math.min(1, opacity))
end

function Highlighter:set_animate(enabled)
    """Enable/disable animation."""
    self.config.animate = enabled
    if not enabled then
        self:_stop_animation()
    end
end

function Highlighter:_get_node_position(node)
    """Get the screen position of a DOM node."""
    -- This requires integration with KOReader's DOM/View system
    -- The actual implementation depends on how KOReader exposes node positions
    
    if node and node.pos then
        return node.pos
    end
    
    -- Fallback: try to get from view
    if self.ui and self.ui.view then
        local view = self.ui.view
        if view and node then
            -- Try to find node in current page
            local page = view:getCurrentPage()
            if page and page.nodes then
                for _, n in ipairs(page.nodes) do
                    if n == node and n.pos then
                        return n.pos
                    end
                end
            end
        end
    end
    
    return nil
end

function Highlighter:_start_animation()
    """Start highlight animation loop."""
    if not self.config.animate then
        return
    end
    
    self:_stop_animation()
    
    local Device = require("device")
    self.animation_timer = Device:set_timeout(function()
        self:_animate_step()
    end, self.config.animation_speed * 1000)
end

function Highlighter:_stop_animation()
    """Stop highlight animation."""
    if self.animation_timer then
        local Device = require("device")
        Device:clear_timeout(self.animation_timer)
        self.animation_timer = nil
    end
    self.animation_phase = 0
end

function Highlighter:_animate_step()
    """Animation frame update."""
    self.animation_phase = self.animation_phase + 0.1
    
    -- Pulse effect: vary opacity
    local pulse = math.sin(self.animation_phase) * 0.1 + 0.9
    self:_refresh_ui()
    
    -- Continue animation
    if #self.highlights > 0 then
        self:_start_animation()
    end
end

function Highlighter:_refresh_ui()
    """Request UI refresh to redraw highlights."""
    if self.ui then
        -- Trigger a repaint
        if self.ui.widget and self.ui.widget.dirtynode then
            self.ui.widget:repaint()
        elseif self.ui.view and self.ui.view.onPageChanged then
            self.ui.view:onPageChanged()
        end
    end
end

function Highlighter:draw_highlight(widget, dc)
    """Draw highlights on the display context."""
    if not self.config.enabled or #self.highlights == 0 then
        return
    end
    
    for _, highlight in ipairs(self.highlights) do
        self:_draw_single_highlight(dc, highlight)
    end
end

function Highlighter:_draw_single_highlight(dc, highlight)
    """Draw a single highlight."""
    local area = highlight.area
    if not area then
        return
    end
    
    local color = highlight.color
    local opacity = highlight.opacity
    
    -- Apply animation pulse
    if self.config.animate and self.animation_timer then
        local pulse = math.sin(self.animation_phase) * 0.1 + 0.9
        opacity = opacity * pulse
    end
    
    if highlight.type == Highlighter.TYPE_BACKGROUND then
        -- Draw background highlight
        dc:fill({
            color = color,
            alpha = opacity,
            rect = area,
            radius = highlight.corner_radius,
        })
        
    elseif highlight.type == Highlighter.TYPE_UNDERLINE then
        -- Draw underline
        local underline_y = area.y0 + area.h - 2
        dc:fill({
            color = color,
            alpha = opacity,
            rect = Geom:new{
                x = area.x0,
                y = underline_y,
                w = area.w,
                h = highlight.border_width,
            },
        })
        
    elseif highlight.type == Highlighter.TYPE_BORDER then
        -- Draw border
        dc:stroke({
            color = color,
            alpha = opacity,
            rect = area,
            line_width = highlight.border_width,
            radius = highlight.corner_radius,
        })
        
    elseif highlight.type == Highlighter.TYPE_GLOW then
        -- Draw glow effect (multiple layered rectangles)
        for i = 3, 1, -1 do
            local glow_area = Geom:new{
                x = area.x0 - i * 2,
                y = area.y0 - i * 2,
                w = area.w + i * 4,
                h = area.h + i * 4,
            }
            dc:fill({
                color = color,
                alpha = opacity / i / 3,
                rect = glow_area,
                radius = highlight.corner_radius + i,
            })
        end
        -- Draw base highlight
        dc:fill({
            color = color,
            alpha = opacity,
            rect = area,
            radius = highlight.corner_radius,
        })
    end
end

return Highlighter
