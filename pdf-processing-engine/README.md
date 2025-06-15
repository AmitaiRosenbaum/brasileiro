# PDF Processing Engine

1. Place each file `bossa_nova_book.pdf` in `pdf-processing-engine/src/music/`.
2. Run `main.py`. This will:

   a) Create a PDF with an OCR lay in the same location as
   the folder named `ocr_bossa_nova_book.pdf`.

   > If a page already has an OCR layer then it will moved into the new PDF without change.

   b) Classify and split your PDF into songs in `pdf-processing-engine/src/music/split`

   c) Create a CSV `songs.csv` in `pdf-processing-engine/src/music` containing
   the song name and artist(s).

   d) Serialize an engine for each book in `pdf-processing-engine/src/pickled`.

   > You should re-serialize the engines if you make any changes to the initial settings. You can manually delete the pickle files, or set `redo=True`.

3. Review or correct `songs.csv` as required, and place it in the same folder named `corrected_songs.csv`
   > It is recommended not to delete rows from the CSV. It is safer to set the artist and title as TODO DELETE and delete the file at the end if required.
4. Run `rename_songs.py`. This will copy the split files into `pdf-processing-engine/src/music/final` and apply the changes made in the review stage.
