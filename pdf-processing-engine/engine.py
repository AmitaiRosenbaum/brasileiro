import ocrmypdf
from pypdf import PdfReader
from pdfminer.high_level import extract_pages as pdf_text_extraction
from pdfminer.layout import LTPage, LTTextContainer, LTChar, LTTextLine
from typing import Iterable, Any, Iterator
from pathlib import Path
SCRIPT_DIR = Path(__file__).parent

class ClassificationEngine():
  def __init__(self) -> None:
    self.pages: list[Page]
    self.num_pages: int = 0

  def ocr(self, file_path: str, output_path: str) -> None:
    """
    Run OCR engine and save in output_path
    """
    ocrmypdf.ocr(file_path, output_path)
  
  def extract_pages(self, file_path: str) -> Iterator[LTPage]: 
    return pdf_text_extraction(pdf_file=file_path)
  
  def set_pages_from_file(self, file_path: str):
    pages = [page for page in self.extract_pages(file_path)]
    self.pages = [Page(page, i) for i, page in enumerate(pages)]
    page = self.pages[0]
    print(page)
    self.num_pages = len(self.pages)
    
  def __str__(self) -> str:
    return f'ClassificationEngine(num_pages={self.num_pages})'
  
  

class Page():
  def __init__(self, page: LTPage, index: int) -> None:
    self.max_font_size: int
    self.page = page
    self.index = index
    self.fonts: list[dict] = [{}]
    
    self._compute_max_size()
    self._compute_fonts()
  
  def _compute_max_size(self):
    self.max_font_size = 0
    self._search_max_font_size(self.page)
    
  def _search_max_font_size(self, element):
    self._check_size(element)
    if isinstance(element, Iterable):
      for subelement in element:
        self._check_size(subelement)
        self._search_max_font_size(subelement)
  
  def _check_size(self, element):
    if hasattr(element, 'size') and element.size > self.max_font_size:
      self.max_font_size = element.size
  
  def _compute_fonts(self):
      for element in self.page:
        if isinstance(element, LTTextContainer):
          for text_line in element:
            if isinstance(text_line, LTTextLine):
              for character in text_line:
                if isinstance(character, LTChar):
                  self.fonts = self.fonts + [{'size': character.size, 'font': character.fontname}]
      
  def __repr__(self) -> str:
    return f'Page(index={self.index}, max_font={self.max_font_size})'
  


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
    
  
  
  
  
  def get_optional_fontinfo(o) -> str:
    """Font info of LTChar if available, otherwise empty string"""
    if hasattr(o, 'size'):
        return o.size
    return ''

  def get_optional_text(o) -> str:
      """Text of LTItem if available, otherwise empty string"""
      if hasattr(o, 'get_text'):
          return o.get_text().strip()
      return ''
    
  def show_ltitem_hierarchy(o: Any, depth=0):
    """Show location and text of LTItem and all its descendants"""
    if depth == 0:
        print('element                        font                  stroking color  text')
        print('------------------------------ --------------------- --------------  ----------')

    print(
        f'fontsize={get_optional_fontinfo(o)}'
        f'text={get_optional_text(o)}'
    )

    if isinstance(o, Iterable) and depth < 5:
        for i in o:
            show_ltitem_hierarchy(i, depth=depth + 1)

    

  

  # show_ltitem_hierarchy(pages)
  
  # for page in pages:
  #   text = get_optional_text(page)
  #   font = get_optional_fontinfo(page)
    
  #   print(f'{text=}, {font=}')
  

def main():
  engine = ClassificationEngine()
  file_path = str(SCRIPT_DIR / "output.pdf")
  engine.set_pages_from_file(file_path)
  print(engine)
  print([page for page in engine.pages])


if __name__ == '__main__':
  main()

