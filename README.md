# Luduan - EPUB to Audiobook Pipeline

**Luduan** (鹿端) - A modular pipeline for converting EPUB books (especially Chinese web novels) into audiobooks with KOReader-compatible audio sidecar files.

## Features

- **Multi-phase architecture** - Translation and audio generation run independently with intermediate saves
- **VRAM-optimized** - Explicit memory management between phases for large files
- **Resume capability** - Continue from intermediate files if interrupted
- **KOReader compatible** - Generates `.audio.json` sidecar files for synchronized audio playback
- **Wuxia/Xianxia aware** - Preserves cultivation terminology in translations

## Project Structure

```
luduan/
├── main.py           # Main pipeline orchestrator (CLI)
├── gui.py            # PyQt6 graphical interface
├── config.py         # Configuration and paths
├── logger.py         # Logging and VRAM monitoring
├── parser.py         # EPUB text extraction
├── translator.py     # Qwen translation engine
├── audio_engine.py   # TTS and forced alignment
├── encoder.py        # Opus encoding and manifest generation
├── requirements.txt  # Python dependencies
├── requirements_gui.txt  # GUI dependencies
└── README.md         # This file
```

## Installation

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install core dependencies
pip install -r requirements.txt

# Install GUI dependencies (optional)
pip install -r requirements_gui.txt
```

## Configuration

Set environment variables or edit `config.py`:

```bash
export LUDUAN_INPUT_DIR="./input"
export LUDUAN_OUTPUT_DIR="./output"
export LUDUAN_CACHE_DIR="./cache"
export LUDUAN_TRANSLATION_MODEL="Qwen/Qwen2.5-7B-Instruct"
export LUDUAN_TTS_MODEL="Qwen/Qwen3-TTS-1.7B"
export LUDUAN_ALIGNER_MODEL="Qwen/Qwen3-ForcedAligner-0.6B"
```

## Usage

### Graphical Interface (GUI)

```bash
python gui.py
```

The GUI provides:
- File selection with drag-and-drop support
- Real-time progress and log viewing
- Settings dialog for configuration
- Batch processing queue
- System tray notifications

### Command Line

### Full Pipeline (Translate + Audio)

```bash
python main.py book.epub --language English
```

### Translation Only

```bash
python main.py book.epub --translation-only
```

### Audio Generation Only (from existing translation)

```bash
python main.py book.epub --audio-only
```

### Batch Processing

```bash
# Place EPUBs in input directory
python main.py --batch --input-dir ./epubs
```

## Output Files

For each processed book, generates:

- `{book_name}_translated_tome.json` - Intermediate translation (resume point)
- `{book_name}.opus` - Encoded audio file
- `{book_name}.audio.json` - KOReader sidecar manifest

## KOReader Integration

Copy the `.opus` and `.audio.json` files to your KOReader device:

```
KOBO/
└── Books/
    └── book.epub
    └── book.opus
    └── book.audio.json
```

KOReader will automatically detect the audio sidecar and enable synchronized playback.

## Pipeline Phases

### Phase 1: EPUB Parsing
- Extracts text from EPUB HTML content
- Filters chapter headings and short strings
- Outputs structured paragraph data

### Phase 2: Translation
- Loads Qwen model with 4-bit quantization
- Batch translates with cultural awareness
- Saves intermediate JSON for resume

### Phase 3: Audio Generation
- Synthesizes speech with Qwen3-TTS
- Aligns audio with Forced Aligner
- Calculates precise timestamps

### Phase 4: Encoding
- Encodes to Opus format
- Generates KOReader manifest
- Packages final output

## Memory Management

The pipeline automatically:
- Unloads models between phases
- Triggers garbage collection
- Monitors VRAM usage
- Clears intermediate data

For GPUs with limited VRAM (< 12GB), consider:
- Using 4-bit quantization (default)
- Processing shorter chapters first
- Running translation and audio separately

## Error Handling

- Skips malformed HTML paragraphs
- Retries failed translations (configurable)
- Falls back to original text on translation failure
- Logs all errors with timestamps

## License

MIT License
