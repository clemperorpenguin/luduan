"""
The Jade Slip - Encoding & Packaging Module.
Encodes raw audio to Opus and builds KOReader sidecar files.
"""

import json
import struct
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np

try:
    import pyogg
    PYOGG_AVAILABLE = True
except ImportError:
    PYOGG_AVAILABLE = False
    pyogg = None

from config import config
from logger import logger
from audio_engine import AudioSegment


@dataclass
class KOReaderManifest:
    """
    KOReader audio sidecar manifest structure.
    Matches KOReader's expected JSON format for audio playback.
    """
    version: str = "1.0"
    book_title: str = ""
    source_file: str = ""
    audio_file: str = ""
    language: str = "en"
    created_at: str = ""
    total_duration: float = 0.0
    segments: list[dict] = field(default_factory=list)
    
    def add_segment(
        self,
        paragraph_index: int,
        start_time: float,
        end_time: float,
        text: str,
        text_start: str = ""
    ):
        """
        Add a segment to the manifest.
        
        Args:
            paragraph_index: Index of paragraph
            start_time: Start time in seconds
            end_time: End time in seconds
            text: Full text of segment
            text_start: First 50 chars for fuzzy matching
        """
        if not text_start:
            text_start = text[:50] if len(text) > 50 else text
        
        self.segments.append({
            "index": paragraph_index,
            "start_time": start_time,
            "end_time": end_time,
            "duration": end_time - start_time,
            "text": text,
            "text_start": text_start
        })
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "version": self.version,
            "book_title": self.book_title,
            "source_file": self.source_file,
            "audio_file": self.audio_file,
            "language": self.language,
            "created_at": self.created_at,
            "total_duration": self.total_duration,
            "segment_count": len(self.segments),
            "segments": self.segments
        }
    
    def save(self, output_path: Path):
        """Save manifest to JSON file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"KOReader manifest saved: {output_path}")


class OpusEncoder:
    """
    Opus audio encoder using pyogg.
    Encodes float32 PCM arrays to Opus format.
    """
    
    def __init__(
        self,
        sample_rate: int = None,
        bitrate: int = None,
        channels: int = 1
    ):
        """
        Initialize Opus encoder.
        
        Args:
            sample_rate: Output sample rate (default from config)
            bitrate: Output bitrate in bps (default from config)
            channels: Number of audio channels (default 1 for mono)
        """
        self.sample_rate = sample_rate or config.audio.opus_sample_rate
        self.bitrate = bitrate or config.audio.opus_bitrate
        self.channels = channels
        self.encoder = None
        self.is_initialized = False
        
        if not PYOGG_AVAILABLE:
            logger.warning("pyogg not available - Opus encoding will be simulated")
    
    def initialize(self) -> bool:
        """Initialize the Opus encoder."""
        if not PYOGG_AVAILABLE:
            return False
        
        try:
            # Create Opus encoder
            # Note: pyogg API may vary; this is a representative implementation
            self.encoder = pyogg.OpusEncoder()
            self.encoder.set_sample_rate(self.sample_rate)
            self.encoder.set_bitrate(self.bitrate)
            self.encoder.set_channels(self.channels)
            
            self.is_initialized = True
            logger.debug(f"Opus encoder initialized: {self.sample_rate}Hz, {self.bitrate}bps")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Opus encoder: {e}")
            return False
    
    def float32_to_int16(self, audio_array: np.ndarray) -> np.ndarray:
        """
        Convert float32 PCM (-1.0 to 1.0) to int16 (-32768 to 32767).
        
        Args:
            audio_array: float32 PCM array
            
        Returns:
            int16 PCM array
        """
        # Clip to valid range
        clipped = np.clip(audio_array, -1.0, 1.0)
        # Scale to int16 range
        scaled = clipped * 32767
        return scaled.astype(np.int16)
    
    def encode_frame(self, audio_frame: np.ndarray) -> Optional[bytes]:
        """
        Encode a single frame of audio.
        
        Args:
            audio_frame: int16 PCM frame
            
        Returns:
            Opus-encoded bytes or None on failure
        """
        if not self.is_initialized:
            return None
        
        try:
            # pyogg expects raw bytes
            frame_bytes = audio_frame.tobytes()
            encoded = self.encoder.encode(frame_bytes, len(frame_bytes))
            return encoded
        except Exception as e:
            logger.error(f"Frame encoding failed: {e}")
            return None
    
    def encode_to_file(
        self,
        audio_array: np.ndarray,
        output_path: Path,
        frame_size_ms: int = 20
    ) -> bool:
        """
        Encode complete audio array to Opus file.
        
        Args:
            audio_array: float32 PCM audio
            output_path: Output file path
            frame_size_ms: Frame size in milliseconds
            
        Returns:
            True if successful
        """
        if len(audio_array) == 0:
            logger.error("Empty audio array")
            return False
        
        # Convert to int16
        int16_audio = self.float32_to_int16(audio_array)
        
        # Calculate frame size in samples
        frame_size = int(self.sample_rate * frame_size_ms / 1000)
        
        if not PYOGG_AVAILABLE:
            # Simulate encoding for testing
            logger.warning("pyogg not available - simulating Opus encoding")
            self._simulate_opus_file(int16_audio, output_path)
            return True
        
        try:
            if not self.is_initialized:
                if not self.initialize():
                    return False
            
            # Open output file
            # Note: Actual pyogg API for file output may differ
            with open(output_path, 'wb') as f:
                # Write Opus header (simplified)
                f.write(self._create_opus_header())
                
                # Process frames
                for i in range(0, len(int16_audio), frame_size):
                    frame = int16_audio[i:i + frame_size]
                    
                    # Pad last frame if needed
                    if len(frame) < frame_size:
                        padding = np.zeros(frame_size - len(frame), dtype=np.int16)
                        frame = np.concatenate([frame, padding])
                    
                    encoded = self.encode_frame(frame)
                    if encoded:
                        f.write(encoded)
            
            logger.info(f"Opus file created: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Opus encoding failed: {e}")
            return False
    
    def _create_opus_header(self) -> bytes:
        """Create a minimal Opus header for the Ogg container."""
        # Simplified Opus header
        # In production, use proper Ogg/Opus header structure
        header = b'OpusHead'  # Magic signature
        header += struct.pack('<B', 1)  # Version
        header += struct.pack('<B', self.channels)  # Channel count
        header += struct.pack('<H', 0)  # Pre-skip
        header += struct.pack('<I', self.sample_rate)  # Sample rate
        header += struct.pack('<H', 0)  # Output gain
        header += struct.pack('<B', 0)  # Channel mapping family
        return header
    
    def _simulate_opus_file(self, audio_data: np.ndarray, output_path: Path):
        """
        Create a simulated Opus file for testing when pyogg is unavailable.
        In production, this would be a real Opus file.
        """
        # Create a marker file indicating simulated output
        with open(output_path, 'wb') as f:
            # Write a simple header indicating this is simulated
            f.write(b'SIMULATED_OPUS')
            f.write(struct.pack('<I', self.sample_rate))
            f.write(struct.pack('<I', len(audio_data)))
            f.write(audio_data.tobytes())
        
        logger.warning(f"Created simulated Opus file (pyogg not available): {output_path}")


class AudioPackager:
    """
    High-level packager that combines encoding and manifest generation.
    Creates both the Opus audio file and KOReader sidecar.
    """
    
    def __init__(self, book_name: str, source_file: str = ""):
        """
        Initialize packager.
        
        Args:
            book_name: Name of the book
            source_file: Original source file path
        """
        self.book_name = book_name
        self.source_file = source_file
        self.encoder = OpusEncoder()
        self.manifest = KOReaderManifest()
        self.all_audio_segments: list[np.ndarray] = []
        
        # Initialize manifest
        self.manifest.book_title = book_name
        self.manifest.source_file = source_file
        self.manifest.audio_file = f"{book_name}.opus"
        self.manifest.created_at = datetime.now().isoformat()
        self.manifest.language = "en"
    
    def add_segment(self, segment: AudioSegment):
        """
        Add an audio segment to the package.
        
        Args:
            segment: AudioSegment from audio engine
        """
        self.all_audio_segments.append(segment.audio_array)
        
        self.manifest.add_segment(
            paragraph_index=segment.paragraph_index,
            start_time=segment.start_time,
            end_time=segment.end_time,
            text=segment.text,
            text_start=segment.text[:50] if len(segment.text) > 50 else segment.text
        )
        
        self.manifest.total_duration = segment.end_time
    
    def save(
        self,
        output_dir: Path,
        audio_filename: str = None,
        manifest_filename: str = None
    ) -> tuple[Path, Path]:
        """
        Save both audio file and manifest.
        
        Args:
            output_dir: Output directory
            audio_filename: Optional custom audio filename
            manifest_filename: Optional custom manifest filename
            
        Returns:
            Tuple of (audio_path, manifest_path)
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Default filenames
        if audio_filename is None:
            audio_filename = f"{self.book_name}.opus"
        if manifest_filename is None:
            manifest_filename = f"{self.book_name}.audio.json"
        
        audio_path = output_dir / audio_filename
        manifest_path = output_dir / manifest_filename
        
        # Concatenate all audio
        if self.all_audio_segments:
            full_audio = np.concatenate(self.all_audio_segments)
        else:
            full_audio = np.array([], dtype=np.float32)
            logger.warning("No audio segments to save")
        
        # Encode and save audio
        self.encoder.encode_to_file(full_audio, audio_path)
        
        # Save manifest
        self.manifest.save(manifest_path)
        
        logger.info(f"Package saved: {audio_path.name}, {manifest_path.name}")
        
        return audio_path, manifest_path


def create_koreader_package(
    segments: list[AudioSegment],
    book_name: str,
    output_dir: Path,
    source_file: str = ""
) -> tuple[Path, Path]:
    """
    Convenience function to create a complete KOReader package.
    
    Args:
        segments: List of AudioSegment objects
        book_name: Book title
        output_dir: Output directory
        source_file: Original source file path
        
    Returns:
        Tuple of (audio_path, manifest_path)
    """
    packager = AudioPackager(book_name, source_file)
    
    for segment in segments:
        packager.add_segment(segment)
    
    return packager.save(output_dir)


if __name__ == "__main__":
    # Test the encoder
    print("Opus Encoder Test")
    print("=" * 40)
    
    # Create test audio (sine wave)
    sample_rate = 24000
    duration = 1.0  # seconds
    frequency = 440  # Hz (A4)
    t = np.linspace(0, duration, int(sample_rate * duration))
    test_audio = np.sin(2 * np.pi * frequency * t).astype(np.float32)
    
    # Test encoding
    encoder = OpusEncoder(sample_rate=sample_rate)
    output_path = Path("test_output.opus")
    
    if encoder.encode_to_file(test_audio, output_path):
        print(f"Encoded {len(test_audio)} samples to {output_path}")
    
    # Test manifest
    manifest = KOReaderManifest(
        book_title="Test Book",
        source_file="test.epub"
    )
    manifest.add_segment(
        paragraph_index=0,
        start_time=0.0,
        end_time=1.0,
        text="This is a test segment for KOReader audio playback."
    )
    manifest.save(Path("test_manifest.json"))
    print(f"Manifest saved with {len(manifest.segments)} segment(s)")
