from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
import re
from typing import Iterable

from pdfminer.layout import LTChar, LTPage, LTTextLineHorizontal


CHORD_RE = re.compile(r"\b[A-G](?:#|b)?(?:m|maj|min|dim|aug|sus)?[0-9]?\b")
JUNK_CHARS = set("—-~=_|:;<>@¢")


@dataclass(frozen=True)
class TextLine:
    text: str
    x0: float
    x1: float
    y0: float
    y1: float
    average_font_size: float
    max_font_size: float
    font_names: tuple[str, ...]

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def alpha_count(self) -> int:
        return sum(char.isalpha() for char in self.text)

    @property
    def uppercase_ratio(self) -> float:
        if not self.alpha_count:
            return 0
        return sum(char.isalpha() and char.isupper() for char in self.text) / self.alpha_count

    @property
    def digit_count(self) -> int:
        return sum(char.isdigit() for char in self.text)

    @property
    def junk_count(self) -> int:
        return sum(char in JUNK_CHARS for char in self.text)

    @property
    def word_count(self) -> int:
        return len(self.text.split())

    @property
    def has_bold_font(self) -> bool:
        return any("bold" in font.lower() for font in self.font_names)

    @property
    def chord_token_count(self) -> int:
        return len(CHORD_RE.findall(self.text))


@dataclass(frozen=True)
class PageFeatures:
    page_width: float
    page_height: float
    lines: tuple[TextLine, ...]
    max_font_size: float
    mean_font_size: float
    large_line_count: int
    top_line_count: int
    top_large_line_count: int
    centered_large_line_count: int
    alpha_count: int
    uppercase_ratio: float
    chord_token_count: int
    junk_char_count: int
    largest_line_y_ratio: float
    largest_line_center_offset: float
    title_candidate_score: float
    artist_candidate_score: float

    @classmethod
    def from_page(cls, page: LTPage) -> "PageFeatures":
        lines = tuple(_extract_text_lines(page))
        font_sizes = [
            line.average_font_size for line in lines if line.average_font_size > 0
        ]
        max_font_size = max((line.max_font_size for line in lines), default=0)
        mean_font_size = mean(font_sizes) if font_sizes else 0
        large_threshold = max(15, mean_font_size * 1.8)
        top_cutoff = page.y1 * 0.55

        large_lines = [
            line for line in lines if line.max_font_size >= large_threshold
        ]
        top_lines = [line for line in lines if line.y1 >= top_cutoff]
        top_large_lines = [
            line for line in large_lines if line.y1 >= top_cutoff
        ]
        centered_large_lines = [
            line
            for line in large_lines
            if _line_center_offset(line, page.x1) <= 0.22
        ]

        alpha_count = sum(line.alpha_count for line in lines)
        uppercase_count = sum(
            char.isalpha() and char.isupper()
            for line in lines
            for char in line.text
        )
        largest_line = max(lines, key=lambda line: line.max_font_size, default=None)

        return cls(
            page_width=page.x1,
            page_height=page.y1,
            lines=lines,
            max_font_size=max_font_size,
            mean_font_size=mean_font_size,
            large_line_count=len(large_lines),
            top_line_count=len(top_lines),
            top_large_line_count=len(top_large_lines),
            centered_large_line_count=len(centered_large_lines),
            alpha_count=alpha_count,
            uppercase_ratio=uppercase_count / alpha_count if alpha_count else 0,
            chord_token_count=sum(line.chord_token_count for line in lines),
            junk_char_count=sum(line.junk_count for line in lines),
            largest_line_y_ratio=(
                largest_line.y1 / page.y1 if largest_line and page.y1 else 0
            ),
            largest_line_center_offset=(
                _line_center_offset(largest_line, page.x1) if largest_line else 1
            ),
            title_candidate_score=max(
                (_title_line_score(line, page.x1, page.y1, max_font_size) for line in lines),
                default=0,
            ),
            artist_candidate_score=max(
                (_artist_line_score(line, page.y1) for line in lines),
                default=0,
            ),
        )

    def as_vector(self) -> tuple[float, ...]:
        return (
            self.max_font_size,
            self.mean_font_size,
            self.large_line_count,
            self.top_line_count,
            self.top_large_line_count,
            self.centered_large_line_count,
            self.uppercase_ratio,
            self.chord_token_count,
            self.junk_char_count,
            self.largest_line_y_ratio,
            self.largest_line_center_offset,
            self.title_candidate_score,
            self.artist_candidate_score,
        )


def _extract_text_lines(element: object) -> list[TextLine]:
    lines: list[TextLine] = []
    if isinstance(element, LTTextLineHorizontal):
        line = _to_text_line(element)
        if line is not None:
            lines.append(line)
    elif isinstance(element, Iterable):
        for child in element:
            lines.extend(_extract_text_lines(child))
    return lines


def _to_text_line(element: LTTextLineHorizontal) -> TextLine | None:
    text = element.get_text().strip()
    if not text:
        return None

    chars = [char for char in element if isinstance(char, LTChar)]
    if not chars:
        return TextLine(text, element.x0, element.x1, element.y0, element.y1, 0, 0, ())

    sizes = [char.size for char in chars]
    return TextLine(
        text=text,
        x0=element.x0,
        x1=element.x1,
        y0=element.y0,
        y1=element.y1,
        average_font_size=sum(sizes) / len(sizes),
        max_font_size=max(sizes),
        font_names=tuple(char.fontname for char in chars),
    )


def _line_center_offset(line: TextLine, page_width: float) -> float:
    if not page_width:
        return 1
    page_center = page_width / 2
    line_center = (line.x0 + line.x1) / 2
    return abs(line_center - page_center) / page_width


def _title_line_score(
    line: TextLine,
    page_width: float,
    page_height: float,
    page_max_font_size: float,
) -> float:
    if line.word_count > 8 or line.alpha_count < 2:
        return 0
    if re.search(r"\b(song|book)\b", line.text, re.IGNORECASE):
        return 0

    font_score = line.max_font_size / page_max_font_size if page_max_font_size else 0
    position_score = line.y1 / page_height if page_height else 0
    centered_score = 1 - min(_line_center_offset(line, page_width) / 0.5, 1)
    noise_penalty = min((line.digit_count + line.junk_count + line.chord_token_count) / 5, 1)
    return font_score * 0.45 + position_score * 0.25 + centered_score * 0.25 - noise_penalty * 0.35


def _artist_line_score(line: TextLine, page_height: float) -> float:
    if line.word_count < 1 or line.word_count > 8 or line.alpha_count < 4:
        return 0
    if re.search(r"\b(song|book)\b", line.text, re.IGNORECASE):
        return 0

    position_score = line.y1 / page_height if page_height else 0
    connector_score = 0.2 if re.search(r"\s(e|and)\s|,", line.text, re.IGNORECASE) else 0
    noise_penalty = min((line.digit_count + line.junk_count + line.chord_token_count) / 5, 1)
    return position_score * 0.35 + line.uppercase_ratio * 0.25 + connector_score - noise_penalty * 0.45
