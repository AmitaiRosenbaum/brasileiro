from __future__ import annotations

from pdfminer.layout import LTPage

from .PageFeatures import PageFeatures
from .TitleExtractor import TitleExtractionResult, TitleExtractor


class Page:
    def __init__(self, page: LTPage, index: int) -> None:
        self.page = page
        self.index = index
        self.type: int | None = None

        self.features = PageFeatures.from_page(page)
        self.max_font_size = self.features.max_font_size
        self.title_likelihood_index = round(self.features.title_candidate_score * 10)

        self.extraction: TitleExtractionResult = TitleExtractor().extract_result(self.features)
        self.title = self.extraction.title
        self.artist = self.extraction.artist

    def set_type(self, type: int):
        self.type = type

    def __repr__(self) -> str:
        return (
            f"Page(index={self.index}, max_font={self.max_font_size}, "
            f"title={self.title!r}, artist={self.artist!r})"
        )
