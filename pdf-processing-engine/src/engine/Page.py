from pdfminer.layout import LTPage, LTTextContainer, LTChar, LTTextLine
from typing import Iterable
from pathlib import Path
SCRIPT_DIR = Path(__file__).parent


class Page():
    def __init__(self, page: LTPage, index: int) -> None:
        self.max_font_size: int
        self.page = page
        self.index = index
        self.fonts: list[dict] = [{}]

        self._compute_max_size()
        self._compute_fonts(self.page)

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

    def _compute_fonts(self, element):
        if isinstance(element, LTChar):
            self.fonts = self.fonts + [{'size': element.size,
                                        'font': element.fontname}]
        elif isinstance(element, Iterable):
            for subelement in element:
                self._compute_fonts(subelement)

    def __repr__(self) -> str:
        return f'Page(index={self.index}, max_font={self.max_font_size})'
