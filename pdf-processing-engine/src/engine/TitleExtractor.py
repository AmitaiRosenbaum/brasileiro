from __future__ import annotations

from dataclasses import dataclass
import re

from .PageFeatures import PageFeatures, TextLine


LOWERCASE_NAME_WORDS = {"de", "da", "do", "das", "dos", "e"}
HEADER_RE = re.compile(
    r"\b(song\s*book|songbook|bossa\s*n(?:ova|ava|owa))\b",
    re.IGNORECASE,
)
BACKMATTER_RE = re.compile(
    r"\b("
    r"discografia|discography|"
    r"outras?\s+publica(?:ç|c)(?:ões|oes)|"
    r"other\s+lumiar|"
    r"publications?"
    r")\b",
    re.IGNORECASE,
)
CHORDISH_TITLE_RE = re.compile(r"\b[A-G](?:#|b)?(?:m|maj|min|dim|aug|sus)?[0-9][^ ]*\b")


@dataclass(frozen=True)
class TitleExtractionResult:
    title: str | None
    artist: str | None
    title_score: float
    artist_score: float
    title_y_ratio: float
    artist_y_ratio: float
    plausible_title_page: bool
    rejection_reasons: tuple[str, ...]


class TitleExtractor:
    def extract(self, features: PageFeatures) -> tuple[str | None, str | None]:
        result = self.extract_result(features)
        return result.title, result.artist

    def extract_result(self, features: PageFeatures) -> TitleExtractionResult:
        title_line = self._find_title_line(features)
        artist_line = self._find_artist_line(features, title_line)
        title = self._clean_title(self._merge_title_text(features, title_line)) if title_line else None
        artist = self._clean_artist(artist_line.text) if artist_line else None
        title_score = self._title_score(title_line, features) if title_line else 0
        artist_score = self._artist_score(artist_line, features, title_line) if artist_line else 0
        title_y_ratio = title_line.y1 / features.page_height if title_line and features.page_height else 0
        artist_y_ratio = artist_line.y1 / features.page_height if artist_line and features.page_height else 0
        rejection_reasons = self._rejection_reasons(
            title,
            artist,
            title_score,
            artist_score,
            title_y_ratio,
        )

        return TitleExtractionResult(
            title=title,
            artist=artist,
            title_score=title_score,
            artist_score=artist_score,
            title_y_ratio=title_y_ratio,
            artist_y_ratio=artist_y_ratio,
            plausible_title_page=not rejection_reasons,
            rejection_reasons=tuple(rejection_reasons),
        )

    def _find_title_line(self, features: PageFeatures) -> TextLine | None:
        candidates = [
            line
            for line in features.lines
            if self._is_plausible_title_line(line, features)
        ]
        if not candidates:
            return None

        clean_top_candidates = [
            line
            for line in candidates
            if self._is_clean_top_title_line(line, features)
        ]
        if clean_top_candidates:
            return max(
                clean_top_candidates,
                key=lambda line: (line.y1, self._title_score(line, features)),
            )

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

        clean_credit_lines = [
            line
            for line in candidates
            if self._is_clean_artist_credit_line(line, features, title_line)
        ]
        if clean_credit_lines:
            return max(
                clean_credit_lines,
                key=lambda line: (line.y1, self._artist_score(line, features, title_line)),
            )

        return max(candidates, key=lambda line: self._artist_score(line, features, title_line))

    def _is_plausible_title_line(self, line: TextLine, features: PageFeatures) -> bool:
        if line.alpha_count < 2 or line.word_count > 10:
            return False
        if (
            self._looks_like_fragmented_title(line.text)
            and not self._is_top_pronounceable_short_title(line, features)
        ):
            return False
        if self._looks_like_staff_noise(line):
            return False
        if line.y1 < features.page_height * 0.25:
            return False
        if line.max_font_size < max(14, min(features.max_font_size * 0.28, 16)):
            return False
        if (
            line.max_font_size > max(40, features.mean_font_size * 4)
            and line.y1 < features.page_height * 0.86
            and line.word_count <= 2
        ):
            return False
        if self._looks_like_header(line):
            return False
        if line.digit_count > 2:
            return False
        junk_count = self._significant_junk_count(line.text)
        if line.digit_count and junk_count and not self._has_clean_title_after_leading_noise(line.text):
            return False
        if junk_count > 2:
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
        if title_line and line.y1 >= title_line.y1:
            return False
        if self._looks_like_header(line):
            return False
        if line.digit_count > 2 or self._significant_junk_count(line.text) > 2:
            return False
        return True

    def _title_score(self, line: TextLine, features: PageFeatures) -> float:
        font_score = line.max_font_size / features.max_font_size if features.max_font_size else 0
        y_score = line.y1 / features.page_height if features.page_height else 0
        center_score = 1 - self._center_offset(line, features)
        human_text_score = min(line.word_count / 3, 1) * (1 - min(line.uppercase_ratio, 0.9) * 0.4)
        noise_penalty = min((line.digit_count + self._significant_junk_count(line.text)) / 4, 1)
        header_penalty = 1 if self._looks_like_header(line) else 0
        title_band_bonus = 0.12 if y_score >= 0.84 and line.alpha_count >= 5 else 0
        return (
            font_score * 0.22
            + y_score * 0.48
            + center_score * 0.16
            + human_text_score * 0.18
            + title_band_bonus
            - noise_penalty * 0.35
            - header_penalty
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
        noise_penalty = min((line.digit_count + self._significant_junk_count(line.text)) / 4, 1)
        header_penalty = 1 if self._looks_like_header(line) else 0
        return (
            y_score * 0.18
            + connector_score
            + case_score * 0.22
            + below_title_score
            - noise_penalty * 0.35
            - header_penalty
        )

    def _center_offset(self, line: TextLine, features: PageFeatures) -> float:
        if not features.page_width:
            return 1
        page_center = features.page_width / 2
        line_center = (line.x0 + line.x1) / 2
        return abs(line_center - page_center) / features.page_width

    def _clean_title(self, text: str) -> str:
        text = self._clean_common_noise(text)
        text = re.sub(r"^[^A-Za-zÀ-ÿ]*\d+\s+", "", text)
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

    def _looks_like_header(self, line: TextLine) -> bool:
        return HEADER_RE.search(line.text) is not None

    def _is_clean_artist_credit_line(
        self,
        line: TextLine,
        features: PageFeatures,
        title_line: TextLine | None,
    ) -> bool:
        if title_line is None:
            return False
        y_ratio = line.y1 / features.page_height if features.page_height else 0
        distance_below_title = (title_line.y0 - line.y1) / features.page_height
        return (
            0 <= distance_below_title <= 0.06
            and y_ratio >= 0.86
            and line.uppercase_ratio >= 0.9
            and line.alpha_count >= 8
            and line.digit_count == 0
            and self._significant_junk_count(line.text) == 0
        )

    def _is_clean_top_title_line(self, line: TextLine, features: PageFeatures) -> bool:
        y_ratio = line.y1 / features.page_height if features.page_height else 0
        return y_ratio >= 0.9 and self._has_natural_title_text(line.text)

    def _has_natural_title_text(self, text: str | None) -> bool:
        if not text:
            return False
        words = [
            re.sub(r"[^A-Za-zÀ-ÿ0-9]", "", word)
            for word in text.split()
        ]
        words = [word for word in words if word]
        alpha_words = [
            re.sub(r"[^A-Za-zÀ-ÿ]", "", word)
            for word in words
        ]
        alpha_words = [word for word in alpha_words if word]
        alpha_count = sum(len(word) for word in alpha_words)
        if alpha_count < 3:
            return False
        vowel_count = sum(
            char.lower() in "aeiouáàâãéêíóôõúü"
            for word in alpha_words
            for char in word
        )
        if alpha_count >= 4 and vowel_count / alpha_count < 0.28:
            return False
        if self._looks_like_fragmented_title(text):
            return False
        if self._significant_junk_count(text) > 1:
            return False
        if CHORDISH_TITLE_RE.search(text):
            return False
        return all(
            len(word) < 3 or any(char.lower() in "aeiouáàâãéêíóôõúü" for char in word)
            for word in alpha_words
        )

    def _looks_like_fragmented_title(self, text: str) -> bool:
        words = [word for word in re.split(r"\s+", text.strip()) if word]
        if len(words) < 3:
            return False

        alpha_lengths = [
            len(re.sub(r"[^A-Za-zÀ-ÿ]", "", word))
            for word in words
        ]
        alpha_word_count = sum(1 for length in alpha_lengths if length)
        longest_word = max(alpha_lengths, default=0)
        short_words = sum(1 for length in alpha_lengths if 0 < length <= 3)
        if longest_word <= 3 and short_words >= 3:
            return True
        if (
            len(words) >= 5
            and alpha_word_count
            and short_words / alpha_word_count >= 0.65
            and self._significant_junk_count(text) >= 1
        ):
            return True
        if any(char.isdigit() for char in text) and short_words >= 3:
            return True
        return False

    def _has_only_pronounceable_short_words(self, text: str) -> bool:
        words = [
            re.sub(r"[^A-Za-zÀ-ÿ]", "", word)
            for word in re.split(r"\s+", text.strip())
        ]
        words = [word for word in words if word]
        if not words:
            return False
        return all(
            len(word) <= 3
            and any(char.lower() in "aeiouáàâãéêíóôõúü" for char in word)
            for word in words
        )

    def _is_top_pronounceable_short_title(
        self,
        line: TextLine,
        features: PageFeatures,
    ) -> bool:
        y_ratio = line.y1 / features.page_height if features.page_height else 0
        return y_ratio >= 0.9 and self._has_only_pronounceable_short_words(line.text)

    def _looks_like_fragmented_artist(self, text: str | None) -> bool:
        if not text:
            return False
        words = [word for word in re.split(r"\s+", text.strip()) if word]
        alpha_lengths = [
            len(re.sub(r"[^A-Za-zÀ-ÿ]", "", word))
            for word in words
        ]
        alpha_words = [length for length in alpha_lengths if length]
        if len(alpha_words) < 3:
            return False
        return max(alpha_words) <= 3

    def _has_clean_title_after_leading_noise(self, text: str) -> bool:
        cleaned = re.sub(r"^[^A-Za-zÀ-ÿ]*\d+\s+", "", text).strip()
        if cleaned == text.strip():
            return False
        alpha_count = sum(char.isalpha() for char in cleaned)
        return alpha_count >= 4 and not self._looks_like_fragmented_title(cleaned)

    def _significant_junk_count(self, text: str) -> int:
        count = 0
        junk_chars = set("—-~=_|:;<>@¢{}[]()\"'‘’“”·•!")
        for index, char in enumerate(text):
            if char not in junk_chars:
                continue
            previous_char = text[index - 1] if index else ""
            next_char = text[index + 1] if index + 1 < len(text) else ""
            if char in {"-", "—"} and previous_char.isalpha() and next_char.isalpha():
                continue
            if char == "!" and index == len(text) - 1 and previous_char.isalnum():
                continue
            count += 1
        return count

    def _rejection_reasons(
        self,
        title: str | None,
        artist: str | None,
        title_score: float,
        artist_score: float,
        title_y_ratio: float,
    ) -> list[str]:
        reasons: list[str] = []
        if not title:
            reasons.append("missing title")
            return reasons

        title_alpha = sum(char.isalpha() for char in title)
        title_junk = self._significant_junk_count(title)
        title_vowels = sum(char.lower() in "aeiouáàâãéêíóôõúü" for char in title)
        if title_score < 0.48:
            reasons.append("weak title score")
        if title_alpha < 3:
            reasons.append("too little title text")
        if title_alpha >= 4 and title_vowels / title_alpha <= 0.2:
            reasons.append("low vowel ratio")
        if (
            self._looks_like_fragmented_title(title)
            and not (
                title_y_ratio >= 0.9
                and self._has_only_pronounceable_short_words(title)
            )
        ):
            reasons.append("fragmented title")
        if self._looks_like_short_ocr_title(title, artist_score):
            reasons.append("short ocr title")
        if self._looks_like_split_syllable_title(title, artist_score):
            reasons.append("split syllable title")
        if self._looks_like_music_glyph_title(title):
            reasons.append("music glyph title")
        if self._looks_like_lyric_fragment_title(title, artist, artist_score):
            reasons.append("lyric fragment title")
        if title_y_ratio < 0.84 and artist_score < 0.55:
            reasons.append("low title position")
        if self._looks_like_same_title_artist(title, artist, artist_score):
            reasons.append("same title and artist")
        if self._looks_like_uppercase_punctuation_noise(title, artist_score):
            reasons.append("uppercase punctuation noise")
        if title_alpha <= 6 and artist_score < 0.45:
            reasons.append("weak short-title artist")
        if title_alpha <= 5 and self._looks_like_fragmented_artist(artist):
            reasons.append("fragmented artist")
        if title_alpha <= 4 and artist and artist_score < 0.45:
            reasons.append("weak short-title artist")
        if title_junk >= 2:
            reasons.append("symbol-heavy title")
        if CHORDISH_TITLE_RE.search(title):
            reasons.append("chord-like title")
        if artist and CHORDISH_TITLE_RE.search(artist) and title_alpha <= 6:
            reasons.append("chord-like artist")
        if HEADER_RE.search(title):
            reasons.append("header title")
        if BACKMATTER_RE.search(title):
            reasons.append("backmatter title")
        if len(title.split()) >= 5 and sum(char.islower() for char in title) <= 2:
            reasons.append("ocr-noise title")
        if not artist and title_score < 0.72:
            reasons.append("missing artist")
        if artist and artist_score < 0.18 and title_score < 0.68:
            reasons.append("weak artist score")
        return reasons

    def _looks_like_short_ocr_title(self, title: str, artist_score: float) -> bool:
        words = [
            re.sub(r"[^A-Za-zÀ-ÿ]", "", word)
            for word in title.split()
        ]
        words = [word for word in words if word]
        if not words:
            return False
        suspicious_single_letter_words = sum(
            1
            for word in words
            if len(word) == 1 and word.lower() not in {"a", "e", "o", "é"}
        )
        short_words = sum(1 for word in words if len(word) <= 2)
        alpha_count = sum(len(word) for word in words)
        if suspicious_single_letter_words >= 2 and alpha_count <= 10:
            return True
        if suspicious_single_letter_words >= 1 and alpha_count <= 4:
            return True
        return len(words) <= 3 and short_words >= 2 and alpha_count <= 10 and artist_score < 0.56

    def _looks_like_split_syllable_title(self, title: str, artist_score: float) -> bool:
        return (
            artist_score < 0.6
            and re.search(r"\b[A-Za-zÀ-ÿ]{1,4}\s+-\s+[A-Za-zÀ-ÿ]{1,4}\b", title) is not None
        )

    def _looks_like_music_glyph_title(self, title: str) -> bool:
        alpha_chars = [char for char in title if char.isalpha()]
        if not alpha_chars:
            return False
        music_chars = sum(char in {"I", "J", "Q"} for char in alpha_chars)
        if music_chars / len(alpha_chars) >= 0.45:
            return True
        if self._significant_junk_count(title) >= 2 and music_chars:
            return True
        return False

    def _looks_like_lyric_fragment_title(
        self,
        title: str,
        artist: str | None,
        artist_score: float,
    ) -> bool:
        words = [
            re.sub(r"[^A-Za-zÀ-ÿ]", "", word)
            for word in title.split()
        ]
        words = [word for word in words if word]
        if not words:
            return False
        alpha_count = sum(len(word) for word in words)
        all_short_words = all(len(word) <= 3 for word in words)
        all_compact_words = all(len(word) <= 4 for word in words)
        has_fragmented_artist = bool(
            artist and re.search(r"\b[A-Za-zÀ-ÿ]{1,4}\s*-\s*[A-Za-zÀ-ÿ]{1,5}\b", artist)
        )
        has_fragmented_artist = has_fragmented_artist or self._looks_like_fragmented_artist(artist)
        has_chordish_artist = self._has_chordish_artist_text(artist)
        starts_with_upper_noise = bool(re.match(r"^[A-ZÀ-Ý]{2,}\s+[a-zà-ÿ]", title))
        return (
            (all_short_words and len(words) >= 4 and artist_score < 0.5)
            or (all_compact_words and len(words) >= 3 and has_fragmented_artist and artist_score < 0.7)
            or (alpha_count <= 6 and has_fragmented_artist)
            or (all_short_words and has_chordish_artist and artist_score < 0.65)
            or starts_with_upper_noise
        )

    def _looks_like_same_title_artist(
        self,
        title: str,
        artist: str | None,
        artist_score: float,
    ) -> bool:
        if not artist or artist_score >= 0.75:
            return False
        normalized_title = re.sub(r"[^a-z0-9]+", "", title.lower())
        normalized_artist = re.sub(r"[^a-z0-9]+", "", artist.lower())
        return bool(normalized_title and normalized_title == normalized_artist)

    def _looks_like_uppercase_punctuation_noise(
        self,
        title: str,
        artist_score: float,
    ) -> bool:
        alpha_chars = [char for char in title if char.isalpha()]
        if len(alpha_chars) < 5:
            return False
        uppercase_ratio = sum(char.isupper() for char in alpha_chars) / len(alpha_chars)
        has_noise_punctuation = bool(re.search(r"[:=|]|\s-[A-ZÀ-Ý]", title))
        return uppercase_ratio >= 0.65 and has_noise_punctuation and artist_score < 0.75

    def _has_chordish_artist_text(self, artist: str | None) -> bool:
        if not artist:
            return False
        tokens = re.findall(r"\b[A-G][A-Za-z0-9/#()]*\b", artist)
        if not tokens:
            return False
        chordish_tokens = [
            token
            for token in tokens
            if (
                len(token) <= 7
                and (
                    any(char.isdigit() for char in token)
                    or "/" in token
                    or "#" in token
                    or re.search(r"(?:maj|min|dim|aug|sus|add|m|M)$", token)
                )
            )
        ]
        return len(chordish_tokens) >= 2
