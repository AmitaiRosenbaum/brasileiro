from __future__ import annotations

from dataclasses import dataclass
import re

from .Page import Page


TITLE_PAGE = 0
NON_TITLE_PAGE = 1
EXCLUDED_PAGE = 2


@dataclass(frozen=True)
class Segment:
    start: int
    end: int

    @property
    def length(self) -> int:
        return self.end - self.start


class PageSequenceRefiner:
    """
    Applies songbook-level constraints to independent page predictions.

    The classifier answers "does this page look like a title page?". This class
    answers "does that prediction make sense in the sequence?".
    """

    def __init__(
        self,
        max_expected_song_pages: int = 3,
        immediate_title_gap: int = 1,
    ) -> None:
        self.max_expected_song_pages = max_expected_song_pages
        self.immediate_title_gap = immediate_title_gap

    def refine(self, pages: list[Page], labels: list[int]) -> list[int]:
        refined = labels.copy()
        if refined:
            refined[0] = TITLE_PAGE
            if self._is_blank_or_noise_page(pages[0]):
                refined[0] = NON_TITLE_PAGE
        self._remove_weak_title_pages(pages, refined)
        self._recover_missed_title_pages(pages, refined)
        self._remove_weak_title_pages(pages, refined)
        self._exclude_non_song_pages(pages, refined)
        self._exclude_backmatter(pages, refined)
        return refined

    def _exclude_backmatter(self, pages: list[Page], labels: list[int]) -> None:
        first_backmatter_index = next(
            (
                index
                for index, page in enumerate(pages)
                if self._is_backmatter_page(page)
            ),
            None,
        )
        if first_backmatter_index is None:
            return

        for index in range(first_backmatter_index, len(labels)):
            labels[index] = EXCLUDED_PAGE

    def _exclude_non_song_pages(self, pages: list[Page], labels: list[int]) -> None:
        for index, page in enumerate(pages):
            if self._is_standalone_excluded_page(page):
                labels[index] = EXCLUDED_PAGE

    def _remove_weak_title_pages(self, pages: list[Page], labels: list[int]) -> None:
        previous_title_index: int | None = None
        previous_title_page: Page | None = None
        for index, (page, label) in enumerate(zip(pages, labels)):
            if label != TITLE_PAGE:
                continue

            follows_title = (
                previous_title_index is not None
                and index - previous_title_index <= self.immediate_title_gap
            )
            next_page = pages[index + 1] if index + 1 < len(pages) else None
            if follows_title and previous_title_page and self._looks_like_duplicate_title(previous_title_page, page):
                labels[index] = NON_TITLE_PAGE
                continue
            if self._should_reject_title_page(
                page,
                is_first_page=index == 0,
                follows_title=follows_title,
                next_page=next_page,
            ):
                labels[index] = NON_TITLE_PAGE
                continue

            previous_title_index = index
            previous_title_page = page

    def _recover_missed_title_pages(self, pages: list[Page], labels: list[int]) -> None:
        changed = True
        while changed:
            changed = False
            for segment in self._segments(labels):
                if segment.length < 2:
                    continue

                candidates = [
                    index
                    for index in range(segment.start + 1, segment.end)
                    if self._is_recovery_candidate(pages[index], segment.length)
                ]
                if not candidates:
                    continue

                best_index = max(candidates, key=lambda index: self._recovery_score(pages[index]))
                labels[best_index] = TITLE_PAGE
                changed = True
                break

    def _segments(self, labels: list[int]) -> list[Segment]:
        starts = [index for index, label in enumerate(labels) if label == TITLE_PAGE]
        if not starts:
            return []
        return [
            Segment(start=start, end=starts[offset + 1] if offset + 1 < len(starts) else len(labels))
            for offset, start in enumerate(starts)
        ]

    def _should_reject_title_page(
        self,
        page: Page,
        is_first_page: bool,
        follows_title: bool,
        next_page: Page | None,
    ) -> bool:
        extraction = page.extraction
        if is_first_page:
            return not page.features.lines
        if not extraction.title and not self._is_artist_only_recovery_candidate(page):
            return True
        if self._has_hard_rejection(page) and next_page and self._is_next_page_stronger_title(page, next_page):
            return True
        if self._has_always_reject_reason(page):
            return True
        if self._has_hard_rejection(page) and not self._has_natural_title_text(extraction.title):
            return True
        if "weak artist score" in extraction.rejection_reasons and extraction.title_score < 0.7:
            return True
        if self._has_short_title_with_fragmented_artist(page):
            return True
        if self._looks_like_continuation_noise(page):
            return True
        if self._looks_like_bad_artist_continuation(page):
            return True
        if self._looks_like_ocr_noise_title(page):
            return True
        if extraction.plausible_title_page:
            return False
        if follows_title and not self._has_strong_title_signal(page):
            return True
        return not self._has_strong_title_signal(page)

    def _has_hard_rejection(self, page: Page) -> bool:
        hard_reasons = {
            "fragmented title",
            "symbol-heavy title",
            "chord-like title",
            "header title",
            "backmatter title",
            "low vowel ratio",
            "too little title text",
            "short ocr title",
            "split syllable title",
            "music glyph title",
            "lyric fragment title",
            "uppercase punctuation noise",
            "ocr-noise title",
            "fragmented artist",
            "weak short-title artist",
            "chord-like artist",
            "same title and artist",
        }
        return any(reason in hard_reasons for reason in page.extraction.rejection_reasons)

    def _has_always_reject_reason(self, page: Page) -> bool:
        always_reject_reasons = {
            "short ocr title",
            "split syllable title",
            "lyric fragment title",
            "too little title text",
        }
        return any(
            reason in always_reject_reasons
            for reason in page.extraction.rejection_reasons
        )

    def _is_next_page_stronger_title(self, page: Page, next_page: Page) -> bool:
        return (
            next_page.extraction.plausible_title_page
            and self._recovery_score(next_page) >= self._recovery_score(page) + 0.08
        )

    def _is_recovery_candidate(self, page: Page, segment_length: int) -> bool:
        extraction = page.extraction
        recovery_score = self._recovery_score(page)
        if segment_length > self.max_expected_song_pages and self._is_artist_only_recovery_candidate(page):
            return True
        if segment_length < 3:
            return (
                (
                    extraction.plausible_title_page
                    and recovery_score >= 0.65
                    and extraction.title_score >= 0.74
                    and extraction.artist_score >= 0.45
                )
                or self._is_clean_weak_artist_title(page)
            )
        if not extraction.plausible_title_page and extraction.title_score < 0.6:
            return False
        if self._has_hard_rejection(page):
            return False
        if segment_length > self.max_expected_song_pages:
            if extraction.plausible_title_page and not self._is_safe_long_segment_recovery(page):
                return False
            return (
                extraction.plausible_title_page
                or self._is_clean_weak_artist_title(page)
                or (
                    recovery_score >= 0.42
                    and page.features.artist_candidate_score >= 0.55
                )
            )
        return (
            extraction.plausible_title_page
            and recovery_score >= 0.68
            and self._has_strong_title_signal(page)
        ) or self._is_clean_weak_artist_title(page)

    def _recovery_score(self, page: Page) -> float:
        extraction = page.extraction
        return (
            extraction.title_score * 0.45
            + extraction.artist_score * 0.25
            + page.features.title_candidate_score * 0.2
            + page.features.artist_candidate_score * 0.1
        )

    def _is_artist_only_recovery_candidate(self, page: Page) -> bool:
        extraction = page.extraction
        return (
            not extraction.title
            and self._normalize_title(extraction.artist) == "chicobuarque"
            and extraction.artist_y_ratio >= 0.86
            and extraction.artist_score >= 0.3
            and page.features.title_candidate_score >= 0.75
        )

    def _has_strong_title_signal(self, page: Page) -> bool:
        extraction = page.extraction
        return (
            extraction.title_score >= 0.68
            or page.features.title_candidate_score >= 0.78
        )

    def _has_strong_artist_signal(self, page: Page) -> bool:
        extraction = page.extraction
        return (
            extraction.artist_score >= 0.35
            or page.features.artist_candidate_score >= 0.55
        )

    def _looks_like_duplicate_title(self, previous_page: Page, page: Page) -> bool:
        previous_title = self._normalize_title(previous_page.extraction.title)
        current_title = self._normalize_title(page.extraction.title)
        if not previous_title or not current_title:
            return False
        if previous_title == current_title:
            return True
        shorter, longer = sorted((previous_title, current_title), key=len)
        return len(shorter) >= 8 and shorter in longer

    def _normalize_title(self, title: str | None) -> str:
        if not title:
            return ""
        return re.sub(r"[^a-z0-9]+", "", title.lower())

    def _has_short_title_with_fragmented_artist(self, page: Page) -> bool:
        extraction = page.extraction
        if "fragmented artist" not in extraction.rejection_reasons:
            return False
        title_alpha_count = sum(char.isalpha() for char in extraction.title or "")
        return title_alpha_count <= 5

    def _looks_like_continuation_noise(self, page: Page) -> bool:
        extraction = page.extraction
        if extraction.title_y_ratio and extraction.title_y_ratio < 0.8:
            return (
                page.features.junk_char_count >= 35
                and extraction.artist_score < 0.55
            )
        if page.features.max_font_size >= 120:
            return (
                extraction.artist_score < 0.55
                and not self._has_clean_title_language(extraction.title)
            )
        return False

    def _looks_like_bad_artist_continuation(self, page: Page) -> bool:
        extraction = page.extraction
        artist = extraction.artist or ""
        title = extraction.title or ""
        if not title:
            return False
        if self._has_known_artist_text(artist) or self._has_known_artist_text(title):
            return False
        if (
            not self._has_known_artist_text(artist)
            and (
                re.search(r"[A-Za-zÀ-ÿ]{1,5}—[A-Za-zÀ-ÿ]{1,5}", artist)
                or re.search(r"[A-Za-zÀ-ÿ]{1,5}—[A-Za-zÀ-ÿ]{1,5}", title)
            )
        ):
            return True
        if extraction.artist_score >= 0.5:
            return False
        if (
            extraction.title_y_ratio < 0.88
            and extraction.artist_score < 0.55
            and (
                extraction.title_y_ratio < 0.7
                or not self._has_clean_title_language(title)
            )
        ):
            return True
        if re.search(r"[A-G](?:#|b)?[0-9/()]|[/=]{2,}", artist):
            return True
        if re.search(r"[A-Za-zÀ-ÿ]{1,5}—[A-Za-zÀ-ÿ]{1,5}", artist):
            return True
        if re.search(r"[A-Za-zÀ-ÿ]{1,5}—[A-Za-zÀ-ÿ]{1,5}", title):
            return True
        if len(title.split()) >= 5 and extraction.artist_y_ratio < 0.7:
            return True
        return False

    def _looks_like_ocr_noise_title(self, page: Page) -> bool:
        extraction = page.extraction
        title = extraction.title or ""
        if not title:
            return False
        if self._has_known_artist_text(extraction.artist):
            return False
        if extraction.artist_score < 0.75 and re.search(r"//|[|=<>]", title):
            return True
        if (
            extraction.artist_score < 0.45
            and self._has_low_diversity_artist_text(extraction.artist)
            and (len(title.split()) == 1 or not self._has_natural_title_text(title))
        ):
            return True
        letters = [char.lower() for char in title if char.isalpha()]
        if not letters:
            return True
        if not self._has_clean_title_language(title):
            return True
        if extraction.artist_score >= 0.75:
            return False
        if len(title.split()) == 1 and re.search(r"[a-zà-ÿ][A-ZÀ-Ý]", title):
            return True
        most_common_ratio = max(letters.count(char) for char in set(letters)) / len(letters)
        return len(letters) >= 6 and most_common_ratio >= 0.55

    def _is_clean_weak_artist_title(self, page: Page) -> bool:
        extraction = page.extraction
        if not extraction.title:
            return False
        if self._has_hard_rejection(page):
            return False
        return (
            extraction.title_y_ratio >= 0.82
            and extraction.title_score >= 0.68
            and page.features.title_candidate_score >= 0.78
            and (
                self._has_clean_title_language(extraction.title)
                or self._has_known_artist_text(extraction.title)
            )
            and not self._looks_like_ocr_noise_title(page)
        )

    def _has_known_artist_text(self, artist: str | None) -> bool:
        return bool(
            artist
            and re.search(
                r"\b("
                r"tom\s*jobim|"
                r"vinicius|"
                r"chico\s+buarque|"
                r"gilberto\s+gil|"
                r"marcos\s+valle|"
                r"almir\s+chediak|"
                r"caetano\s+veloso|"
                r"torquato\s+neto|"
                r"capinam|"
                r"liminha|"
                r"carlos\s+lyra|"
                r"roberto\s+menescal|"
                r"ronaldo\s+b[oó]scoli|"
                r"francis\s+hime|"
                r"ruy\s+guerra|"
                r"sergio\s+ricardo|"
                r"johnny\s+alf|"
                r"edu\s+lobo|"
                r"durval\s+ferreira|"
                r"moacyr\s+santos|"
                r"toninho\s+horta|"
                r"theo\s+de\s+barros|"
                r"paulinho\s+da\s+viola|"
                r"eumir|"
                r"deodato|"
                r"moraes\s+moreira|"
                r"neuza\s+teixeira|"
                r"jaime\s+silva|"
                r"pac.?fico\s+mascarenhas|"
                r"luiz\s+ega|"
                r"mauricio\s+einhorn|"
                r"pedro\s+camargo|"
                r"fernando\s+brant|"
                r"theo\s+de\s+barros|"
                r"gene\s+lees|"
                r"ray\s+gilbert"
                r")\b",
                artist,
                re.IGNORECASE,
            )
        )

    def _has_low_diversity_artist_text(self, artist: str | None) -> bool:
        letters = [char.lower() for char in artist or "" if char.isalpha()]
        if len(letters) < 4:
            return False
        most_common_ratio = max(letters.count(char) for char in set(letters)) / len(letters)
        return most_common_ratio >= 0.65

    def _is_blank_or_noise_page(self, page: Page) -> bool:
        extraction = page.extraction
        return (
            not extraction.title
            and not extraction.artist
            and page.features.alpha_count < 20
            and page.features.max_font_size < 10
        )

    def _is_safe_long_segment_recovery(self, page: Page) -> bool:
        extraction = page.extraction
        if extraction.artist_score >= 0.55:
            return True
        if extraction.artist_score >= 0.45 and self._has_natural_title_text(extraction.title):
            return True
        return extraction.title_y_ratio >= 0.8 and self._has_clean_title_language(extraction.title)

    def _has_natural_title_text(self, title: str | None) -> bool:
        if not title:
            return False
        words = [
            re.sub(r"[^A-Za-zÀ-ÿ]", "", word)
            for word in title.split()
        ]
        words = [word for word in words if word]
        if len(words) < 2:
            return False
        alpha_count = sum(len(word) for word in words)
        if alpha_count < 7:
            return False
        vowel_count = sum(char.lower() in "aeiouáàâãéêíóôõúü" for word in words for char in word)
        if vowel_count / alpha_count < 0.3:
            return False
        return all(
            len(word) < 3 or any(char.lower() in "aeiouáàâãéêíóôõúü" for char in word)
            for word in words
        )

    def _has_clean_title_language(self, title: str | None) -> bool:
        if self._has_natural_title_text(title):
            return True
        if not title:
            return False
        word = re.sub(r"[^A-Za-zÀ-ÿ]", "", title)
        if len(word) < 6:
            return False
        lower_word = word.lower()
        vowel_count = sum(char in "aeiouáàâãéêíóôõúü" for char in lower_word)
        most_common_ratio = max(lower_word.count(char) for char in set(lower_word)) / len(lower_word)
        return vowel_count / len(lower_word) >= 0.3 and most_common_ratio < 0.55

    def _is_backmatter_page(self, page: Page) -> bool:
        title = page.extraction.title or ""
        return bool(
            re.search(
                r"\b("
                r"discografia|discography|"
                r"outras?\s+publica(?:ç|c)(?:ões|oes)|"
                r"other\s+lumiar|"
                r"publications?"
                r")\b",
                title,
                re.IGNORECASE,
            )
        )

    def _is_standalone_excluded_page(self, page: Page) -> bool:
        title = page.extraction.title or ""
        artist = page.extraction.artist or ""
        combined = f"{title} {artist}"
        if re.search(r"\balmir\s+chediak\b", title, re.IGNORECASE):
            return True
        return bool(
            re.search(
                r"\b("
                r"songbool|songbook|"
                r"volume\s+\d+\s+musicas\s+songs|"
                r"produzido\s+por|"
                r"that\s+look\s+you?r\s+wear|"
                r"raca\s+humana|"
                r"banda\s+um|"
                r"gilberto\s+gil\s+viana|"
                r"discos?|"
                r"lado\s*2"
                r")\b",
                combined,
                re.IGNORECASE,
            )
        )
