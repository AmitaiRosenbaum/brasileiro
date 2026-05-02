from .Page import Page
from pypdf import PdfWriter, PdfReader
from pathlib import Path
import os
import re


TITLE_PAGE = 0
EXCLUDED_PAGE = 2


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

    def _get_file_name(self, output_index: int, page_index: int) -> str:
        file_name = f'{self._get_file_title(page_index)}-{self._get_file_artist(page_index)}'
        cleaned = re.sub(
            r'[\.$\/\\#\%\{\}\<\>\?\*\!\'\"\:\@\+\|\=]', '', file_name).strip()
        return f'{output_index:03d}-' + cleaned + '.pdf'

    def _write_song_csv(self, output_dir: Path, index: int):
        csv_path = output_dir / 'songs.csv'
        with open(csv_path, 'a') as file:
            if not csv_path.exists() or csv_path.stat().st_size == 0:
                file.write('artist; title\n')
            file.write(
                f'{self._get_file_artist(index)}; {self._get_file_title(index)}\n')

    def _next_output_index(self, output_dir: Path) -> int:
        existing_indexes = []
        for file_name in os.listdir(output_dir):
            match = re.match(r"^(\d+)-", file_name)
            if match:
                existing_indexes.append(int(match.group(1)))
        return max(existing_indexes, default=-1) + 1

    def _write_current_song(
        self,
        writer: PdfWriter,
        output_dir: Path,
        csv_dir: Path,
        output_index: int,
        title_page_index: int,
    ) -> None:
        with open(output_dir / self._get_file_name(output_index, title_page_index), 'wb') as file:
            writer.write(file)
        self._write_song_csv(csv_dir, title_page_index)

    def split(self, input_path: Path, output_dir: Path, skip: int = 0):
        reader = PdfReader(input_path)
        os.makedirs(output_dir, exist_ok=True)
        output_index = self._next_output_index(output_dir)
        csv_dir = Path(os.path.dirname(input_path))
        writer: PdfWriter | None = None
        current_title_index: int | None = None

        for i, label in enumerate(self._labels):
            if label == EXCLUDED_PAGE:
                if writer is not None and current_title_index is not None:
                    self._write_current_song(
                        writer,
                        output_dir,
                        csv_dir,
                        output_index,
                        current_title_index,
                    )
                    output_index += 1
                writer = None
                current_title_index = None
                continue

            if label == TITLE_PAGE:
                if writer is not None and current_title_index is not None:
                    self._write_current_song(
                        writer,
                        output_dir,
                        csv_dir,
                        output_index,
                        current_title_index,
                    )
                    output_index += 1
                current_title_index = i
                writer = PdfWriter()

            if writer is not None:
                writer.add_page(reader.pages[skip + i])

        if writer is not None and current_title_index is not None:
            self._write_current_song(
                writer,
                output_dir,
                csv_dir,
                output_index,
                current_title_index,
            )
