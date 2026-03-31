#!/usr/bin/env python3
"""
Luduan - EPUB to Audiobook Pipeline
Main execution module that orchestrates all phases.

Usage:
    python main.py <epub_file> [options]
    
Environment Variables:
    LUDUAN_INPUT_DIR    - Input directory for EPUB files
    LUDUAN_OUTPUT_DIR   - Output directory for generated files
    LUDUAN_CACHE_DIR    - Cache directory for models
    LUDUAN_TRANSLATION_MODEL - Translation model name/path
    LUDUAN_TTS_MODEL    - TTS model name/path
    LUDUAN_ALIGNER_MODEL - Aligner model name/path
"""

import sys
import gc
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from config import config
from logger import logger, vram_monitor, progress_tracker
from parser import EPUBParser, parse_epub_to_dict
from translator import BatchTranslator, TranslationEngine
from audio_engine import AudioEngine, AudioGenerator, AudioSegment
from encoder import AudioPackager, create_koreader_package


class LuduanPipeline:
    """
    Main pipeline orchestrator for EPUB to Audiobook conversion.
    
    Features:
    - Modular phase execution
    - Memory management between phases
    - Resume capability from intermediate files
    - Error handling and recovery
    - Progress tracking and logging
    """
    
    def __init__(self, epub_path: Path, target_language: str = "English"):
        """
        Initialize the pipeline.
        
        Args:
            epub_path: Path to the EPUB file
            target_language: Target language for translation
        """
        self.epub_path = Path(epub_path)
        self.target_language = target_language
        self.book_name = epub_path.stem
        
        # Output paths
        self.intermediate_path = config.paths.output_dir / f"{self.book_name}_translated_tome.json"
        self.audio_output_path = config.paths.output_dir / f"{self.book_name}.opus"
        self.manifest_output_path = config.paths.output_dir / f"{self.book_name}.audio.json"
        
        # Phase state
        self.translation_complete = False
        self.audio_complete = False
        self.encoding_complete = False
        
        # Data containers
        self.chapters: list[dict] = []
        self.audio_segments: list[AudioSegment] = []
        
        logger.info(f"Pipeline initialized for: {self.epub_path.name}")
        logger.info(f"Book name: {self.book_name}")
    
    def _check_resume(self) -> bool:
        """
        Check if we can resume from intermediate files.
        
        Returns:
            True if resuming from existing intermediate
        """
        if not config.processing.enable_resume:
            return False
        
        if self.intermediate_path.exists():
            logger.info(f"Found intermediate file: {self.intermediate_path}")
            try:
                with open(self.intermediate_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.chapters = list(data.get("chapters", {}).values())
                total_paras = sum(len(c.get("paragraphs", [])) for c in self.chapters)
                
                if total_paras > 0:
                    logger.info(f"Resuming with {len(self.chapters)} chapters, {total_paras} paragraphs")
                    self.translation_complete = True
                    return True
            except Exception as e:
                logger.warning(f"Failed to load intermediate: {e}")
        
        return False
    
    def _force_memory_cleanup(self):
        """Force garbage collection and VRAM cleanup."""
        gc.collect()
        
        if TORCH_AVAILABLE and torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        
        vram_monitor.log_now()
    
    def phase_1_parse(self) -> bool:
        """
        Phase 1: Parse EPUB and extract text.
        
        Returns:
            True if successful
        """
        logger.info("=" * 60)
        logger.info("PHASE 1: EPUB Parsing")
        logger.info("=" * 60)
        
        progress_tracker.set_phase("parsing")
        
        try:
            parser = EPUBParser(self.epub_path)
            
            if not parser.load():
                logger.error("Failed to load EPUB file")
                return False
            
            # Get statistics
            stats = parser.get_statistics()
            logger.info(f"Parsed: {stats['chapters']} chapters, {stats['paragraphs']} paragraphs")
            logger.info(f"Total characters: {stats['total_characters']:,}")
            
            # Store chapters for translation
            self.chapters = [
                {
                    "index": c.index,
                    "title": c.title,
                    "paragraphs": [
                        {
                            "chapter_index": p.chapter_index,
                            "chapter_title": p.chapter_title,
                            "paragraph_index": p.paragraph_index,
                            "source_text": p.source_text,
                            "html_path": p.html_path
                        }
                        for p in c.paragraphs
                    ]
                }
                for c in parser.parse_all()
            ]
            
            return True
            
        except Exception as e:
            logger.error(f"Parsing failed: {e}")
            return False
    
    def phase_2_translate(self) -> bool:
        """
        Phase 2: Translate all text using Qwen.
        
        Returns:
            True if successful
        """
        logger.info("=" * 60)
        logger.info("PHASE 2: Translation")
        logger.info("=" * 60)
        
        progress_tracker.set_phase("translation")
        progress_tracker.start_tracking()
        
        try:
            translator = BatchTranslator(self.epub_path, self.target_language)
            
            # Check for resume
            if config.processing.enable_resume and self.intermediate_path.exists():
                logger.info("Loading existing translation...")
                if translator.engine.load_intermediate(self.intermediate_path):
                    self.chapters = translator.get_chapters()
                    self.translation_complete = True
                    return True
            
            # Run full translation
            translator.translate_full(
                save_intermediate=True,
                resume=False
            )
            
            self.chapters = translator.get_chapters()
            self.translation_complete = True
            
            logger.info(f"Translation complete: {len(self.chapters)} chapters")
            return True
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return False
        
        finally:
            # Ensure model is unloaded
            self._force_memory_cleanup()
    
    def phase_3_generate_audio(self) -> bool:
        """
        Phase 3: Generate audio for all translated text.
        
        Returns:
            True if successful
        """
        logger.info("=" * 60)
        logger.info("PHASE 3: Audio Generation")
        logger.info("=" * 60)
        
        progress_tracker.set_phase("audio_generation")
        
        audio_generator = AudioGenerator()
        self.audio_segments = []
        
        try:
            for chapter in self.chapters:
                chapter_index = chapter.get("index", 0)
                chapter_title = chapter.get("title", f"Chapter {chapter_index}")
                
                logger.info(f"Processing chapter {chapter_index + 1}: {chapter_title}")
                
                for segment in audio_generator.generate_chapter_audio(chapter, chapter_index):
                    self.audio_segments.append(segment)
                
                # Clear chapter segments to save memory
                audio_generator.clear_segments()
                self._force_memory_cleanup()
            
            self.audio_complete = True
            logger.info(f"Audio generation complete: {len(self.audio_segments)} segments")
            return True
            
        except Exception as e:
            logger.error(f"Audio generation failed: {e}")
            return False
        
        finally:
            self._force_memory_cleanup()
    
    def phase_4_encode(self) -> bool:
        """
        Phase 4: Encode audio to Opus and create KOReader manifest.
        
        Returns:
            True if successful
        """
        logger.info("=" * 60)
        logger.info("PHASE 4: Encoding & Packaging")
        logger.info("=" * 60)
        
        progress_tracker.set_phase("encoding")
        
        try:
            packager = AudioPackager(
                book_name=self.book_name,
                source_file=str(self.epub_path)
            )
            
            for segment in self.audio_segments:
                packager.add_segment(segment)
            
            audio_path, manifest_path = packager.save(
                output_dir=config.paths.output_dir,
                audio_filename=f"{self.book_name}.opus",
                manifest_filename=f"{self.book_name}.audio.json"
            )
            
            self.audio_output_path = audio_path
            self.manifest_output_path = manifest_path
            self.encoding_complete = True
            
            logger.info(f"Encoding complete:")
            logger.info(f"  Audio: {audio_path}")
            logger.info(f"  Manifest: {manifest_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Encoding failed: {e}")
            return False
        
        finally:
            # Clear audio data to free memory
            self.audio_segments.clear()
            self._force_memory_cleanup()
    
    def run_full_pipeline(self) -> bool:
        """
        Run the complete pipeline from parsing to encoding.
        
        Returns:
            True if all phases completed successfully
        """
        logger.info("=" * 60)
        logger.info("LUDUAN PIPELINE - Starting Full Run")
        logger.info("=" * 60)
        logger.info(f"Input: {self.epub_path}")
        logger.info(f"Output: {config.paths.output_dir}")
        logger.info(f"Target language: {self.target_language}")
        
        # Start VRAM monitoring
        vram_monitor.start()
        
        try:
            # Check for resume
            if self._check_resume():
                logger.info("Resuming from intermediate translation...")
                # Skip to audio generation
                if not self.phase_3_generate_audio():
                    return False
            else:
                # Full pipeline
                if not self.phase_1_parse():
                    return False
                
                if not self.phase_2_translate():
                    return False
            
            if not self.phase_3_generate_audio():
                return False
            
            if not self.phase_4_encode():
                return False
            
            # Success summary
            logger.info("=" * 60)
            logger.info("PIPELINE COMPLETE")
            logger.info("=" * 60)
            
            summary = progress_tracker.get_summary()
            logger.info(f"Total time: {summary['elapsed']}")
            logger.info(f"Processed: {summary['processed']} items")
            logger.info(f"Failed: {summary['failed']} items")
            logger.info(f"Output files:")
            logger.info(f"  {self.audio_output_path}")
            logger.info(f"  {self.manifest_output_path}")
            
            return True
            
        finally:
            vram_monitor.stop()
    
    def run_translation_only(self) -> bool:
        """Run only the translation phase."""
        logger.info("Running translation only...")
        
        vram_monitor.start()
        
        try:
            if not self.phase_1_parse():
                return False
            
            return self.phase_2_translate()
            
        finally:
            vram_monitor.stop()
    
    def run_audio_only(self) -> bool:
        """Run only audio generation from existing translation."""
        logger.info("Running audio generation only...")
        
        if not self._check_resume():
            logger.error("No intermediate translation found")
            return False
        
        vram_monitor.start()
        
        try:
            if not self.phase_3_generate_audio():
                return False
            
            return self.phase_4_encode()
            
        finally:
            vram_monitor.stop()


def find_epub_files(input_dir: Path) -> list[Path]:
    """Find all EPUB files in a directory."""
    return list(input_dir.glob("*.epub")) + list(input_dir.glob("*.EPUB"))


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Luduan - EPUB to Audiobook Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py book.epub
  python main.py book.epub --language Chinese
  python main.py --input-dir ./epubs --batch
  python main.py book.epub --audio-only  # Requires existing translation
        """
    )
    
    parser.add_argument(
        "epub_file",
        nargs="?",
        type=Path,
        help="Path to EPUB file"
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=config.paths.input_dir,
        help="Input directory for batch processing"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=config.paths.output_dir,
        help="Output directory"
    )
    parser.add_argument(
        "--language",
        type=str,
        default="English",
        help="Target language for translation"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process all EPUBs in input directory"
    )
    parser.add_argument(
        "--translation-only",
        action="store_true",
        help="Only run translation phase"
    )
    parser.add_argument(
        "--audio-only",
        action="store_true",
        help="Only run audio generation (requires existing translation)"
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Disable resume from intermediate files"
    )
    
    args = parser.parse_args()
    
    # Set output directory
    config.paths.output_dir = args.output_dir
    config.paths.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Disable resume if requested
    if args.no_resume:
        config.processing.enable_resume = False
    
    # Determine files to process
    epub_files = []
    
    if args.epub_file:
        if not args.epub_file.exists():
            logger.error(f"File not found: {args.epub_file}")
            sys.exit(1)
        epub_files.append(args.epub_file)
    
    if args.batch or (not args.epub_file and not args.input_dir):
        found_files = find_epub_files(args.input_dir)
        if found_files:
            epub_files.extend(found_files)
            logger.info(f"Found {len(found_files)} EPUB files in {args.input_dir}")
    
    if not epub_files:
        parser.print_help()
        logger.error("No EPUB files to process")
        sys.exit(1)
    
    # Process files
    success_count = 0
    failure_count = 0
    
    for epub_path in epub_files:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Processing: {epub_path.name}")
        logger.info(f"{'=' * 60}\n")
        
        pipeline = LuduanPipeline(epub_path, args.language)
        
        try:
            if args.translation_only:
                success = pipeline.run_translation_only()
            elif args.audio_only:
                success = pipeline.run_audio_only()
            else:
                success = pipeline.run_full_pipeline()
            
            if success:
                success_count += 1
            else:
                failure_count += 1
                
        except KeyboardInterrupt:
            logger.warning("Interrupted by user")
            break
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            failure_count += 1
    
    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("FINAL SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {failure_count}")
    logger.info(f"Total: {success_count + failure_count}")
    
    sys.exit(0 if failure_count == 0 else 1)


if __name__ == "__main__":
    main()
