from __future__ import annotations

from .Page import Page
from .PageClassifier import PageClassifier


class Lda(PageClassifier):
    """
    Backwards-compatible alias for the old classifier entry point.

    The previous implementation was named Lda, but the task is supervised page
    classification rather than topic modelling. New code should import
    PageClassifier directly.
    """

    def __init__(self, pages: list[Page]) -> None:
        super().__init__(pages)

    def test(self, use_training_data=False) -> float:
        evaluation = self.evaluate_training_labels()
        return evaluation.accuracy
