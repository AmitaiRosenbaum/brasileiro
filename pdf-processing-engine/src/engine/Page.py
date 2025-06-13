import ocrmypdf
from pypdf import PdfReader
from pdfminer.high_level import extract_pages as pdf_text_extraction
from pdfminer.layout import LTPage, LTTextContainer, LTChar, LTTextLine
from typing import Iterable, Any, Iterator
from pathlib import Path
SCRIPT_DIR = Path(__file__).parent


class Page():
    def __init__(self, page: LTPage, index: int) -> None:
        self.max_font_size: int
        self.page = page
        self.index = index
        self.fonts: list[dict] = [{}]

        self._compute_max_size()
        self._compute_fonts()

    def _compute_max_size(self):
        self.max_font_size = 0
        self._search_max_font_size(self.page)

    def _search_max_font_size(self, element):
        self._check_size(element)
        if isinstance(element, Iterable):
            for subelement in element:
                self._check_size(subelement)
                self._search_max_font_size(subelement)

    def _check_size(self, element):
        if hasattr(element, 'size') and element.size > self.max_font_size:
            self.max_font_size = element.size

    def _compute_fonts(self):
        for element in self.page:
            if isinstance(element, LTTextContainer):
                for text_line in element:
                    if isinstance(text_line, LTTextLine):
                        for character in text_line:
                            if isinstance(character, LTChar):
                                self.fonts = self.fonts + \
                                    [{'size': character.size,
                                        'font': character.fontname}]

    def __repr__(self) -> str:
        return f'Page(index={self.index}, max_font={self.max_font_size})'
