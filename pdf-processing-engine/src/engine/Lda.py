from .Page import Page
from math import log


class Lda():
    def __init__(self, pages: list[Page]) -> None:
        self._pages = pages
        self._groups: int = 2
        self._mus: list[float] = [.0 for _ in range(self._groups)]
        self._sigma: float
        self._props: list[float]
        self._group_sizes: list[int]

        self._training_pages = self._pages[0:30]
        self._testing_pages = self._pages[30:40]

        self._training_labels: str = '001010101010101010001010001010'
        self._testing_labels: str = '1000101010'

    def train(self):
        self._compute_group_sizes()
        self._compute_mus()
        self._compute_sigma()
        self._compute_props()

    def _compute_group_sizes(self):
        self._group_sizes = list(
            map(lambda x: self._training_labels.count(x), '01'))

    def _compute_mus(self):
        totals = [0, 0]
        for i, page in enumerate(self._training_pages):
            group = int(self._training_labels[i])
            totals[group] += page.title_likelihood_index

        for i, total in enumerate(totals):
            self._mus[i] = total / self._group_sizes[i]

    def _compute_sigma(self):
        total = 0
        for i, page in enumerate(self._training_pages):
            group = int(self._training_labels[i])
            total += (page.title_likelihood_index - self._mus[group]) ** 2

        self._sigma = total / (sum(self._group_sizes) - len(self._group_sizes))

    def _compute_props(self):
        total = sum(self._group_sizes)
        self._props = [n / total for n in self._group_sizes]

    def predict(self, page: Page):
        x = page.title_likelihood_index
        return 0 if x > 6 else 1
        deltas = [x * mu / self._sigma - mu ** 2 /
                  (2 * self._sigma) + log(self._props[i]) for i, mu in enumerate(self._mus)]

        return deltas.index(max(deltas))

    def test(self, use_training_data=False) -> float:
        if use_training_data:
            pages = self._training_pages
            labels = self._training_labels
        else:
            pages = self._testing_pages
            labels = self._testing_labels
        success_count = sum([self.predict(page) == int(labels[i])
                            for i, page in enumerate(pages)])

        for i, page in enumerate(pages):
            if self.predict(page) != int(labels[i]):
                print(page)

        return success_count / len(labels)
