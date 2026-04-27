from .Page import Page
from pypdf import PdfWriter, PdfReader
from pathlib import Path
import os
import re


class Transformer():
    def __init__(self) -> None:
        self._labels: list[int]
        self._pages: list[Page]

    def set_labels(self, labels: list[int]):
        self._labels = labels

    def set_pages(self, pages: list[Page]):
        self._pages = pages

    def _remove_semicolon(self, text: str | None):
        return ''.join(text.split(';')) if text else ''

    def _get_file_artist(self, index: int):
        artist = self._pages[index].artist
        return self._remove_semicolon(artist) or f'MISSING_ARTIST_{index}'

    def _get_file_title(self, index: int):
        title = self._pages[index].title
        return self._remove_semicolon(title) or f'MISSING_TITLE_{index}'

    def _get_file_name(self, index: int) -> str:
        offset = 447
        file_name = f'{self._get_file_title(index)}-{self._get_file_artist(index)}'
        cleaned = re.sub(
            r'[\.$\/\\#\%\{\}\<\>\?\*\!\'\"\:\@\+\|\=]', '', file_name).strip()
        return f'{offset + index}-' + cleaned + '.pdf'

    def _write_song_csv(self, output_dir: Path, index: int):
        with open(output_dir / 'songs.csv', 'a') as file:
            if index == 0:
                file.write('artist; title\n')
            file.write(
                f'{self._get_file_artist(index)}; {self._get_file_title(index)}\n')

    def split(self, input_path: Path, output_dir: Path, skip: int = 0):
        reader = PdfReader(input_path)
        writer = PdfWriter()
        current_title_index = 0
        os.makedirs(output_dir, exist_ok=True)
        for i, label in enumerate(self._labels):
            if label == 0:
                if i > 0:
                    # with open(output_dir / self._get_file_name(current_title_index), 'wb') as file:
                    #     writer.write(file)
                    # self._write_song_csv(
                    #     Path(os.path.dirname(input_path)), current_title_index)
                    pass
                current_title_index = i
                writer = PdfWriter()
            writer.add_page(reader.pages[skip + i])
