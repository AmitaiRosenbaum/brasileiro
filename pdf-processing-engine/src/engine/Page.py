from pdfminer.layout import LTPage, LTTextContainer, LTChar, LTTextLine, LTTextLineHorizontal
from typing import Iterable
from pathlib import Path
SCRIPT_DIR = Path(__file__).parent


class Page():
    def __init__(self, page: LTPage, index: int, title_threshold_prop=0.2) -> None:
        self.max_font_size: int
        self.page = page
        self.index = index
        self.fonts: list[dict] = []
        self.upper_word_count: int = 0
        self.words: list[str] = []
        self._title_count: int

        self._vertical_cutoff = self.page.y1 * title_threshold_prop

        self._compute_attributes()
        self._compute_fonts(self.page)

    def _compute_attributes(self):
        self.max_font_size = 0
        self._search_and_compute_attributes(self.page)
        self._title_count = sum([char.isalpha() and char == char.upper()
                                for word in self.words for char in word])

    def _search_and_compute_attributes(self, element):
        self._check_size(element)
        self._store_title_words(element)
        if isinstance(element, Iterable):
            for subelement in element:
                self._check_size(subelement)
                self._search_and_compute_attributes(subelement)

    def _check_size(self, element):
        if hasattr(element, 'size') and element.size > self.max_font_size:
            self.max_font_size = element.size

    def _store_title_words(self, element):
        if isinstance(element, LTTextLineHorizontal):
            text = element.get_text().strip()
            if self._is_potential_title(element.y1, text):
                self.words.append(text)

    def _is_potential_title(self, height: float, text: str) -> bool:
        lower = text.lower()
        if height < self._vertical_cutoff:
            return False
        elif len(text) < 5:
            return False
        elif sum([char.isnumeric() for char in text]) > 2:
            return False
        elif '(' in text and ')' in text:
            return False
        elif 'III' in text:
            return False
        elif 'song' in lower or 'book' in lower:
            return False
        elif not sum([char not in 'IVW' for char in text]):
            return False
        else:
            capitals = [reg.isalpha() and reg == cap for reg, cap in zip(
                text, text.upper())]
            if self._get_max_streak(capitals) < 4:
                return False
        return True

    def _get_max_streak(self, xs: list[bool]):
        max_streak = 0
        streak = 0
        for x in xs:
            if not x:
                streak = 0
            else:
                streak += 1
                if streak > max_streak:
                    max_streak = streak
        return max_streak

    def _compute_fonts(self, element):
        if isinstance(element, LTChar):
            self.fonts = self.fonts + [{'size': element.size,
                                        'font': element.fontname}]
        elif isinstance(element, Iterable):
            for subelement in element:
                self._compute_fonts(subelement)

    def _compute_upper_word_count(self):
        pass

    def __repr__(self) -> str:
        return f'Page(index={self.index}, max_font={self.max_font_size})'
