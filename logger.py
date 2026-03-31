"""
Robust logging system for Luduan EPUB-to-Audiobook pipeline.
Tracks translation progress, VRAM usage, and pipeline status.
"""

import logging
import sys
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from config import config


class VRAMMonitor:
    """Monitor and log VRAM usage."""
    
    def __init__(self, logger: logging.Logger, interval: int = 10):
        self.logger = logger
        self.interval = interval
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        
    def _get_vram_info(self) -> str:
        """Get current VRAM usage information."""
        if not TORCH_AVAILABLE or not torch.cuda.is_available():
            return "CUDA not available"
        
        try:
            allocated = torch.cuda.memory_allocated() / (1024 ** 3)
            reserved = torch.cuda.memory_reserved() / (1024 ** 3)
            max_allocated = torch.cuda.max_memory_allocated() / (1024 ** 3)
            
            return (f"VRAM: Alloc={allocated:.2f}GB, "
                    f"Reserved={reserved:.2f}GB, "
                    f"Max={max_allocated:.2f}GB")
        except Exception as e:
            return f"VRAM info error: {e}"
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        while not self._stop_event.is_set():
            self.logger.info(self._get_vram_info())
            self._stop_event.wait(self.interval)
    
    def start(self):
        """Start VRAM monitoring thread."""
        if not config.logging.enable_vram_monitoring:
            return
            
        if self._thread and self._thread.is_alive():
            return
            
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        self.logger.info("VRAM monitoring started")
    
    def stop(self):
        """Stop VRAM monitoring thread."""
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=2.0)
            self.logger.info("VRAM monitoring stopped")
    
    def log_now(self):
        """Log VRAM usage immediately."""
        self.logger.info(self._get_vram_info())


class ProgressTracker:
    """Track and log translation/processing progress."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.current_chapter = 0
        self.total_chapters = 0
        self.current_paragraph = 0
        self.total_paragraphs = 0
        self.processed_count = 0
        self.failed_count = 0
        self.start_time: Optional[datetime] = None
        self.phase = "initializing"
        self._lock = threading.Lock()
    
    def set_phase(self, phase: str):
        """Set current processing phase."""
        with self._lock:
            self.phase = phase
            self.logger.info(f"=== Phase: {phase.upper()} ===")
    
    def set_chapter_progress(self, current: int, total: int):
        """Set chapter progress."""
        with self._lock:
            self.current_chapter = current
            self.total_chapters = total
            self._log_progress()
    
    def set_paragraph_progress(self, current: int, total: int):
        """Set paragraph progress within chapter."""
        with self._lock:
            self.current_paragraph = current
            self.total_paragraphs = total
    
    def increment_processed(self):
        """Increment processed count."""
        with self._lock:
            self.processed_count += 1
            if self.processed_count % config.processing.intermediate_save_interval == 0:
                self._log_progress()
    
    def increment_failed(self):
        """Increment failed count."""
        with self._lock:
            self.failed_count += 1
            self.logger.warning(f"Failed item count: {self.failed_count}")
    
    def start_tracking(self):
        """Start progress tracking."""
        with self._lock:
            self.start_time = datetime.now()
            self.processed_count = 0
            self.failed_count = 0
    
    def _log_progress(self):
        """Log current progress."""
        if self.start_time is None:
            return
            
        elapsed = datetime.now() - self.start_time
        elapsed_str = str(elapsed).split('.')[0]  # Remove microseconds
        
        if self.total_paragraphs > 0:
            progress_pct = (self.current_paragraph / self.total_paragraphs) * 100
        else:
            progress_pct = 0
            
        self.logger.info(
            f"Progress: Chapter {self.current_chapter}/{self.total_chapters} | "
            f"Para {self.current_paragraph}/{self.total_paragraphs} ({progress_pct:.1f}%) | "
            f"Processed: {self.processed_count} | Failed: {self.failed_count} | "
            f"Elapsed: {elapsed_str}"
        )
    
    def get_summary(self) -> dict:
        """Get progress summary."""
        with self._lock:
            elapsed = datetime.now() - self.start_time if self.start_time else None
            return {
                "phase": self.phase,
                "chapter": f"{self.current_chapter}/{self.total_chapters}",
                "processed": self.processed_count,
                "failed": self.failed_count,
                "elapsed": str(elapsed).split('.')[0] if elapsed else "N/A"
            }


def setup_logging() -> tuple[logging.Logger, VRAMMonitor, ProgressTracker]:
    """
    Set up the logging system with console and file handlers.
    
    Returns:
        tuple: (logger, vram_monitor, progress_tracker)
    """
    # Create logger
    logger = logging.getLogger("luduan")
    logger.setLevel(getattr(logging, config.logging.log_level.upper()))
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    simple_formatter = logging.Formatter(
        "%(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S"
    )
    
    # Console handler
    if config.logging.enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if config.logging.enable_file:
        config.logging.log_dir.mkdir(parents=True, exist_ok=True)
        log_file = config.logging.log_dir / config.logging.log_file
        
        # Create timestamped backup
        if log_file.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = config.logging.log_dir / f"{timestamp}_{config.logging.log_file}"
            log_file.rename(backup_file)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
    
    # Create VRAM monitor
    vram_monitor = VRAMMonitor(
        logger, 
        interval=config.logging.vram_monitor_interval
    )
    
    # Create progress tracker
    progress_tracker = ProgressTracker(logger)
    
    logger.info("=" * 60)
    logger.info("LUDUAN - EPUB to Audiobook Pipeline")
    logger.info("=" * 60)
    logger.info(f"Input directory: {config.paths.input_dir}")
    logger.info(f"Output directory: {config.paths.output_dir}")
    logger.info(f"Log file: {log_file if config.logging.enable_file else 'disabled'}")
    
    return logger, vram_monitor, progress_tracker


# Global instances (initialized when module is imported)
logger, vram_monitor, progress_tracker = setup_logging()
