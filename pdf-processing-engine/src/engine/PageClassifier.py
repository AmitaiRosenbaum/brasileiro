from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from pathlib import Path

from .Page import Page
from .PageSequenceRefiner import PageSequenceRefiner


TITLE_PAGE = 0
NON_TITLE_PAGE = 1


DEFAULT_LABELS = "0010101010101010100010100010101000101010"


@dataclass(frozen=True)
class Evaluation:
    accuracy: float
    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int


class PageClassifier:
    def __init__(
        self,
        pages: list[Page],
        labels: str | list[int] | None = None,
        training_pages: list[Page] | None = None,
        lock_labeled_pages: bool = False,
        refine_sequence: bool = True,
    ) -> None:
        self._pages = pages
        self._training_pages = training_pages or pages
        self._labels = self._normalize_labels(labels) if labels is not None else self._default_labels()
        self._lock_labeled_pages = lock_labeled_pages
        self._refine_sequence = refine_sequence
        self._sequence_refiner = PageSequenceRefiner()
        self._means: list[float] = []
        self._stdevs: list[float] = []
        self._centroids: dict[int, tuple[float, ...]] = {}

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
        if not self._centroids:
            self.train()

        vector = self._scale(page.features.as_vector())
        distances = {
            label: self._distance(vector, centroid)
            for label, centroid in self._centroids.items()
        }
        return min(distances, key=distances.get)

    def label_pages(self) -> list[int]:
        if not self._centroids:
            self.train()

        predictions = [self.predict(page) for page in self._pages]
        if self._lock_labeled_pages and self._training_pages is self._pages:
            predictions[: len(self._labels)] = self._labels
        if self._refine_sequence:
            predictions = self._sequence_refiner.refine(self._pages, predictions)
        return predictions

    def evaluate_training_labels(self) -> Evaluation:
        if not self._centroids:
            self.train()

        predictions = [self.predict(page) for page in self._training_pages[: len(self._labels)]]
        return evaluate_predictions(predictions, self._labels)

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
