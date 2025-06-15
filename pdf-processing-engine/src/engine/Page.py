from pdfminer.layout import LTPage, LTTextContainer, LTChar, LTTextLine, LTTextLineHorizontal
from typing import Iterable
from pathlib import Path
import re
SCRIPT_DIR = Path(__file__).parent


class Page():
    def __init__(self, page: LTPage, index: int, title_threshold_prop=0.2) -> None:
        self.max_font_size: int
        self.page = page
        self.index = index
        self.fonts: list[dict] = []
        self.potential_artists: list[str] = []
        self.potential_titles: list = []
        self.title_likelihood_index: int
        self.type: int
        self.artist: str | None
        self.title: str | None

        self._vertical_cutoff = self.page.y1 * title_threshold_prop

        self._compute_attributes()
        self._compute_fonts(self.page)

        self._set_artist()
        self._set_title()

    def set_type(self, type: int):
        self.type = type

    def _set_artist(self) -> None:
        if self.potential_artists:
            self.artist = ' '.join([word.title() if word not in [
                                   'DE', 'E'] else word.lower() for word in self.potential_artists[0].split(' ')])
        else:
            self.artist = None

    def _set_title(self) -> None:
        if self.potential_titles:
            self.title = self.potential_titles[0][0]
        else:
            self.title = None

    def _compute_attributes(self):
        self.max_font_size = 0
        self._search_and_compute_attributes(self.page)
        self.title_likelihood_index = sum([char.isalpha() and char == char.upper()
                                           for word in self.potential_artists for char in word])

    def _search_and_compute_attributes(self, element):
        self._check_size(element)
        self._store_title_words(element)
        if isinstance(element, Iterable):
            for subelement in element:
                self._search_and_compute_attributes(subelement)

    def _check_size(self, element):
        if hasattr(element, 'size') and element.size > self.max_font_size:
            self.max_font_size = element.size

    def _store_title_words(self, element):
        if isinstance(element, LTTextLineHorizontal):
            text = element.get_text().strip()
            if self._is_potential_artist_name(element.y1, text):
                self.potential_artists.append(text)

            average_font = self._get_average_font(element)
            font_names = self._get_font_names(element)
            if self._is_potential_title(element, text, average_font, font_names):
                self.potential_titles.append(
                    [text, element.x0, element.x1, element.y0, element.y1, average_font, font_names])

    def _get_font_names(self, element: LTTextLineHorizontal):
        fonts = []
        if isinstance(element, Iterable):
            for char in element:
                if isinstance(char, LTChar):
                    fonts.append(char.fontname)
        return fonts

    def _get_average_font(self, element: LTTextLineHorizontal):
        sizes = []
        if isinstance(element, Iterable):
            for char in element:
                if isinstance(char, LTChar):
                    sizes.append(char.size)
        return sum(sizes) / len(sizes)

    def _is_potential_title(self, element: LTTextLineHorizontal, text: str, average_font: float, font_names: list[str]) -> bool:
        if element.y1 < self._vertical_cutoff:
            return False
        elif len(text) <= 1:
            return False
        elif re.search(r'\(|\)|=|@', text) is not None:
            return False
        elif re.search(r'\b(song|book)\b', text, re.IGNORECASE) is not None:
            return False
        elif sum([i.isnumeric() for i in text]) > 2:
            return False
        elif re.search(r'[mM][0-9]', text) is not None:
            return False
        elif '¢' in text or '==' in text or '——' in text:
            return False
        elif sum([char in '—-~=_|:<>' for char in text]) > 1:
            return False
        elif re.search(r'(?=.*[0-9])(?=.*[—\-\~\=\_\|@])', text) is not None:
            return False
        elif average_font < 15:
            return False
        elif not sum(['Bold' in font for font in font_names]):
            return True
            return False
        return True

    def _is_potential_artist_name(self, height: float, text: str) -> bool:
        lower = text.lower()
        if height < self._vertical_cutoff:
            return False
        elif len(text) < 5 or len(text.split(' ')) > 7:
            return False
        elif sum([char.isnumeric() or char in '—-~=_|:;()<>' for char in text]) > 1:
            return False
        elif '(' in text and ')' in text:
            return False
        elif 'III' in text:
            return False
        elif re.search(r'(?=.*[0-9])(?=.*[—\-\~\=\_\|@])', text) is not None:
            return False
        elif re.search(r'[mMA-G][0-9#]', text) is not None:
            return False
        elif sum([char in '—-~=_|:;()<>' for char in text]) > 1:
            return False
        elif 'song' in lower or 'book' in lower:
            return False
        elif 'Gime cHIGE' in text or 'ALG EDTIG' in text or 'FIED' in text or 'FISTS' in text:
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

    def __repr__(self) -> str:
        return f'Page(index={self.index}, max_font={self.max_font_size})'
