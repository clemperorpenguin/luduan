"""
Configuration module for Luduan EPUB-to-Audiobook pipeline.
Handles paths, model configurations, and runtime settings.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PathConfig:
    """Path configurations for input/output directories."""
    base_dir: Path = field(default_factory=Path.cwd)
    input_dir: Path = field(default_factory=lambda: Path.cwd / "input")
    output_dir: Path = field(default_factory=lambda: Path.cwd / "output")
    cache_dir: Path = field(default_factory=lambda: Path.cwd / "cache")
    temp_dir: Path = field(default_factory=lambda: Path.cwd / "temp")

    def __post_init__(self):
        """Create directories if they don't exist."""
        for dir_path in [self.input_dir, self.output_dir, self.cache_dir, self.temp_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)


@dataclass
class TranslationConfig:
    """Configuration for the Qwen 3.5 translation model."""
    # Model path - can be local GGUF/Safetensors or HuggingFace model ID
    model_name: str = "Qwen/Qwen2.5-7B-Instruct"
    model_path: Optional[Path] = None
    
    # Quantization settings for VRAM optimization
    use_4bit: bool = True
    use_8bit: bool = False
    bnb_4bit_compute_dtype: str = "float16"
    bnb_4bit_quant_type: str = "nf4"
    
    # Generation parameters
    max_new_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    do_sample: bool = True
    
    # Batch processing
    batch_size: int = 4
    max_batch_length: int = 2048  # Max characters per batch


@dataclass
class AudioConfig:
    """Configuration for TTS and Forced Aligner models."""
    # TTS Model
    tts_model_name: str = "Qwen/Qwen3-TTS-1.7B"
    tts_model_path: Optional[Path] = None
    
    # Forced Aligner Model
    aligner_model_name: str = "Qwen/Qwen3-ForcedAligner-0.6B"
    aligner_model_path: Optional[Path] = None
    
    # Audio settings
    sample_rate: int = 24000  # Qwen TTS native sample rate
    opus_sample_rate: int = 24000  # Must match TTS output
    opus_bitrate: int = 32000  # 32kbps for good quality audiobook
    
    # Voice settings
    voice: str = "default"  # Can be extended for multiple voices


@dataclass
class ProcessingConfig:
    """General processing and optimization settings."""
    # Memory management
    unload_models_between_phases: bool = True
    gc_collect_threshold: float = 0.8  # GPU memory threshold to trigger GC
    
    # Error handling
    skip_failed_paragraphs: bool = True
    max_retries: int = 3
    
    # Resume capability
    enable_resume: bool = True
    intermediate_save_interval: int = 5  # Save every N paragraphs
    
    # Text filtering
    min_paragraph_length: int = 10  # Minimum characters to process
    skip_chapter_headings: bool = True
    heading_patterns: list = field(default_factory=lambda: [
        r"^Chapter\s*\d+",
        r"^第 [零一二三四五六七八九十百千万\d]+ 章",
        r"^PART\s+\d+",
        r"^PROLOGUE",
        r"^EPILOGUE",
    ])


@dataclass
class LogConfig:
    """Logging configuration."""
    log_dir: Path = field(default_factory=lambda: Path.cwd / "logs")
    log_level: str = "INFO"
    log_file: str = "luduan.log"
    enable_console: bool = True
    enable_file: bool = True
    enable_vram_monitoring: bool = True
    vram_monitor_interval: int = 10  # Log VRAM every N seconds


class Config:
    """Main configuration class that aggregates all sub-configs."""
    
    def __init__(self):
        self.paths = PathConfig()
        self.translation = TranslationConfig()
        self.audio = AudioConfig()
        self.processing = ProcessingConfig()
        self.logging = LogConfig()
        
        # Override with environment variables if set
        self._load_from_env()

    def _load_from_env(self):
        """Load configuration overrides from environment variables."""
        # Path overrides
        if env_input := os.getenv("LUDUAN_INPUT_DIR"):
            self.paths.input_dir = Path(env_input)
        if env_output := os.getenv("LUDUAN_OUTPUT_DIR"):
            self.paths.output_dir = Path(env_output)
        if env_cache := os.getenv("LUDUAN_CACHE_DIR"):
            self.paths.cache_dir = Path(env_cache)
            
        # Model overrides
        if env_model := os.getenv("LUDUAN_TRANSLATION_MODEL"):
            self.translation.model_name = env_model
        if env_tts := os.getenv("LUDUAN_TTS_MODEL"):
            self.audio.tts_model_name = env_tts
        if env_aligner := os.getenv("LUDUAN_ALIGNER_MODEL"):
            self.audio.aligner_model_name = env_aligner
            
        # Ensure directories exist after overrides
        for dir_path in [self.paths.input_dir, self.paths.output_dir, 
                         self.paths.cache_dir, self.paths.temp_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        self.logging.log_dir.mkdir(parents=True, exist_ok=True)


# Global configuration instance
config = Config()
