import ocrmypdf
from pypdf import PdfReader
from pdfminer.high_level import extract_pages as pdf_text_extraction
from typing import Iterable, Any, Iterator


def ocr():
    ocrmypdf.ocr('songs/wave.pdf', 'output.pdf')


def extract():
    reader = PdfReader('output.pdf')
    page = reader.pages[0]
    print(page.extract_text())


def mine():
    font = {"max": 0}

    def find_max_font_size(element: Any):
        if hasattr(element, 'size') and element.size > font['max']:
            font['max'] = element.size
        elif isinstance(element, Iterable):
            for subel in element:
                find_max_font_size(subel)

    pages = pdf_text_extraction('songs/chega de saudade.pdf')
    for page in pages:
        find_max_font_size(page)
        print('size', font['max'])
        font['max'] = 0
    return
