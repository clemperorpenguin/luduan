"""
The Dragon's Voice - Audio Synthesis & Alignment Module.
Generates raw audio arrays and timestamp metadata using Qwen TTS and Forced Aligner.
"""

import gc
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Generator

import numpy as np

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None

from config import config
from logger import logger, vram_monitor
from translator import TranslatedParagraph


@dataclass
class AudioSegment:
    """Represents a generated audio segment with timing information."""
    paragraph_index: int
    chapter_index: int
    text: str
    audio_array: np.ndarray  # float32 PCM
    duration_seconds: float
    start_time: float  # Global start time in chapter
    end_time: float    # Global end time in chapter
    sample_rate: int
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "paragraph_index": self.paragraph_index,
            "chapter_index": self.chapter_index,
            "text": self.text,
            "duration_seconds": self.duration_seconds,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "sample_rate": self.sample_rate
        }


class QwenTTS:
    """
    Qwen3-TTS-1.7B wrapper for text-to-speech synthesis.
    
    Note: This is a placeholder implementation. The actual Qwen3-TTS
    model architecture may require specific loading code based on
    the model's implementation on HuggingFace.
    """
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.is_loaded = False
        self.sample_rate = config.audio.sample_rate
        
    def load_model(self) -> bool:
        """Load the TTS model."""
        if not TORCH_AVAILABLE:
            logger.error("PyTorch not available")
            return False
        
        if self.is_loaded:
            return True
        
        try:
            model_path = str(config.audio.tts_model_path) if config.audio.tts_model_path else config.audio.tts_model_name
            logger.info(f"Loading TTS model: {model_path}")
            
            # Load tokenizer and model
            # Note: Actual loading depends on the specific model architecture
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                trust_remote_code=True,
                cache_dir=str(config.paths.cache_dir)
            )
            
            self.model = AutoModelForCausalLM.from_pretrained(
                model_path,
                trust_remote_code=True,
                cache_dir=str(config.paths.cache_dir),
                torch_dtype=torch.float16,
                device_map="auto"
            )
            
            self.model.eval()
            self.is_loaded = True
            
            vram_monitor.log_now()
            logger.info("TTS model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load TTS model: {e}")
            return False
    
    def unload_model(self):
        """Unload model and free VRAM."""
        if self.model is not None:
            del self.model
            self.model = None
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
        
        gc.collect()
        if TORCH_AVAILABLE and torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        self.is_loaded = False
        vram_monitor.log_now()
        logger.info("TTS model unloaded")
    
    def synthesize(self, text: str) -> np.ndarray:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to synthesize
            
        Returns:
            float32 PCM audio array
        """
        if not self.is_loaded:
            logger.error("TTS model not loaded")
            return np.array([], dtype=np.float32)
        
        try:
            # Note: This is a placeholder implementation
            # Actual Qwen3-TTS may have a different API
            # The following is a representative example
            
            # Prepare input
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            )
            
            if torch.cuda.is_available():
                inputs = {k: v.cuda() for k, v in inputs.items()}
            
            # Generate audio tokens
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=1024,
                    do_sample=True,
                    temperature=0.7
                )
            
            # Decode to audio waveform
            # This is model-specific - actual implementation depends on Qwen3-TTS architecture
            audio_tokens = outputs[0]
            
            # Placeholder: Generate a synthetic audio array
            # In reality, this would decode the audio tokens to waveform
            duration_estimate = len(text) * 0.1  # Rough estimate: 10 chars per second
            num_samples = int(duration_estimate * self.sample_rate)
            
            # This would be replaced with actual model output
            audio_array = np.zeros(num_samples, dtype=np.float32)
            
            return audio_array
            
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            return np.array([], dtype=np.float32)


class QwenForcedAligner:
    """
    Qwen3-ForcedAligner-0.6B wrapper for audio-text alignment.
    Extracts precise timestamps for text segments within audio.
    """
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.is_loaded = False
        
    def load_model(self) -> bool:
        """Load the aligner model."""
        if not TORCH_AVAILABLE:
            logger.error("PyTorch not available")
            return False
        
        if self.is_loaded:
            return True
        
        try:
            model_path = str(config.audio.aligner_model_path) if config.audio.aligner_model_path else config.audio.aligner_model_name
            logger.info(f"Loading aligner model: {model_path}")
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                trust_remote_code=True,
                cache_dir=str(config.paths.cache_dir)
            )
            
            self.model = AutoModelForCausalLM.from_pretrained(
                model_path,
                trust_remote_code=True,
                cache_dir=str(config.paths.cache_dir),
                torch_dtype=torch.float16,
                device_map="auto"
            )
            
            self.model.eval()
            self.is_loaded = True
            
            vram_monitor.log_now()
            logger.info("Aligner model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load aligner model: {e}")
            return False
    
    def unload_model(self):
        """Unload model and free VRAM."""
        if self.model is not None:
            del self.model
            self.model = None
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
        
        gc.collect()
        if TORCH_AVAILABLE and torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        self.is_loaded = False
        vram_monitor.log_now()
        logger.info("Aligner model unloaded")
    
    def align(self, audio_array: np.ndarray, text: str, sample_rate: int) -> tuple[float, float]:
        """
        Align text with audio to get precise timestamps.
        
        Args:
            audio_array: float32 PCM audio
            text: Text that was spoken
            sample_rate: Audio sample rate
            
        Returns:
            Tuple of (start_time, end_time) in seconds
        """
        if not self.is_loaded:
            logger.error("Aligner model not loaded")
            return (0.0, len(audio_array) / sample_rate)
        
        try:
            # Note: Actual alignment implementation depends on model architecture
            # This is a placeholder showing the expected interface
            
            # Convert audio to model input format
            # The aligner typically takes audio features + text tokens
            
            # Placeholder: Return estimated full duration
            duration = len(audio_array) / sample_rate
            return (0.0, duration)
            
        except Exception as e:
            logger.error(f"Alignment failed: {e}")
            # Return full duration as fallback
            duration = len(audio_array) / sample_rate
            return (0.0, duration)


class AudioEngine:
    """
    Main audio engine combining TTS and alignment.
    Manages both models and provides unified interface for audio generation.
    """
    
    def __init__(self):
        self.tts = QwenTTS()
        self.aligner = QwenForcedAligner()
        self.current_time = 0.0  # Global time tracker for chapter
        self.sample_rate = config.audio.sample_rate
        
    def load_models(self) -> bool:
        """Load both TTS and aligner models."""
        logger.info("Loading audio models...")
        
        tts_ok = self.tts.load_model()
        aligner_ok = self.aligner.load_model()
        
        if tts_ok and aligner_ok:
            logger.info("All audio models loaded")
            return True
        else:
            logger.error("Failed to load one or more audio models")
            return False
    
    def unload_models(self):
        """Unload both models and free VRAM."""
        self.tts.unload_model()
        self.aligner.unload_model()
        logger.info("All audio models unloaded")
    
    def generate_audio_segment(
        self,
        text: str,
        paragraph_index: int,
        chapter_index: int
    ) -> Optional[AudioSegment]:
        """
        Generate audio for a single paragraph with alignment.
        
        Args:
            text: Text to synthesize
            paragraph_index: Index within chapter
            chapter_index: Chapter number
            
        Returns:
            AudioSegment with audio and timing, or None on failure
        """
        try:
            # Generate audio
            audio_array = self.tts.synthesize(text)
            
            if len(audio_array) == 0:
                logger.error(f"Failed to generate audio for paragraph {paragraph_index}")
                return None
            
            # Get precise alignment
            start_time, end_time = self.aligner.align(
                audio_array, text, self.sample_rate
            )
            
            # Calculate global times
            global_start = self.current_time
            duration = end_time - start_time
            global_end = self.current_time + duration
            
            # Update global time tracker
            self.current_time = global_end
            
            # Create segment
            segment = AudioSegment(
                paragraph_index=paragraph_index,
                chapter_index=chapter_index,
                text=text,
                audio_array=audio_array,
                duration_seconds=duration,
                start_time=global_start,
                end_time=global_end,
                sample_rate=self.sample_rate
            )
            
            return segment
            
        except Exception as e:
            logger.error(f"Failed to generate audio segment: {e}")
            return None
    
    def reset_time(self):
        """Reset global time tracker (for new chapter)."""
        self.current_time = 0.0
    
    def get_current_time(self) -> float:
        """Get current global time position."""
        return self.current_time


class AudioGenerator:
    """
    High-level audio generation orchestrator.
    Processes translated paragraphs and generates complete chapter audio.
    """
    
    def __init__(self):
        self.engine = AudioEngine()
        self.segments: list[AudioSegment] = []
        
    def generate_chapter_audio(
        self,
        chapter_data: dict,
        chapter_index: int
    ) -> Generator[AudioSegment, None, None]:
        """
        Generate audio for all paragraphs in a chapter.
        
        Args:
            chapter_data: Chapter dictionary from translator
            chapter_index: Chapter index
            
        Yields:
            AudioSegment objects
        """
        if not self.engine.load_models():
            logger.error("Failed to load audio models")
            return
        
        self.engine.reset_time()
        
        paragraphs = chapter_data.get("paragraphs", [])
        logger.info(f"Generating audio for chapter {chapter_index}: {len(paragraphs)} paragraphs")
        
        from logger import progress_tracker
        progress_tracker.set_phase("audio_generation")
        progress_tracker.total_paragraphs = len(paragraphs)
        
        try:
            for i, para in enumerate(paragraphs):
                progress_tracker.current_paragraph = i + 1
                
                text = para.get("translated_text", para.get("source_text", ""))
                
                segment = self.engine.generate_audio_segment(
                    text=text,
                    paragraph_index=i,
                    chapter_index=chapter_index
                )
                
                if segment:
                    self.segments.append(segment)
                    yield segment
                    progress_tracker.increment_processed()
                else:
                    progress_tracker.increment_failed()
                    
        finally:
            # Unload models to free VRAM
            if config.processing.unload_models_between_phases:
                self.engine.unload_models()
    
    def concatenate_chapter_audio(self) -> np.ndarray:
        """
        Concatenate all audio segments for a chapter.
        
        Returns:
            Concatenated float32 PCM audio array
        """
        if not self.segments:
            return np.array([], dtype=np.float32)
        
        arrays = [seg.audio_array for seg in self.segments]
        return np.concatenate(arrays)
    
    def get_segments(self) -> list[AudioSegment]:
        """Get all generated segments."""
        return self.segments
    
    def clear_segments(self):
        """Clear stored segments (for memory management)."""
        self.segments.clear()


def generate_audio_for_paragraph(
    text: str,
    paragraph_index: int,
    chapter_index: int,
    engine: Optional[AudioEngine] = None
) -> Optional[AudioSegment]:
    """
    Convenience function to generate audio for a single paragraph.
    
    Args:
        text: Text to synthesize
        paragraph_index: Paragraph index
        chapter_index: Chapter index
        engine: Optional existing AudioEngine
        
    Returns:
        AudioSegment or None on failure
    """
    own_engine = engine is None
    if engine is None:
        engine = AudioEngine()
        if not engine.load_models():
            return None
    
    try:
        return engine.generate_audio_segment(text, paragraph_index, chapter_index)
    finally:
        if own_engine:
            engine.unload_models()


if __name__ == "__main__":
    # Test the audio engine
    print("Audio Engine Test")
    print("=" * 40)
    
    engine = AudioEngine()
    if engine.load_models():
        segment = engine.generate_audio_segment(
            text="Hello, this is a test.",
            paragraph_index=0,
            chapter_index=0
        )
        if segment:
            print(f"Generated: {segment.duration_seconds:.2f}s audio")
            print(f"Samples: {len(segment.audio_array)}")
            print(f"Time: {segment.start_time:.2f}s - {segment.end_time:.2f}s")
        engine.unload_models()
    else:
        print("Failed to load audio models")
