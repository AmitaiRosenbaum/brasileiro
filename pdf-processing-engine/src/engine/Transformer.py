from .Page import Page
from PyPDF2 import PdfWriter, PdfReader
from pathlib import Path
import os


class Transformer():
    def __init__(self) -> None:
        self._labels: list[int] | str
        self._pages: list[Page]

    def set_labels(self, labels: list[int] | str):
        self._labels = labels

    def set_pages(self, pages: list[Page]):
        self._pages = pages

    def split(self, input_path: Path, output_dir: Path, skip: int = 0):
        reader = PdfReader(input_path)
        writer = PdfWriter()
        song_count = 0
        os.makedirs(output_dir, exist_ok=True)
        for i, label in enumerate(self._labels):
            if label == '0':
                if i > 0:
                    with open(output_dir / f'song_{song_count}.pdf', 'wb') as file:
                        writer.write(file)
                song_count += 1
                writer = PdfWriter()
            writer.add_page(reader.pages[skip + i])
