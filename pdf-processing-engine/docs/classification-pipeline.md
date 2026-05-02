# PDF Classification Pipeline

This document describes how the PDF processing engine classifies songbook pages,
extracts title and artist text, refines page boundaries, and produces split song
PDFs. It is meant to make the current model maintainable: every heuristic should
have a reason, a failure mode it addresses, and a way to verify it.

## Goals

The engine is solving two related problems:

1. Classify each OCR page as either a title page or a continuation page.
2. Extract the song title and artist from each title page.

The title-page labels are then used as split points. Every page from one title
page up to, but not including, the next title page belongs to the same song.

The main risk is regression. A change that fixes one false split can easily hide
a real song title elsewhere, so classification changes should always be checked
against:

- known false positives, where a continuation page was classified as a title;
- known false negatives, where a real title page was missed;
- the previous full-book split list, to understand every boundary that moved.

## Main Files

- `src/main.py`
  Runs the current five-book workflow. It loads default training pages from
  `SongBook_BossaNova_1`, then processes books 1-5 with the configured preambles.

- `src/engine/ClassificationEngine.py`
  Coordinates OCR extraction, page object creation, classifier setup, and split
  preparation.

- `src/engine/Page.py`
  Wraps each `pdfminer` page. It computes page-level features and immediately
  runs title/artist extraction.

- `src/engine/PageFeatures.py`
  Converts PDF text layout into structured numeric features for the classifier.

- `src/engine/TitleExtractor.py`
  Finds the most plausible title and artist lines on a page, scores them, and
  records rejection reasons for suspicious OCR.

- `src/engine/PageClassifier.py`
  Trains a lightweight centroid classifier from manually labelled pages, predicts
  raw page labels, and calls the sequence refiner.

- `src/engine/PageSequenceRefiner.py`
  Applies songbook-level constraints to raw predictions: removing weak false
  title pages and recovering missed title pages inside long segments.

- `src/engine/Transformer.py`
  Uses final labels to split the original OCR PDF into song-level PDFs.

## Label Values

The classifier uses integer labels:

- `0`: title page
- `1`: non-title page or continuation page

This convention appears in both `PageClassifier.py` and `PageSequenceRefiner.py`.

## End-To-End Flow

### 1. OCR PDF Preparation

`process_book()` in `src/main.py` starts from a book name such as
`SongBook_BossaNova_3`.

It expects source PDFs in:

```text
pdf-processing-engine/src/music/
```

For each book it checks for an OCR-layer PDF named:

```text
ocr_<book_name>.pdf
```

If that file does not exist, `ClassificationEngine.ocr()` runs `ocrmypdf.ocr()`
with `skip_text=True` and an explicit Tesseract language list. `src/main.py`
defaults this to `por`, but it can be overridden with `--ocr-languages` or the
`OCR_LANGUAGES` environment variable. This preserves pages that already have
text and adds OCR only where needed.

### 2. Preamble and Page Window Selection

Each book is processed with a preamble, because front matter pages are not songs.
The current workflow uses:

```python
SongBook_BossaNova_1: preamble=30, max_pages=137
SongBook_BossaNova_2: preamble=1
SongBook_BossaNova_3: preamble=6
SongBook_BossaNova_4: preamble=5
SongBook_BossaNova_5: preamble=5, max_pages=136
```

The page index used by the classifier is zero-based after the preamble. For
example, if a book has `preamble=6`, classifier page `0` is source PDF page `6`.

### 3. PDFMiner Layout Extraction

`ClassificationEngine._extract_pages()` calls `pdfminer.high_level.extract_pages`
to produce `LTPage` objects. These layout objects include text, coordinates, font
sizes, and font names.

Extraction is cached as a pickle under:

```text
pickled/extracted_<book_name>/pickle.pickle
```

Use `redo=True` or delete the pickle if page extraction behavior changes. This is
important because cached layout objects can hide changes made to OCR or PDF
parsing.

### 4. Page Object Creation

Each `LTPage` becomes a `Page`:

```python
self.pages = [Page(page, i) for i, page in enumerate(pages)]
```

Creating a `Page` does three things:

1. Stores the original `LTPage`.
2. Computes `PageFeatures`.
3. Runs `TitleExtractor.extract_result()` and stores:
   - `page.title`
   - `page.artist`
   - `page.extraction`

`page.extraction` is important because it contains not only the extracted text,
but also confidence scores, vertical positions, plausibility, and rejection
reasons.

## Feature Extraction

`PageFeatures.from_page()` walks the `LTPage` tree and extracts text lines into
`TextLine` records.

Each `TextLine` contains:

- text;
- bounding box coordinates: `x0`, `x1`, `y0`, `y1`;
- average and maximum font size;
- font names.

It also exposes derived properties:

- `width`;
- `alpha_count`;
- `uppercase_ratio`;
- `digit_count`;
- `junk_count`;
- `word_count`;
- `has_bold_font`;
- `chord_token_count`.

### Page-Level Features

The classifier vector currently includes:

1. `max_font_size`
2. `mean_font_size`
3. `large_line_count`
4. `top_line_count`
5. `top_large_line_count`
6. `centered_large_line_count`
7. `uppercase_ratio`
8. `chord_token_count`
9. `junk_char_count`
10. `largest_line_y_ratio`
11. `largest_line_center_offset`
12. `title_candidate_score`
13. `artist_candidate_score`

These features capture the rough visual shape of a title page:

- title pages usually have a prominent text line near the top;
- artist lines tend to be near the title and often contain connectors such as
  `e`, `and`, or commas;
- continuation pages often contain many chord tokens and noisy OCR fragments;
- OCR artifacts often have very large font sizes or junk-heavy text.

### Candidate Scores

`title_candidate_score` is the best score among all text lines according to:

- relative font size;
- vertical position;
- centeredness;
- digit, junk, and chord noise.

`artist_candidate_score` is the best score among all artist-like lines according
to:

- vertical position;
- uppercase ratio;
- connectors such as `e`, `and`, or commas;
- digit, junk, and chord noise.

These candidate scores are intentionally independent of the final extracted
title and artist. They give the classifier a broad page-shape signal even when
the exact line extraction is imperfect.

## Title and Artist Extraction

`TitleExtractor` is responsible for finding the text that should be used in file
names and reports. It also produces signals used by the sequence refiner.

The output is a `TitleExtractionResult`:

```python
title: str | None
artist: str | None
title_score: float
artist_score: float
title_y_ratio: float
artist_y_ratio: float
plausible_title_page: bool
rejection_reasons: tuple[str, ...]
```

### Finding Title Lines

The extractor first collects plausible title-line candidates.

A title candidate must:

- contain at least two alphabetic characters;
- contain no more than eight words;
- not look like fragmented OCR;
- not look like staff/noise text;
- appear above the lower quarter of the page;
- pass a dynamic font-size threshold;
- not be a book header such as `Songbook` or `Bossa Nova`;
- not be too digit-heavy;
- not be too symbol-heavy.

The dynamic font-size threshold is intentionally capped. Some pages contain
absurdly large OCR glyphs, so requiring a fixed fraction of the maximum font size
would reject real titles like `Vagamente`, `Wave`, or `Pouca duracao`.

### Significant Junk

`_significant_junk_count()` counts symbols that usually indicate OCR artifacts:

```text
— - ~ = _ | : ; < > @ ¢ { } [ ] ( ) quotes
```

There is one important exception: hyphens and dashes between alphabetic
characters are not counted as junk. This keeps real hyphenated titles such as
`Bo-ba-Iá-Iá` and `Valsa-rancho` from being rejected.

### Leading Noise Cleanup

Some titles are extracted with leading OCR noise, for example a number before a
real title. `_has_clean_title_after_leading_noise()` allows the extractor to keep
the candidate if removing the leading noise leaves a natural-looking title.

`_clean_title()` then removes that leading noise from the final title text.

### Finding Artist Lines

Artist candidates are filtered separately. An artist candidate must:

- contain enough alphabetic text;
- not contain too many words;
- not look like staff/noise text;
- be in the upper portion of the page;
- sit below or near the title, if a title was found;
- not be a book header;
- not be digit-heavy or symbol-heavy.

The artist score rewards:

- position near the top;
- connectors such as `e`, `and`, or commas;
- uppercase text;
- closeness to the title line.

### Rejection Reasons

The extractor does not simply return `None` for every suspicious page. It records
specific rejection reasons so that the sequence refiner can make more informed
decisions.

Current rejection reasons include:

- `missing title`
- `weak title score`
- `too little title text`
- `low vowel ratio`
- `fragmented title`
- `fragmented artist`
- `weak short-title artist`
- `symbol-heavy title`
- `chord-like title`
- `chord-like artist`
- `header title`
- `ocr-noise title`
- `missing artist`
- `weak artist score`

These are deliberately descriptive. When a page moves from title to continuation
or vice versa, the rejection reason should explain why.

## Base Classifier

`PageClassifier` is a small centroid classifier. It is not LDA. The old LDA class
is effectively a compatibility wrapper around this classifier.

### Training Data

The default labels are:

```python
DEFAULT_LABELS = "0010101010101010100010100010101000101010"
```

These labels correspond to the first manually labelled training window. In the
current workflow, `main.py` loads training pages from:

```text
SongBook_BossaNova_1, preamble=30, max_pages=70
```

Other books can use those same training pages by passing `training_pages` into
`ClassificationEngine.set_pages_from_file()`.

### Scaling

During training:

1. The classifier takes the first `len(labels)` training pages.
2. It builds feature vectors using `page.features.as_vector()`.
3. It computes a mean and standard deviation for each feature.
4. It scales every vector as:

```python
(value - mean) / stdev
```

If a feature has zero variance, the standard deviation is treated as `1` to avoid
division by zero.

### Centroids

After scaling, the classifier computes one centroid for title pages and one
centroid for non-title pages.

Prediction works by:

1. Scaling the target page's feature vector.
2. Computing Euclidean distance to each centroid.
3. Choosing the nearest centroid.

This gives a first-pass page label. It is useful but not enough on its own,
because a page can visually resemble a title page while actually being a
continuation with large OCR noise.

## Sequence Refinement

`PageSequenceRefiner` is the second stage. It knows that pages are ordered and
that songs usually have a plausible length.

The refiner runs in this order:

1. Force the first non-empty processed page to be a title page.
2. Remove weak title-page predictions.
3. Recover missed title pages inside long or suspiciously long segments.
4. Remove weak title-page predictions again.

The second removal pass is important because recovering a title page can make a
neighboring title page newly suspicious.

### First Page Handling

The first page is normally treated as a title page. Empty pages are the exception.
If the first processed page has no extracted text lines, it is treated as
non-title. This avoids producing a `MISSING_TITLE_0-MISSING_ARTIST_0` split for
blank front matter.

If this happens often for a new document, the better fix may be to increase the
preamble.

### Removing Weak Title Pages

A predicted title page may be removed when:

- it has a hard rejection and the next page is a stronger title;
- it has a weak artist score and a weak title score;
- it has a very short title with a fragmented artist;
- it looks like continuation noise;
- it follows another title too closely without strong title signal;
- it lacks strong title signal overall.

### Hard Rejections

The following extraction reasons are considered hard evidence against a title
page:

- `fragmented title`
- `symbol-heavy title`
- `chord-like title`
- `chord-like artist`
- `header title`
- `low vowel ratio`
- `ocr-noise title`
- `fragmented artist`
- `weak short-title artist`

These are not always fatal by themselves. The refiner considers context, such as
whether the next page is a stronger title page. The aim is to avoid deleting real
titles that have a small amount of OCR damage.

### Continuation Noise

`_looks_like_continuation_noise()` handles a recurring pattern in the Bossa Nova
books: a continuation page contains large OCR fragments or staff/chord artifacts,
and the base classifier mistakes one of those fragments for a title.

The current checks are:

- If the extracted title is below the title band and the page is junk-heavy, the
  page is rejected unless the artist signal is strong.
- If the page contains absurdly large OCR glyphs, the page is rejected unless the
  artist signal is strong.

This is intentionally general. It does not check file names like
`Pgh in ceaeaip` or `xrH`. It checks the structural problem those names reveal.

### Duplicate Title Suppression

If two immediate title pages normalize to the same title, the second one is
suppressed. This handles OCR bleed-through where the same title is detected on
adjacent pages.

Normalization removes non-alphanumeric characters and lowercases the text.

### Recovering Missed Title Pages

The refiner also looks for missed title pages inside segments. A segment is the
range from one title page to the next title page.

For example:

```text
title page A
continuation
continuation
missed title page B
continuation
title page C
```

Without recovery, title page B would be swallowed into song A's split.

The recovery process:

1. Build all current segments from the current labels.
2. For each segment, scan pages after the segment start.
3. Keep pages that pass `_is_recovery_candidate()`.
4. Pick the candidate with the highest `_recovery_score()`.
5. Mark it as a title page.
6. Repeat until no segment changes.

### Recovery Score

The recovery score combines extraction confidence and broad page features:

```python
title_score * 0.45
+ artist_score * 0.25
+ title_candidate_score * 0.20
+ artist_candidate_score * 0.10
```

This gives the exact extracted title and artist most of the weight, but still
allows page-shape signals to help when OCR is slightly imperfect.

### Short-Segment Recovery

For short segments, recovery is conservative. A page must have:

- a plausible title page extraction;
- recovery score of at least `0.65`;
- title score of at least `0.74`;
- artist score of at least `0.45`.

This was added to recover one-page songs such as `Bo-ba-Iá-Iá` without creating
many false starts.

### Long-Segment Recovery

For longer-than-expected segments, recovery can be more aggressive because a long
segment often means a title was missed.

The page still must not have a hard rejection. If the page is already plausible,
it must also pass `_is_safe_long_segment_recovery()`.

Safe long-segment recovery accepts pages with:

- strong artist score; or
- a natural-looking multiword title and adequate artist score; or
- a natural-looking multiword title in the title band.

The natural-title check requires:

- at least two words;
- enough alphabetic text;
- a reasonable vowel ratio;
- no long word with no vowels.

This prevents OCR fragments like `By Et fetes yee` or `Palliiieg` from being
introduced as recovered titles while still allowing titles such as:

- `Pouca duracao`
- `eVivo sonhando`

### Single-Word Title Recovery

Some real titles are single words, such as `Wave` and `Emorio`. These are
recovered through the short-segment path when the title and artist scores are
strong enough. The model does not require every title to be multiword.

## Splitting

After classification and refinement, `ClassificationEngine.classify_pages()`:

1. obtains final labels from `PageClassifier.label_pages()`;
2. stores those labels in the `Transformer`;
3. writes each label back onto its `Page`;
4. gives the final pages to the `Transformer`.

The split rule is simple:

- whenever a page has label `0`, it starts a new output PDF;
- pages continue being added until the next label `0`;
- the output file name uses the extracted title and artist.

The report-generation scripts used during review follow the same logic, but
write timestamped folders under `reports/` so results can be compared safely.

## Current Review Results

The latest review report generated during this refactor is:

```text
reports/split_review_20260428_182753/index.md
```

The final counts in that report were:

```text
SongBook_BossaNova_1: 62
SongBook_BossaNova_2: 61
SongBook_BossaNova_3: 56
SongBook_BossaNova_4: 62
SongBook_BossaNova_5: 63
```

These numbers are not permanent ground truth. They are a snapshot after applying
the current model and the manually reviewed corrections known at that time.

## Validation Method Used During Refactor

The model was improved using a feedback loop:

1. Generate split PDFs and an index report.
2. Manually inspect suspicious splits.
3. Record false positives: continuation pages classified as titles.
4. Record false negatives: real title pages swallowed into the previous song.
5. Inspect feature/extraction signals for both groups.
6. Add general rules only when they separate the known false positives from the
   known false negatives.
7. Compare the new title-start set against the previous report.
8. Regenerate a new clickable report.

The most important command pattern was a diagnostic script that printed, for
specific page indexes:

- final label;
- title and artist;
- title and artist scores;
- title and artist vertical positions;
- candidate scores;
- max and mean font sizes;
- junk counts;
- rejection reasons;
- the largest text lines on the page.

This made it possible to see that many false positives were not isolated mistakes
but shared structural traits: fragmented artists, mid-page title candidates,
large OCR glyphs, and junk-heavy continuation pages.

## Known Examples Captured by the Current Rules

False positives now rejected:

- Bossa 2 page 64: chord/OCR continuation, previously `Ebs mat 2`.
- Bossa 3 pages 4, 24, 29, 55, 107: continuation pages with fragmented OCR.
- Bossa 4 pages 0, 32, 53, 77: blank or continuation pages.
- Bossa 5 pages 8, 14, 34, 42, 76, 81, 92, 98, 126: continuation pages.

False negatives now recovered:

- Bossa 1 page 42: `Bo-ba-Iá-Iá`.
- Bossa 2 pages 31, 39, 45, 47, 69, 98, 113.
- Bossa 3 pages 75, 103, 106: `Pouca duracao`, `eVivo sonhando`, `Wave`.
- Bossa 4 page 33: `Emorio`.

## How To Make Future Changes Safely

When improving the model for new documents:

1. Add manual labels where possible.
2. Generate a timestamped split review report.
3. Make a list of false positives and false negatives by book and page index.
4. Inspect both types together before changing code.
5. Prefer structural rules over filename-specific rules.
6. Keep recovery stricter than removal. False positives create extra files, but
   false negatives hide songs inside the previous PDF.
7. Compare old and new start-page sets before trusting the result.
8. Regenerate clickable PDFs after every meaningful model change.

## What Not To Do

Avoid hard-coding individual file names or song titles as classification rules.
For example, do not write a rule that says:

```text
if filename contains "Pgh in ceaeaip", reject it
```

Instead, identify the structural reason:

- title line is below the normal title band;
- artist line is fragmented;
- page is junk-heavy;
- line contains chord-like text;
- OCR produced absurdly large glyphs.

Rules based on structure are more likely to generalize to other songbooks.

## Future Improvements

The current model is intentionally simple and explainable. Useful next steps:

- Move known validation cases into a small checked-in fixture so regressions can
  be tested automatically.
- Store expected title-page indexes for each reviewed book.
- Add a command that prints old-vs-new boundary diffs for any report.
- Add more manual labels from books 2-5 instead of relying mostly on book 1.
- Consider training a small supervised model once enough labelled pages exist.
- Track title extraction quality separately from page-boundary quality.

The main principle should stay the same: every classifier change should be
validated against known false positives, known false negatives, and the full
start-page diff.
