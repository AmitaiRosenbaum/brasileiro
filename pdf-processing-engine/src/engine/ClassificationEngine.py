import ocrmypdf
from pdfminer.high_level import extract_pages as pdf_text_extraction
from pdfminer.layout import LTPage
from typing import Iterator
from pathlib import Path
import pickle
import os
from .Page import Page
from .Lda import Lda
from .Transformer import Transformer


class ClassificationEngine():
    """
    Engine for processing and classifying PDF documents
    """

    def __init__(self, book_name) -> None:
        self.book_name = book_name
        self.pages: list[Page]
        self.num_pages: int = 0
        self.lda: Lda
        self.transformer = Transformer()

    def ocr(self, file_path: str, output_path: str) -> None:
        """
        Run OCR engine and save in output_path
        """
        ocrmypdf.ocr(file_path, output_path, skip_text=True)

    def _extract_pages(self, file_path: str, preamble: int, max_pages: int, redo: bool) -> list[LTPage]:
        """
        Extracts and saves elements from PDF with OCR layer.
        """
        pickle_dir = f'pickled/extracted_{self.book_name}'
        pickled_path = f'{pickle_dir}/pickle.pickle'
        status_path = f'{pickle_dir}/status.txt'

        prev_exit_status = self._get_pickle_exit_status(status_path)

        if os.path.exists(pickled_path) and not redo and not prev_exit_status:
            # Deserialize
            print('Loading extraction from serialization...', end=' ')
            with open(pickled_path, 'rb') as file:
                pages = pickle.load(file)
        else:
            # Generate page objects
            print('Extracting pages...', end=' ')
            pages = [page for i, page in enumerate(
                pdf_text_extraction(pdf_file=file_path)) if i >= preamble and i < max_pages]

            # Serialize and save
            os.makedirs(os.path.dirname(pickled_path), exist_ok=True)
            with open(pickled_path, 'wb') as file:
                pickle.dump(pages, file)

            # Save success exit status
            with open(status_path, 'w') as file:
                file.write('0')
        print('Done')
        return pages

        # Pages is the output we want from this function
        self.pages = [Page(page, i) for i, page in enumerate(pages)]

        pdf_text_extraction(pdf_file=file_path)

    def _get_pickle_exit_status(self, status_path):
        """Get pickling exit status. 

        Args:
            status_path (_type_): Used to save exit status

        Returns:
            _type_: 0 for success, 1 for error
        """
        if os.path.exists(status_path):
            with open(status_path, 'r') as file:
                return int(file.read())
        else:
            return 0

    def set_pages_from_file(self, file_path: str, preamble: int = 0, max_pages: int = 2**1000, redo=False):
        pages = self._extract_pages(file_path, preamble, max_pages, redo)
        self.pages = [Page(page, i) for i, page in enumerate(pages)]

        self.num_pages = len(self.pages)
        self.lda = Lda(self.pages)

    def classify_pages(self):
        labels = self.lda.label_pages()
        self.transformer.set_labels(labels)
        for label, page in zip(labels, self.pages):
            page.set_type(label)

    def __str__(self) -> str:
        return f'ClassificationEngine(num_pages={self.num_pages})'
