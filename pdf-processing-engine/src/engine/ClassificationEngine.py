import ocrmypdf
from pdfminer.high_level import extract_pages as pdf_text_extraction
from pdfminer.layout import LTPage
from typing import Iterator
from pathlib import Path
import pickle
import os
from .Page import Page


class ClassificationEngine():
    """
    Engine for processing and classifying PDF documents
    """

    def __init__(self, book_name) -> None:
        self.book_name = book_name
        self.pages: list[Page]
        self.num_pages: int = 0

    def ocr(self, file_path: str, output_path: str) -> None:
        """
        Run OCR engine and save in output_path
        """
        ocrmypdf.ocr(file_path, output_path, skip_text=True)

    def _extract_pages(self, file_path: str) -> Iterator[LTPage]:
        """
        Extracts elements from PDF with OCR layer.
        """
        return pdf_text_extraction(pdf_file=file_path)

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

    def set_pages_from_file(self, file_path: str, preamble: int = 0, redo=False):
        """Extracts elements from each page and saves all pages. 

        Args:
            file_path (str): Path to document to be transformed
            preamble (int, optional): Pages to skip at the start. Defaults to 0.
            redo (boolean): Overwrite serialization
        """

        pickle_dir = f'pickled/extracted_{self.book_name}'
        pickled_path = f'{pickle_dir}/pickle.pickle'
        status_path = f'{pickle_dir}/status.txt'

        prev_exit_status = self._get_pickle_exit_status(status_path)

        if os.path.exists(pickled_path) and not redo and not prev_exit_status:
            # Deserialize
            print('Loading pages from serialization...', end=' ')
            with open(pickled_path, 'rb') as file:
                self.pages = pickle.load(file)
        else:
            # Generate page objects
            print('Generating pages...', end=' ')
            pages = [page for i, page in enumerate(
                self._extract_pages(file_path)) if i >= preamble]
            self.pages = [Page(page, i) for i, page in enumerate(pages)]

            # Serialize and save
            os.makedirs(os.path.dirname(pickled_path), exist_ok=True)
            with open(pickled_path, 'wb') as file:
                pickle.dump(self.pages, file)

            # Save success exit status
            with open(status_path, 'w') as file:
                file.write('0')
        self.num_pages = len(self.pages)
        print('Done')

    def __str__(self) -> str:
        return f'ClassificationEngine(num_pages={self.num_pages})'
