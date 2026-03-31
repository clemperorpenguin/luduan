"""
The Scroll Parser - Text Extraction Module.
Safely extracts text from EPUB files without modifying the original.
Uses ebooklib and BeautifulSoup4 for robust HTML parsing.
"""

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Generator, Optional

from ebooklib import epub, ITEM_DOCUMENT
from bs4 import BeautifulSoup, NavigableString

from config import config
from logger import logger


@dataclass
class ParagraphData:
    """Represents a single paragraph extracted from the EPUB."""
    chapter_index: int
    chapter_title: str
    paragraph_index: int
    source_text: str
    html_path: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "chapter_index": self.chapter_index,
            "chapter_title": self.chapter_title,
            "paragraph_index": self.paragraph_index,
            "source_text": self.source_text,
            "html_path": self.html_path
        }


@dataclass
class ChapterData:
    """Represents a chapter with all its paragraphs."""
    index: int
    title: str
    paragraphs: list[ParagraphData] = field(default_factory=list)
    html_path: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "index": self.index,
            "title": self.title,
            "paragraphs": [p.to_dict() for p in self.paragraphs],
            "html_path": self.html_path
        }


class EPUBParser:
    """
    Parser for extracting text from EPUB files.
    
    Features:
    - Non-destructive reading (original file unchanged)
    - Filters empty strings and chapter headings
    - Configurable minimum paragraph length
    - Generator-based for memory efficiency
    """
    
    def __init__(self, epub_path: Path):
        """
        Initialize the parser with an EPUB file path.
        
        Args:
            epub_path: Path to the EPUB file
        """
        self.epub_path = Path(epub_path)
        self.book: Optional[epub.EpubBook] = None
        self.chapters: list[ChapterData] = []
        
        # Compile heading patterns for filtering
        self.heading_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in config.processing.heading_patterns
        ]
        
        logger.info(f"Parser initialized for: {self.epub_path.name}")
    
    def load(self) -> bool:
        """
        Load the EPUB file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.epub_path.exists():
                logger.error(f"EPUB file not found: {self.epub_path}")
                return False
                
            if not self.epub_path.suffix.lower() == '.epub':
                logger.warning(f"File may not be a valid EPUB: {self.epub_path}")
            
            self.book = epub.read_epub(self.epub_path, {'ignore_ncx': True})
            logger.info(f"EPUB loaded: {self.book.get_metadata('DC', 'title')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load EPUB: {e}")
            return False
    
    def _is_heading(self, text: str) -> bool:
        """
        Check if text matches chapter heading patterns.
        
        Args:
            text: Text to check
            
        Returns:
            True if text appears to be a chapter heading
        """
        if not config.processing.skip_chapter_headings:
            return False
            
        text = text.strip()
        for pattern in self.heading_patterns:
            if pattern.search(text):
                return True
        return False
    
    def _is_valid_paragraph(self, text: str) -> bool:
        """
        Check if text qualifies as a valid paragraph for processing.
        
        Args:
            text: Text to validate
            
        Returns:
            True if text should be processed
        """
        if not text:
            return False
            
        text = text.strip()
        
        # Check minimum length
        if len(text) < config.processing.min_paragraph_length:
            return False
        
        # Filter out headings
        if self._is_heading(text):
            return False
        
        # Filter out pure whitespace or special characters
        if not re.search(r'[\w\u4e00-\u9fff]', text):
            return False
            
        return True
    
    def _extract_text_from_html(self, html_content: bytes) -> list[str]:
        """
        Extract clean text paragraphs from HTML content.
        
        Args:
            html_content: Raw HTML bytes from EPUB item
            
        Returns:
            List of clean text paragraphs
        """
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Remove script and style elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer']):
                element.decompose()
            
            paragraphs = []
            
            # Find all <p> tags
            for p_tag in soup.find_all('p'):
                text = p_tag.get_text(strip=True)
                if self._is_valid_paragraph(text):
                    paragraphs.append(text)
            
            # If no <p> tags, try other block elements
            if not paragraphs:
                for element in soup.find_all(['div', 'span', 'section']):
                    text = element.get_text(strip=True)
                    if self._is_valid_paragraph(text):
                        paragraphs.append(text)
            
            # Fallback: extract any meaningful text
            if not paragraphs:
                for element in soup.body or soup:
                    if isinstance(element, NavigableString):
                        text = str(element).strip()
                        if self._is_valid_paragraph(text):
                            paragraphs.append(text)
                    else:
                        text = element.get_text(strip=True)
                        if self._is_valid_paragraph(text):
                            paragraphs.append(text)
            
            return paragraphs
            
        except Exception as e:
            logger.error(f"HTML parsing error: {e}")
            return []
    
    def _get_chapter_title(self, item) -> str:
        """
        Extract chapter title from EPUB item.
        
        Args:
            item: EPUB item
            
        Returns:
            Chapter title string
        """
        # Try to get title from metadata
        if hasattr(item, 'title') and item.title:
            return item.title.strip()
        
        # Try to extract from HTML content
        try:
            soup = BeautifulSoup(item.get_content(), 'lxml')
            title_tag = soup.find('title')
            if title_tag and title_tag.string:
                return title_tag.string.strip()
            
            # Try h1, h2 headings
            for heading in soup.find_all(['h1', 'h2']):
                text = heading.get_text(strip=True)
                if text and len(text) < 200:  # Reasonable title length
                    return text
        except Exception:
            pass
        
        # Fallback to filename
        return Path(item.get_name()).stem
    
    def parse(self) -> Generator[ParagraphData, None, None]:
        """
        Generator that yields paragraphs one at a time.
        Memory-efficient for large EPUBs.
        
        Yields:
            ParagraphData objects containing text and metadata
        """
        if not self.book:
            logger.error("EPUB not loaded. Call load() first.")
            return
        
        chapter_index = 0
        
        for item in self.book.get_items_of_kind(ITEM_DOCUMENT):
            chapter_title = self._get_chapter_title(item)
            logger.debug(f"Parsing chapter {chapter_index + 1}: {chapter_title}")
            
            paragraphs = self._extract_text_from_html(item.get_content())
            
            for para_index, text in enumerate(paragraphs):
                yield ParagraphData(
                    chapter_index=chapter_index,
                    chapter_title=chapter_title,
                    paragraph_index=para_index,
                    source_text=text,
                    html_path=item.get_name()
                )
            
            if paragraphs:
                chapter_index += 1
    
    def parse_all(self) -> list[ChapterData]:
        """
        Parse entire EPUB and return structured chapter data.
        Stores results in memory - use parse() generator for large files.
        
        Returns:
            List of ChapterData objects
        """
        if not self.book:
            logger.error("EPUB not loaded. Call load() first.")
            return []
        
        self.chapters = []
        chapter_map = {}  # chapter_index -> ChapterData
        
        for para_data in self.parse():
            chapter_idx = para_data.chapter_index
            
            if chapter_idx not in chapter_map:
                chapter_map[chapter_idx] = ChapterData(
                    index=chapter_idx,
                    title=para_data.chapter_title,
                    paragraphs=[],
                    html_path=para_data.html_path
                )
            
            chapter_map[chapter_idx].paragraphs.append(para_data)
        
        # Convert to sorted list
        self.chapters = [chapter_map[i] for i in sorted(chapter_map.keys())]
        
        logger.info(f"Parsed {len(self.chapters)} chapters, "
                   f"{sum(len(c.paragraphs) for c in self.chapters)} paragraphs total")
        
        return self.chapters
    
    def get_statistics(self) -> dict:
        """
        Get parsing statistics.
        
        Returns:
            Dictionary with parsing statistics
        """
        if not self.chapters:
            self.parse_all()
        
        total_paragraphs = sum(len(c.paragraphs) for c in self.chapters)
        total_chars = sum(
            len(p.source_text) 
            for c in self.chapters 
            for p in c.paragraphs
        )
        
        return {
            "chapters": len(self.chapters),
            "paragraphs": total_paragraphs,
            "total_characters": total_chars,
            "avg_paragraph_length": total_chars / total_paragraphs if total_paragraphs else 0,
            "avg_chapter_length": total_chars / len(self.chapters) if self.chapters else 0
        }


def parse_epub(epub_path: Path) -> Generator[ParagraphData, None, None]:
    """
    Convenience function to parse an EPUB file.
    
    Args:
        epub_path: Path to the EPUB file
        
    Yields:
        ParagraphData objects
    """
    parser = EPUBParser(epub_path)
    if parser.load():
        yield from parser.parse()


def parse_epub_to_dict(epub_path: Path) -> list[dict]:
    """
    Parse EPUB and return as list of dictionaries.
    
    Args:
        epub_path: Path to the EPUB file
        
    Returns:
        List of paragraph dictionaries
    """
    parser = EPUBParser(epub_path)
    if parser.load():
        chapters = parser.parse_all()
        return [c.to_dict() for c in chapters]
    return []


if __name__ == "__main__":
    # Test the parser
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python parser.py <epub_file>")
        sys.exit(1)
    
    test_path = Path(sys.argv[1])
    parser = EPUBParser(test_path)
    
    if parser.load():
        stats = parser.get_statistics()
        print(f"\nParsing Statistics:")
        print(f"  Chapters: {stats['chapters']}")
        print(f"  Paragraphs: {stats['paragraphs']}")
        print(f"  Total characters: {stats['total_characters']:,}")
        print(f"  Avg paragraph length: {stats['avg_paragraph_length']:.1f}")
        
        # Show first few paragraphs
        print("\nFirst 5 paragraphs:")
        for i, para in enumerate(parser.parse()):
            if i >= 5:
                break
            print(f"  [{para.chapter_index}:{para.paragraph_index}] {para.source_text[:80]}...")
