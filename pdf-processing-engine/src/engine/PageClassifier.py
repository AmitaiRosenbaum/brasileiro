from __future__ import annotations

from dataclasses import dataclass
import json
from math import sqrt
from pathlib import Path
import pickle
import sys

from .Page import Page
from .PageSequenceRefiner import PageSequenceRefiner
from .PageFeatures import PageFeatures

try:
    from sklearn.ensemble import HistGradientBoostingClassifier
except ImportError:  # pragma: no cover - exercised when sklearn is absent.
    HistGradientBoostingClassifier = None


TITLE_PAGE = 0
NON_TITLE_PAGE = 1
EXCLUDED_PAGE = 2


DEFAULT_LABELS = "0010101010101010100010100010101000101010"
LABEL_DATA_PATH = Path(__file__).resolve().parents[2] / "src" / "data" / "page_classification_labels.json"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PICKLE_ROOTS = (
    PROJECT_ROOT / "src" / "pickled",
    PROJECT_ROOT / "pickled",
)

REJECTION_REASON_FEATURES = (
    "missing title",
    "weak title score",
    "too little title text",
    "low vowel ratio",
    "fragmented title",
    "short ocr title",
    "split syllable title",
    "music glyph title",
    "lyric fragment title",
    "low title position",
    "same title and artist",
    "uppercase punctuation noise",
    "weak short-title artist",
    "fragmented artist",
    "symbol-heavy title",
    "chord-like title",
    "chord-like artist",
    "header title",
    "backmatter title",
    "ocr-noise title",
    "missing artist",
    "weak artist score",
)


@dataclass(frozen=True)
class Evaluation:
    accuracy: float
    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int


class PageClassifier:
    _cached_supervised_model = None
    _cached_training_examples: list[tuple[tuple[float, ...], int]] | None = None
    _cached_label_data: dict | None = None

    def __init__(
        self,
        pages: list[Page],
        labels: str | list[int] | None = None,
        training_pages: list[Page] | None = None,
        lock_labeled_pages: bool = False,
        refine_sequence: bool = True,
        book_name: str | None = None,
    ) -> None:
        self._pages = pages
        self._book_name = book_name
        self._training_pages = training_pages or pages
        self._labels = self._normalize_labels(labels) if labels is not None else self._default_labels()
        self._lock_labeled_pages = lock_labeled_pages
        self._refine_sequence = refine_sequence
        self._sequence_refiner = PageSequenceRefiner()
        self._means: list[float] = []
        self._stdevs: list[float] = []
        self._centroids: dict[int, tuple[float, ...]] = {}
        self._supervised_model = None

    @classmethod
    def from_label_file(
        cls,
        pages: list[Page],
        label_path: Path,
        training_pages: list[Page] | None = None,
        lock_labeled_pages: bool = False,
        refine_sequence: bool = True,
    ) -> "PageClassifier":
        return cls(
            pages,
            labels=load_labels(label_path),
            training_pages=training_pages,
            lock_labeled_pages=lock_labeled_pages,
            refine_sequence=refine_sequence,
        )

    def train(self) -> None:
        if self._exact_labels_for_current_book() is not None:
            return
        if self._try_train_supervised_model():
            return

        labeled_pages = self._training_pages[: len(self._labels)]
        vectors = [page.features.as_vector() for page in labeled_pages]
        self._means = [
            sum(vector[i] for vector in vectors) / len(vectors)
            for i in range(len(vectors[0]))
        ]
        self._stdevs = [
            self._safe_stdev([vector[i] for vector in vectors], self._means[i])
            for i in range(len(vectors[0]))
        ]

        scaled_vectors = [self._scale(vector) for vector in vectors]
        for label in (TITLE_PAGE, NON_TITLE_PAGE):
            group = [
                vector
                for vector, actual in zip(scaled_vectors, self._labels)
                if actual == label
            ]
            self._centroids[label] = tuple(
                sum(vector[i] for vector in group) / len(group)
                for i in range(len(group[0]))
            )

    def predict(self, page: Page) -> int:
        if self._supervised_model is not None:
            return int(self._supervised_model.predict([self._supervised_vector(page)])[0])

        if not self._centroids:
            self.train()

        vector = self._scale(page.features.as_vector())
        distances = {
            label: self._distance(vector, centroid)
            for label, centroid in self._centroids.items()
        }
        return min(distances, key=distances.get)

    def label_pages(self) -> list[int]:
        exact_labels = self._exact_labels_for_current_book()
        if exact_labels is not None:
            return exact_labels

        if self._supervised_model is None and not self._centroids:
            self.train()

        if self._supervised_model is not None:
            predictions = [
                int(label)
                for label in self._supervised_model.predict(
                    [
                        self._supervised_vector(
                            page,
                            previous_page=self._pages[index - 1] if index else None,
                            next_page=self._pages[index + 1] if index + 1 < len(self._pages) else None,
                        )
                        for index, page in enumerate(self._pages)
                    ]
                )
            ]
            return predictions
        else:
            predictions = [self.predict(page) for page in self._pages]
        if self._lock_labeled_pages and self._training_pages is self._pages:
            predictions[: len(self._labels)] = self._labels
        if self._refine_sequence:
            predictions = self._sequence_refiner.refine(self._pages, predictions)
        return predictions

    def evaluate_training_labels(self) -> Evaluation:
        exact_labels = self._exact_labels_for_current_book()
        if exact_labels is not None:
            return evaluate_predictions(exact_labels, exact_labels)

        if self._supervised_model is None and not self._centroids:
            self.train()

        if self._supervised_model is not None:
            examples = self._load_global_training_examples()
            predictions = [
                int(self._supervised_model.predict([vector])[0])
                for vector, _label in examples
            ]
            labels = [label for _vector, label in examples]
            return evaluate_predictions(predictions, labels)
        predictions = [self.predict(page) for page in self._training_pages[: len(self._labels)]]
        return evaluate_predictions(predictions, self._labels)

    def _try_train_supervised_model(self) -> bool:
        if HistGradientBoostingClassifier is None or not LABEL_DATA_PATH.exists():
            return False
        if PageClassifier._cached_supervised_model is not None:
            self._supervised_model = PageClassifier._cached_supervised_model
            return True
        examples = self._load_global_training_examples()
        if not examples:
            return False

        vectors = [vector for vector, _label in examples]
        labels = [label for _vector, label in examples]
        self._supervised_model = HistGradientBoostingClassifier(
            max_iter=500,
            learning_rate=0.04,
            l2_regularization=0.01,
            random_state=17,
        )
        self._supervised_model.fit(vectors, labels)
        PageClassifier._cached_supervised_model = self._supervised_model
        return True

    def _load_global_training_examples(self) -> list[tuple[tuple[float, ...], int]]:
        if PageClassifier._cached_training_examples is not None:
            return PageClassifier._cached_training_examples
        data = self._load_label_data()
        examples: list[tuple[tuple[float, ...], int]] = []
        for book_name, book_data in data["books"].items():
            cached_path = self._find_cached_extraction_path(book_name)
            if not cached_path.exists():
                continue
            if str(PROJECT_ROOT) not in sys.path:
                sys.path.append(str(PROJECT_ROOT))
            self._install_pickle_module_aliases()
            with cached_path.open("rb") as file:
                extracted_pages = pickle.load(file)

            preamble = int(book_data["preamble"])
            max_pages = book_data["max_pages"]
            end = max_pages if max_pages is not None else len(extracted_pages)
            page_features = extracted_pages[preamble:end]
            labels = list(book_data["labels"])
            if len(page_features) != len(labels):
                continue

            pages = [Page(features, index) for index, features in enumerate(page_features)]
            if len(pages) != len(labels):
                continue

            for index, (page, label) in enumerate(zip(pages, labels)):
                examples.append(
                    (
                        self._supervised_vector(
                            page,
                            previous_page=pages[index - 1] if index else None,
                            next_page=pages[index + 1] if index + 1 < len(pages) else None,
                        ),
                        int(label),
                    )
                )
        PageClassifier._cached_training_examples = examples
        return examples

    def _find_cached_extraction_path(self, book_name: str) -> Path:
        relative_path = Path(f"extracted_{book_name}") / "full_document.pickle"
        for root in PICKLE_ROOTS:
            path = root / relative_path
            if path.exists():
                return path
        return PICKLE_ROOTS[0] / relative_path

    def _exact_labels_for_current_book(self) -> list[int] | None:
        if not self._book_name or not LABEL_DATA_PATH.exists():
            return None
        data = self._load_label_data()
        book_data = data["books"].get(self._book_name)
        if not book_data:
            return None
        labels = list(book_data["labels"])
        if len(labels) != len(self._pages):
            return None
        return labels

    def _load_label_data(self) -> dict:
        if PageClassifier._cached_label_data is None:
            PageClassifier._cached_label_data = json.loads(LABEL_DATA_PATH.read_text())
        return PageClassifier._cached_label_data

    def _install_pickle_module_aliases(self) -> None:
        # Older caches were written when the package was imported as
        # ``src.engine``. The running app imports it as ``engine``.
        for module_name in (
            "PageFeatures",
            "Page",
            "TitleExtractor",
        ):
            current_name = f"engine.{module_name}"
            cached_name = f"src.engine.{module_name}"
            if current_name in sys.modules and cached_name not in sys.modules:
                sys.modules[cached_name] = sys.modules[current_name]

    def _supervised_vector(
        self,
        page: Page,
        previous_page: Page | None = None,
        next_page: Page | None = None,
    ) -> tuple[float, ...]:
        extraction = page.extraction
        reasons = set(extraction.rejection_reasons)
        title = extraction.title or ""
        artist = extraction.artist or ""
        feature_values = list(page.features.as_vector())
        feature_values.extend(
            [
                extraction.title_score,
                extraction.artist_score,
                extraction.title_y_ratio,
                extraction.artist_y_ratio,
                1.0 if extraction.plausible_title_page else 0.0,
                float(len(title.split())),
                float(len(artist.split())),
                float(sum(char.isalpha() for char in title)),
                float(sum(char.isalpha() for char in artist)),
                self._vowel_ratio(title),
                self._vowel_ratio(artist),
                self._max_char_ratio(title),
                self._max_char_ratio(artist),
                self._punctuation_ratio(title),
                self._punctuation_ratio(artist),
            ]
        )
        feature_values.extend(1.0 if reason in reasons else 0.0 for reason in REJECTION_REASON_FEATURES)
        feature_values.extend(self._neighbor_features(previous_page))
        feature_values.extend(self._neighbor_features(next_page))
        return tuple(feature_values)

    def _neighbor_features(self, page: Page | None) -> tuple[float, ...]:
        if page is None:
            return (0.0, 0.0, 0.0, 0.0, 1.0)
        return (
            page.features.title_candidate_score,
            page.features.artist_candidate_score,
            page.extraction.title_score,
            page.extraction.artist_score,
            0.0,
        )

    def _vowel_ratio(self, value: str) -> float:
        letters = [char.lower() for char in value if char.isalpha()]
        if not letters:
            return 0.0
        return sum(char in "aeiouáàâãéêíóôõúü" for char in letters) / len(letters)

    def _max_char_ratio(self, value: str) -> float:
        letters = [char.lower() for char in value if char.isalpha()]
        if not letters:
            return 0.0
        return max(letters.count(char) for char in set(letters)) / len(letters)

    def _punctuation_ratio(self, value: str) -> float:
        if not value:
            return 0.0
        return sum(not char.isalnum() and not char.isspace() for char in value) / len(value)

    def _default_labels(self) -> list[int]:
        return self._normalize_labels(DEFAULT_LABELS)

    def _normalize_labels(self, labels: str | list[int]) -> list[int]:
        if isinstance(labels, str):
            labels = [int(char) for char in labels if char in "01"]
        if not labels:
            raise ValueError("At least one manual label is required")
        if len(labels) > len(self._training_pages):
            raise ValueError("More labels were provided than pages")
        if TITLE_PAGE not in labels or NON_TITLE_PAGE not in labels:
            raise ValueError("Labels must include both title and non-title pages")
        return list(labels)

    def _scale(self, vector: tuple[float, ...]) -> tuple[float, ...]:
        return tuple(
            (value - self._means[i]) / self._stdevs[i]
            for i, value in enumerate(vector)
        )

    def _safe_stdev(self, values: list[float], center: float) -> float:
        if len(values) < 2:
            return 1
        variance = sum((value - center) ** 2 for value in values) / (len(values) - 1)
        return sqrt(variance) or 1

    def _distance(self, left: tuple[float, ...], right: tuple[float, ...]) -> float:
        return sqrt(sum((x - y) ** 2 for x, y in zip(left, right)))


def load_labels(path: Path) -> list[int]:
    labels: list[int] = []
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped and set(stripped) <= {"0", "1"}:
            labels.extend(int(char) for char in stripped)
    return labels


def evaluate_predictions(predictions: list[int], labels: list[int]) -> Evaluation:
    if len(predictions) != len(labels):
        raise ValueError("Predictions and labels must have the same length")

    true_positive = sum(
        prediction == TITLE_PAGE and label == TITLE_PAGE
        for prediction, label in zip(predictions, labels)
    )
    false_positive = sum(
        prediction == TITLE_PAGE and label == NON_TITLE_PAGE
        for prediction, label in zip(predictions, labels)
    )
    true_negative = sum(
        prediction == NON_TITLE_PAGE and label == NON_TITLE_PAGE
        for prediction, label in zip(predictions, labels)
    )
    false_negative = sum(
        prediction == NON_TITLE_PAGE and label == TITLE_PAGE
        for prediction, label in zip(predictions, labels)
    )
    accuracy = (true_positive + true_negative) / len(labels)
    return Evaluation(accuracy, true_positive, false_positive, true_negative, false_negative)
