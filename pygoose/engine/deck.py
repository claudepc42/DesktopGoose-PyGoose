from .math_utils import get_rng


class Deck:
    def __init__(self, length: int):
        self.indices = list(range(length))
        self._i = 0
        self.reshuffle()

    def reshuffle(self):
        rng = get_rng()
        n = len(self.indices)
        for i in range(n):
            j = int(rng.random() * (i + 1))  # matches original: random_range(0, i) can return i
            self.indices[i], self.indices[j] = self.indices[j], self.indices[i]

    def next(self) -> int:
        result = self.indices[self._i]
        self._i += 1
        if self._i >= len(self.indices):
            self.reshuffle()
            self._i = 0
        return result
