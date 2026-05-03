from collections.abc import Iterable
import ocrmypdf
from pdfminer.high_level import extract_pages as pdf_text_extraction
from pdfminer.layout import LTPage
import pickle
import os
from .Page import Page
from .PageClassifier import DEFAULT_LABELS, PageClassifier
from .PageFeatures import PageFeatures
from .Transformer import Transformer


class ClassificationEngine():
    """
    Engine for processing and classifying PDF documents
    """

    def __init__(self, book_name) -> None:
        self.book_name = book_name
        self.pages: list[Page]
        self.num_pages: int = 0
        self.classifier: PageClassifier
        self.transformer = Transformer()

    def ocr(
        self,
        file_path: str,
        output_path: str,
        languages: Iterable[str] | None = None,
    ) -> None:
        """
        Run OCR engine and save in output_path
        """
        ocrmypdf.ocr(
            file_path,
            output_path,
            language=list(languages) if languages else None,
            skip_text=True,
        )

    def _extract_pages(
        self,
        file_path: str,
        preamble: int,
        max_pages: int,
        redo: bool,
    ) -> list[LTPage | PageFeatures]:
        """
        Extracts and saves elements from PDF with OCR layer.
        """
        pickle_dir = f'pickled/extracted_{self.book_name}'
        pickled_path = f'{pickle_dir}/full_document.pickle'
        temp_pickled_path = f'{pickled_path}.tmp'
        status_path = f'{pickle_dir}/full_document_status.txt'

        prev_exit_status = self._get_pickle_exit_status(status_path)

        if os.path.exists(pickled_path) and not redo and not prev_exit_status:
            # Deserialize
            print(
                f'Loading extraction from serialization {pickled_path}', end=' ')
            try:
                with open(pickled_path, 'rb') as file:
                    all_pages = pickle.load(file)
            except (EOFError, OSError, pickle.PickleError, TypeError, AttributeError):
                print('Cache unreadable; regenerating...', end=' ')
                all_pages = self._extract_page_features(file_path)
                self._save_page_cache(all_pages, pickled_path, temp_pickled_path, status_path)
        else:
            # Generate page objects
            print('Extracting pages...', end=' ')
            all_pages = self._extract_page_features(file_path)
            self._save_page_cache(all_pages, pickled_path, temp_pickled_path, status_path)
        print('Done')
        return [
            page
            for i, page in enumerate(all_pages)
            if i >= preamble and i < max_pages
        ]

    def _extract_page_features(self, file_path: str) -> list[PageFeatures]:
        return [
            PageFeatures.from_page(page)
            for page in pdf_text_extraction(pdf_file=file_path)
        ]

    def _save_page_cache(
        self,
        all_pages: list[PageFeatures],
        pickled_path: str,
        temp_pickled_path: str,
        status_path: str,
    ) -> None:
        os.makedirs(os.path.dirname(pickled_path), exist_ok=True)
        with open(status_path, 'w') as file:
            file.write('1')
        try:
            with open(temp_pickled_path, 'wb') as file:
                pickle.dump(all_pages, file, protocol=pickle.HIGHEST_PROTOCOL)
            os.replace(temp_pickled_path, pickled_path)
            with open(status_path, 'w') as file:
                file.write('0')
        finally:
            if os.path.exists(temp_pickled_path):
                os.remove(temp_pickled_path)

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

    def set_pages_from_file(
        self,
        file_path: str,
        preamble: int = 0,
        max_pages: int = 2**1000,
        redo=False,
        training_pages: list[Page] | None = None,
        training_labels: str | list[int] | None = None,
    ):
        pages = self._extract_pages(file_path, preamble, max_pages, redo)
        self.pages = [Page(page, i) for i, page in enumerate(pages)]

        self.num_pages = len(self.pages)
        self.classifier = PageClassifier(
            self.pages,
            labels=training_labels or DEFAULT_LABELS,
            training_pages=training_pages,
            book_name=self.book_name,
        )

    def set_classifier_training(
        self,
        training_pages: list[Page],
        training_labels: str | list[int] | None = None,
    ):
        self.classifier = PageClassifier(
            self.pages,
            labels=training_labels or DEFAULT_LABELS,
            training_pages=training_pages,
            book_name=self.book_name,
        )

    def classify_pages(self):
        labels = self.classifier.label_pages()
        self.transformer.set_labels(labels)
        for label, page in zip(labels, self.pages):
            page.set_type(label)
        self.transformer.set_pages(self.pages)

    def __str__(self) -> str:
        return f'ClassificationEngine(num_pages={self.num_pages})'
