# Luduan KOReader Plugin

**Luduan Audiobook Plugin** - Synchronized audio playback with translations for KOReader.

## Features

- **Synchronized Playback** - Tap any paragraph to hear audio while seeing translation
- **Multi-language Support** - UI available in 6 languages
- **Bluetooth Audio** - Works seamlessly with Bluetooth headphones/speakers
- **TTS Fallback** - Text-to-speech for untranslated passages
- **Customizable** - Adjust highlight colors, playback speed, display options
- **Progress Tracking** - Visual progress bar during playback

## Supported Languages

| Code | Language | Native Name |
|------|----------|-------------|
| en | English | English |
| zh | Chinese | 中文 |
| ja | Japanese | 日本語 |
| vi | Vietnamese | Tiếng Việt |
| ko | Korean | 한국어 |
| ru | Russian | Русский |

## Installation

### Step 1: Copy Plugin

Copy the `luduan.koplugin` folder to your KOReader plugins directory:

```
# On device (Kobo/Kindle/PocketBook)
KOReader/.koreader/plugins/luduan.koplugin/

# Or via USB
/<device>/.koreader/plugins/luduan.koplugin/
```

### Step 2: Generate Audio Files

Use the Luduan desktop application to generate audio files for your EPUB:

```bash
cd /path/to/luduan
python main.py book.epub --language English
```

This creates:
- `book.opus` - Audio file
- `book.audio.json` - Synchronization manifest

### Step 3: Copy Audio Files

Copy the generated files to the same directory as your EPUB:

```
Books/
├── book.epub
├── book.opus
└── book.audio.json
```

### Step 4: Enable Plugin

1. Open KOReader
2. Open an EPUB with Luduan audio files
3. Tap menu → **Plugins** → **Luduan Audiobook** → **Enable**

## Usage

### Basic Playback

1. **Tap a paragraph** - Audio starts playing, translation appears
2. **Tap again** - Pause/resume playback
3. **Use control panel** - Navigate between paragraphs

### Control Panel

```
┌─────────────────────────────────────────┐
│  ◀  ⏯  ⏹  ▶  ✕                         │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
└─────────────────────────────────────────┘
```

| Button | Action |
|--------|--------|
| ◀ | Previous paragraph |
| ⏯ | Play/Pause |
| ⏹ | Stop |
| ▶ | Next paragraph |
| ✕ | Close player |

### Translation Display

When a paragraph has translation:
- Translation overlay appears
- Original text shown (dimmed)
- Progress bar shows playback position
- Current paragraph highlighted

### TTS Mode

When no translation exists:
- Paragraph highlighted during playback
- Uses KOReader's built-in TTS (if available)
- Status shows "TTS Mode"

## Settings

Access via **Menu** → **Plugins** → **Luduan** → **Settings**

### Playback

| Setting | Description | Default |
|---------|-------------|---------|
| Auto-play | Start on tap | On |
| Playback speed | 0.5× - 2.0× | 1.0× |
| Volume boost | Amplify audio | 1.0× |
| Bluetooth only | Only play via BT | Off |

### Display

| Setting | Description | Default |
|---------|-------------|---------|
| Show translation | Display translation | On |
| Position | Overlay/Bottom/Top | Bottom |
| Font size | Translation text | 18 |
| Opacity | Panel transparency | 95% |

### Highlighting

| Setting | Description | Default |
|---------|-------------|---------|
| Enable highlight | Highlight passage | On |
| Color | Highlight color | Yellow |
| Opacity | Highlight alpha | 30% |
| Animate | Pulse effect | On |

### Language

| Setting | Description | Default |
|---------|-------------|---------|
| UI Language | Interface language | English |
| Preferred translation | Translation language | English |
| TTS fallback | Use TTS if no translation | On |

## File Structure

```
luduan.koplugin/
├── _manifest.lua      # Plugin manifest
├── main.lua           # Main entry point
├── config.lua         # Configuration
├── audioplayer.lua    # Audio playback engine
├── translator.lua     # Translation lookup
├── highlighter.lua    # Text highlighting
├── sync.lua           # Synchronization
└── lang/
    ├── en.lua         # English strings
    ├── zh.lua         # Chinese strings
    ├── ja.lua         # Japanese strings
    ├── vi.lua         # Vietnamese strings
    ├── ko.lua         # Korean strings
    └── ru.lua         # Russian strings
```

## Troubleshooting

### No audio available
- Ensure `.opus` and `.audio.json` files are in the same directory as the EPUB
- Check file names match (e.g., `book.epub`, `book.opus`, `book.audio.json`)

### Translation not showing
- Verify the manifest contains `translated_text` for paragraphs
- Check "Show translation" is enabled in settings

### Audio not playing
- Ensure Bluetooth is connected (if "Bluetooth only" is enabled)
- Try restarting KOReader
- Check device volume settings

### Highlight not visible
- Enable "Highlight" in settings
- Adjust highlight color/opacity for better contrast
- Try different highlight type (Background/Underline/Glow)

## Advanced Usage

### Custom Highlight Colors

Edit `config.lua` or use settings dialog:

```lua
highlight_color = "#FFFF00"  -- Yellow
highlight_color = "#00FF00"  -- Green
highlight_color = "#0080FF"  -- Blue
```

### Keyboard Shortcuts

If your device supports hardware keys:

| Key | Action |
|-----|--------|
| Volume Up | Next paragraph |
| Volume Down | Previous paragraph |
| Power | Play/Pause |

### Manifest Format

The `.audio.json` format:

```json
{
  "version": "1.0",
  "book_title": "Book Name",
  "audio_file": "book.opus",
  "total_duration": 3600.5,
  "segments": [
    {
      "index": 0,
      "start_time": 0.0,
      "end_time": 5.2,
      "duration": 5.2,
      "text": "Original Chinese text...",
      "translated_text": "English translation...",
      "text_start": "First 50 characters..."
    }
  ]
}
```

## Contributing

Contributions welcome! Please submit pull requests to the main Luduan repository.

## Support

For issues or questions:
1. Check the main Luduan README
2. Review troubleshooting section above
3. Open an issue on GitHub
