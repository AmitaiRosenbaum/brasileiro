import ocrmypdf
from pdfminer.high_level import extract_pages as pdf_text_extraction
from pdfminer.layout import LTPage
from typing import Iterator
from pathlib import Path
from .Page import Page


class ClassificationEngine():
    """
    Engine for processing and classifying PDF documents
    """

    def __init__(self) -> None:
        self.pages: list[Page]
        self.num_pages: int = 0

    def ocr(self, file_path: str, output_path: str) -> None:
        """
        Run OCR engine and save in output_path
        """
        ocrmypdf.ocr(file_path, output_path, skip_text=True)

    def extract_pages(self, file_path: str) -> Iterator[LTPage]:
        """
        Extracts elements from PDF with OCR layer
        """
        return pdf_text_extraction(pdf_file=file_path)

    def set_pages_from_file(self, file_path: str):
        """
        Extracts elemnts from each page and saves all pages
        """
        pages = [page for page in self.extract_pages(file_path)]
        self.pages = [Page(page, i) for i, page in enumerate(pages)]
        page = self.pages[0]
        print(page)
        self.num_pages = len(self.pages)

    def __str__(self) -> str:
        return f'ClassificationEngine(num_pages={self.num_pages})'
