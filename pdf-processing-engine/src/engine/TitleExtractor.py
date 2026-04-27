from __future__ import annotations

import re

from .PageFeatures import PageFeatures, TextLine


LOWERCASE_NAME_WORDS = {"de", "da", "do", "das", "dos", "e"}


class TitleExtractor:
    def extract(self, features: PageFeatures) -> tuple[str | None, str | None]:
        title_line = self._find_title_line(features)
        artist_line = self._find_artist_line(features, title_line)
        return (
            self._clean_title(self._merge_title_text(features, title_line)) if title_line else None,
            self._clean_artist(artist_line.text) if artist_line else None,
        )

    def _find_title_line(self, features: PageFeatures) -> TextLine | None:
        candidates = [
            line
            for line in features.lines
            if self._is_plausible_title_line(line, features)
        ]
        if not candidates:
            return None

        return max(candidates, key=lambda line: self._title_score(line, features))

    def _find_artist_line(
        self,
        features: PageFeatures,
        title_line: TextLine | None,
    ) -> TextLine | None:
        candidates = [
            line
            for line in features.lines
            if self._is_plausible_artist_line(line, features, title_line)
        ]
        if not candidates:
            return None

        return max(candidates, key=lambda line: self._artist_score(line, features, title_line))

    def _is_plausible_title_line(self, line: TextLine, features: PageFeatures) -> bool:
        if line.alpha_count < 2 or line.word_count > 8:
            return False
        if self._looks_like_staff_noise(line):
            return False
        if line.y1 < features.page_height * 0.25:
            return False
        if line.max_font_size < max(14, min(features.max_font_size * 0.28, 22)):
            return False
        if (
            line.max_font_size > max(40, features.mean_font_size * 4)
            and line.y1 < features.page_height * 0.86
            and line.word_count <= 2
        ):
            return False
        if re.search(r"\b(song|book)\b", line.text, re.IGNORECASE):
            return False
        if line.digit_count > 2:
            return False
        if line.digit_count and line.junk_count:
            return False
        if line.junk_count > 2:
            return False
        return True

    def _is_plausible_artist_line(
        self,
        line: TextLine,
        features: PageFeatures,
        title_line: TextLine | None,
    ) -> bool:
        if line.alpha_count < 4 or line.word_count > 9:
            return False
        if self._looks_like_staff_noise(line):
            return False
        if line.y1 < features.page_height * 0.22:
            return False
        if title_line and line.text == title_line.text:
            return False
        if title_line and line.y1 > title_line.y1 + features.page_height * 0.08:
            return False
        if re.search(r"\b(song|book)\b", line.text, re.IGNORECASE):
            return False
        if line.digit_count > 2 or line.junk_count > 2:
            return False
        return True

    def _title_score(self, line: TextLine, features: PageFeatures) -> float:
        font_score = line.max_font_size / features.max_font_size if features.max_font_size else 0
        y_score = line.y1 / features.page_height if features.page_height else 0
        center_score = 1 - self._center_offset(line, features)
        human_text_score = min(line.word_count / 3, 1) * (1 - min(line.uppercase_ratio, 0.9) * 0.4)
        noise_penalty = min((line.digit_count + line.junk_count) / 4, 1)
        return (
            font_score * 0.22
            + y_score * 0.48
            + center_score * 0.16
            + human_text_score * 0.18
            - noise_penalty * 0.35
        )

    def _artist_score(
        self,
        line: TextLine,
        features: PageFeatures,
        title_line: TextLine | None,
    ) -> float:
        y_score = line.y1 / features.page_height if features.page_height else 0
        connector_score = 0.25 if re.search(r"\s(e|and)\s|,", line.text, re.IGNORECASE) else 0
        case_score = min(line.uppercase_ratio, 0.85)
        below_title_score = 0
        if title_line:
            distance = abs(title_line.y0 - line.y1) / features.page_height
            below_title_score = max(0, 0.25 - distance)
        noise_penalty = min((line.digit_count + line.junk_count) / 4, 1)
        return (
            y_score * 0.18
            + connector_score
            + case_score * 0.22
            + below_title_score
            - noise_penalty * 0.35
        )

    def _center_offset(self, line: TextLine, features: PageFeatures) -> float:
        if not features.page_width:
            return 1
        page_center = features.page_width / 2
        line_center = (line.x0 + line.x1) / 2
        return abs(line_center - page_center) / features.page_width

    def _clean_title(self, text: str) -> str:
        text = self._clean_common_noise(text)
        return text.strip()

    def _clean_artist(self, text: str) -> str:
        text = self._clean_common_noise(text)
        words = []
        for word in text.split():
            lower = word.lower()
            if lower in LOWERCASE_NAME_WORDS:
                words.append(lower)
            elif word.isupper():
                words.append(word.title())
            else:
                words.append(word)
        return " ".join(words).strip()

    def _clean_common_noise(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"^[^\wÀ-ÿ]+|[^\wÀ-ÿ]+$", "", text)
        return text.strip()

    def _merge_title_text(self, features: PageFeatures, title_line: TextLine) -> str:
        same_baseline = [
            line
            for line in features.lines
            if line is not title_line
            and self._is_plausible_title_line(line, features)
            and abs(line.y1 - title_line.y1) <= 3
            and abs(line.max_font_size - title_line.max_font_size) <= 3
        ]
        lines = sorted([title_line, *same_baseline], key=lambda line: line.x0)
        merged: list[TextLine] = []
        for line in lines:
            if not merged:
                merged.append(line)
                continue
            gap = line.x0 - merged[-1].x1
            if 0 <= gap <= features.page_width * 0.08:
                merged.append(line)
        return " ".join(line.text for line in merged)

    def _looks_like_staff_noise(self, line: TextLine) -> bool:
        letters = [char.upper() for char in line.text if char.isalpha()]
        if not letters:
            return True
        roman_staff_letters = {"I", "V", "W", "L", "M"}
        if all(char in roman_staff_letters for char in letters):
            return True
        roman_staff_ratio = sum(char in roman_staff_letters for char in letters) / len(letters)
        if roman_staff_ratio > 0.55 and line.uppercase_ratio >= 0.65:
            return True
        if line.uppercase_ratio > 0.9 and line.word_count <= 2 and len(letters) <= 6:
            return True
        return False
