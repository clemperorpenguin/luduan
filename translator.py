"""
The Spiritual Transmission - Translation Engine.
Handles batch translation of EPUB text using Qwen 3.5 model.
Designed to run independently with intermediate JSON output.
"""

import json
import gc
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Generator

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from accelerate import Accelerator
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None

from config import config
from logger import logger, vram_monitor
from parser import EPUBParser, ParagraphData


@dataclass
class TranslatedParagraph:
    """Represents a translated paragraph with metadata."""
    chapter_index: int
    chapter_title: str
    paragraph_index: int
    source_text: str
    translated_text: str
    html_path: str = ""
    translation_timestamp: str = ""
    model_used: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "chapter_index": self.chapter_index,
            "chapter_title": self.chapter_title,
            "paragraph_index": self.paragraph_index,
            "source_text": self.source_text,
            "translated_text": self.translated_text,
            "html_path": self.html_path,
            "translation_timestamp": self.translation_timestamp,
            "model_used": self.model_used
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TranslatedParagraph':
        """Create from dictionary."""
        return cls(
            chapter_index=data["chapter_index"],
            chapter_title=data["chapter_title"],
            paragraph_index=data["paragraph_index"],
            source_text=data["source_text"],
            translated_text=data["translated_text"],
            html_path=data.get("html_path", ""),
            translation_timestamp=data.get("translation_timestamp", ""),
            model_used=data.get("model_used", "")
        )


class TranslationEngine:
    """
    Translation engine using Qwen models.
    
    Features:
    - Supports local GGUF/Safetensors or HuggingFace models
    - 4-bit quantization for VRAM efficiency
    - Batch processing with configurable size
    - Intermediate JSON saving for resume capability
    - Culturally aware translation prompts for Wuxia/Xianxia
    """
    
    # System prompt for maintaining Wuxia/Xianxia terminology
    SYSTEM_PROMPT = """You are a professional literary translator specializing in Chinese 
web novels, particularly Wuxia (martial arts) and Xianxia (cultivation) genres.

Translation Guidelines:
1. Maintain the original tone and style - formal, classical, yet accessible
2. Preserve cultural terms and honorifics where appropriate
3. For cultivation terms, use established conventions:
   - 道友 (Daoist friend) -> "Fellow Daoist" or "Friend"
   - 前辈 (Senior) -> "Senior" or "Elder"
   - 晚辈 (Junior) -> "Junior" or "this junior"
   - 宗门 (Sect) -> "Sect"
   - 功法 (Cultivation method) -> "cultivation technique" or "method"
   - 丹药 (Pill) -> "pill" or "elixir"
   - 法宝 (Treasure) -> "treasure" or "dharma treasure"
   - 灵气 (Qi) -> "spiritual energy" or "Qi"
   - 修炼 (Cultivate) -> "cultivate" or "train"
4. Keep names in pinyin without translation
5. Translate idioms meaningfully rather than literally
6. Maintain paragraph structure and flow

Output ONLY the translation, no explanations or notes."""

    def __init__(self, target_language: str = "English"):
        """
        Initialize the translation engine.
        
        Args:
            target_language: Target language for translation
        """
        self.target_language = target_language
        self.model = None
        self.tokenizer = None
        self.accelerator = None
        self.is_loaded = False
        self.translated_paragraphs: list[TranslatedParagraph] = []
        
        # Build translation prompt
        self.translation_prompt = (
            f"Translate the following Chinese text to {target_language}. "
            f"Maintain the Wuxia/Xianxia style and terminology:\n\n"
        )
        
        logger.info(f"Translation engine initialized (target: {target_language})")
    
    def load_model(self) -> bool:
        """
        Load the translation model with quantization.
        
        Returns:
            True if successful
        """
        if not TORCH_AVAILABLE:
            logger.error("PyTorch not available. Install with: pip install torch transformers accelerate")
            return False
        
        if self.is_loaded:
            logger.info("Model already loaded")
            return True
        
        try:
            model_path = str(config.translation.model_path) if config.translation.model_path else config.translation.model_name
            logger.info(f"Loading model: {model_path}")
            
            # Set up accelerator
            self.accelerator = Accelerator()
            
            # Configure quantization
            if config.translation.use_4bit:
                from transformers import BitsAndBytesConfig
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type=config.translation.bnb_4bit_quant_type,
                    bnb_4bit_compute_dtype=getattr(torch, config.translation.bnb_4bit_compute_dtype),
                    bnb_4bit_use_double_quant=True
                )
                logger.info("Using 4-bit quantization")
            elif config.translation.use_8bit:
                bnb_config = {"load_in_8bit": True}
                logger.info("Using 8-bit quantization")
            else:
                bnb_config = {}
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                trust_remote_code=True,
                cache_dir=str(config.paths.cache_dir)
            )
            
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Load model
            self.model = AutoModelForCausalLM.from_pretrained(
                model_path,
                quantization_config=bnb_config if bnb_config else None,
                device_map="auto" if not bnb_config else None,
                trust_remote_code=True,
                cache_dir=str(config.paths.cache_dir),
                torch_dtype=getattr(torch, config.translation.bnb_4bit_compute_dtype)
            )
            
            if not bnb_config:
                self.model = self.accelerator.prepare(self.model)
            
            self.model.eval()
            self.is_loaded = True
            
            vram_monitor.log_now()
            logger.info("Model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
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
        logger.info("Model unloaded, VRAM freed")
    
    def _build_messages(self, source_text: str) -> list[dict]:
        """
        Build message list for chat model.
        
        Args:
            source_text: Source text to translate
            
        Returns:
            Message list for model input
        """
        return [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": self.translation_prompt + source_text}
        ]
    
    def translate_text(self, source_text: str) -> str:
        """
        Translate a single text string.
        
        Args:
            source_text: Text to translate
            
        Returns:
            Translated text
        """
        if not self.is_loaded:
            logger.error("Model not loaded. Call load_model() first.")
            return ""
        
        try:
            messages = self._build_messages(source_text)
            
            # Apply chat template
            input_text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            
            # Tokenize
            inputs = self.tokenizer(
                input_text,
                return_tensors="pt",
                truncation=True,
                max_length=config.translation.max_new_tokens + 512
            )
            
            if TORCH_AVAILABLE and torch.cuda.is_available():
                inputs = {k: v.to(self.accelerator.device) for k, v in inputs.items()}
            
            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=config.translation.max_new_tokens,
                    temperature=config.translation.temperature,
                    top_p=config.translation.top_p,
                    do_sample=config.translation.do_sample,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode and extract response
            response = self.tokenizer.decode(
                outputs[0][inputs['input_ids'].shape[1]:],
                skip_special_tokens=True
            ).strip()
            
            # Clean up response (remove any trailing notes)
            response = self._clean_translation(response)
            
            return response
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return source_text  # Return original on failure
    
    def _clean_translation(self, text: str) -> str:
        """
        Clean up translation output.
        
        Args:
            text: Raw model output
            
        Returns:
            Cleaned translation
        """
        # Remove common AI response patterns
        patterns_to_remove = [
            "Here is the translation:",
            "Translation:",
            "The translation is:",
        ]
        
        for pattern in patterns_to_remove:
            if text.startswith(pattern):
                text = text[len(pattern):].strip()
        
        return text.strip()
    
    def translate_batch(self, texts: list[str]) -> list[str]:
        """
        Translate a batch of texts.
        
        Args:
            texts: List of texts to translate
            
        Returns:
            List of translated texts
        """
        results = []
        for i, text in enumerate(texts):
            logger.debug(f"Translating {i + 1}/{len(texts)}")
            results.append(self.translate_text(text))
        return results
    
    def translate_paragraph(self, para_data: ParagraphData) -> TranslatedParagraph:
        """
        Translate a single paragraph with metadata.
        
        Args:
            para_data: ParagraphData from parser
            
        Returns:
            TranslatedParagraph with translation
        """
        translated_text = self.translate_text(para_data.source_text)
        
        return TranslatedParagraph(
            chapter_index=para_data.chapter_index,
            chapter_title=para_data.chapter_title,
            paragraph_index=para_data.paragraph_index,
            source_text=para_data.source_text,
            translated_text=translated_text,
            html_path=para_data.html_path,
            translation_timestamp=datetime.now().isoformat(),
            model_used=config.translation.model_name
        )
    
    def save_intermediate(self, output_path: Path):
        """
        Save translated paragraphs to intermediate JSON.
        
        Args:
            output_path: Path to save JSON file
        """
        data = {
            "metadata": {
                "source_language": "Chinese",
                "target_language": self.target_language,
                "model": config.translation.model_name,
                "created_at": datetime.now().isoformat(),
                "total_paragraphs": len(self.translated_paragraphs)
            },
            "chapters": {}
        }
        
        # Group by chapter
        for para in self.translated_paragraphs:
            chapter_key = f"{para.chapter_index:04d}_{para.chapter_title}"
            if chapter_key not in data["chapters"]:
                data["chapters"][chapter_key] = {
                    "index": para.chapter_index,
                    "title": para.chapter_title,
                    "paragraphs": []
                }
            data["chapters"][chapter_key]["paragraphs"].append(para.to_dict())
        
        # Sort chapters
        data["chapters"] = dict(sorted(data["chapters"].items()))
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Intermediate saved: {output_path} ({len(self.translated_paragraphs)} paragraphs)")
    
    def load_intermediate(self, input_path: Path) -> bool:
        """
        Load translated paragraphs from intermediate JSON (for resume).
        
        Args:
            input_path: Path to JSON file
            
        Returns:
            True if successful
        """
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.translated_paragraphs = []
            for chapter in data.get("chapters", {}).values():
                for para_dict in chapter.get("paragraphs", []):
                    self.translated_paragraphs.append(
                        TranslatedParagraph.from_dict(para_dict)
                    )
            
            logger.info(f"Loaded {len(self.translated_paragraphs)} paragraphs from intermediate")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load intermediate: {e}")
            return False
    
    def get_translated_paragraphs(self) -> list[TranslatedParagraph]:
        """Get all translated paragraphs."""
        return self.translated_paragraphs


class BatchTranslator:
    """
    High-level batch translation orchestrator.
    Handles the full EPUB translation pipeline.
    """
    
    def __init__(self, epub_path: Path, target_language: str = "English"):
        """
        Initialize batch translator.
        
        Args:
            epub_path: Path to EPUB file
            target_language: Target language
        """
        self.epub_path = Path(epub_path)
        self.target_language = target_language
        self.engine = TranslationEngine(target_language)
        self.parser = EPUBParser(epub_path)
        self.intermediate_path: Optional[Path] = None
        
        # Generate output filename
        book_name = epub_path.stem
        self.output_name = book_name
    
    def translate_full(
        self,
        save_intermediate: bool = True,
        resume: bool = True
    ) -> Path:
        """
        Translate entire EPUB.
        
        Args:
            save_intermediate: Save intermediate JSON
            resume: Try to resume from existing intermediate
            
        Returns:
            Path to intermediate JSON file
        """
        # Check for existing intermediate (resume)
        self.intermediate_path = config.paths.output_dir / f"{self.output_name}_translated_tome.json"
        
        if resume and self.intermediate_path.exists():
            logger.info(f"Found existing intermediate: {self.intermediate_path}")
            if self.engine.load_intermediate(self.intermediate_path):
                logger.info("Resuming from intermediate...")
                # Could add logic to skip already translated paragraphs
                return self.intermediate_path
        
        # Load EPUB
        if not self.parser.load():
            raise RuntimeError(f"Failed to load EPUB: {self.epub_path}")
        
        # Load model
        if not self.engine.load_model():
            raise RuntimeError("Failed to load translation model")
        
        # Start tracking
        from logger import progress_tracker
        progress_tracker.set_phase("translation")
        progress_tracker.start_tracking()
        
        total_paragraphs = sum(
            1 for _ in self.parser.parse()
        )
        progress_tracker.total_paragraphs = total_paragraphs
        
        # Re-parse (generator was consumed)
        self.parser = EPUBParser(self.epub_path)
        self.parser.load()
        
        # Translate
        try:
            for i, para_data in enumerate(self.parser.parse()):
                progress_tracker.current_paragraph = i + 1
                progress_tracker.set_chapter_progress(
                    para_data.chapter_index + 1,
                    total_paragraphs  # Approximate
                )
                
                translated = self.engine.translate_paragraph(para_data)
                self.engine.translated_paragraphs.append(translated)
                progress_tracker.increment_processed()
                
                # Periodic save
                if save_intermediate and (i + 1) % config.processing.intermediate_save_interval == 0:
                    self.engine.save_intermediate(self.intermediate_path)
                    vram_monitor.log_now()
            
            # Final save
            if save_intermediate:
                self.engine.save_intermediate(self.intermediate_path)
            
            logger.info(f"Translation complete: {len(self.engine.translated_paragraphs)} paragraphs")
            return self.intermediate_path
            
        finally:
            # Unload model to free VRAM for next phase
            if config.processing.unload_models_between_phases:
                self.engine.unload_model()
    
    def get_chapters(self) -> list[dict]:
        """
        Get translated chapters as list of dicts.
        
        Returns:
            List of chapter dictionaries
        """
        chapters = {}
        for para in self.engine.get_translated_paragraphs():
            chapter_key = para.chapter_index
            if chapter_key not in chapters:
                chapters[chapter_key] = {
                    "index": para.chapter_index,
                    "title": para.chapter_title,
                    "paragraphs": []
                }
            chapters[chapter_key]["paragraphs"].append(para.to_dict())
        
        return [chapters[k] for k in sorted(chapters.keys())]


def translate_epub(
    epub_path: Path,
    target_language: str = "English",
    save_intermediate: bool = True
) -> Path:
    """
    Convenience function to translate an EPUB.
    
    Args:
        epub_path: Path to EPUB file
        target_language: Target language
        save_intermediate: Whether to save intermediate JSON
        
    Returns:
        Path to intermediate JSON file
    """
    translator = BatchTranslator(epub_path, target_language)
    return translator.translate_full(save_intermediate=save_intermediate)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python translator.py <epub_file> [target_language]")
        sys.exit(1)
    
    epub_file = Path(sys.argv[1])
    target_lang = sys.argv[2] if len(sys.argv) > 2 else "English"
    
    translator = BatchTranslator(epub_file, target_lang)
    output_path = translator.translate_full()
    print(f"\nTranslation saved to: {output_path}")
