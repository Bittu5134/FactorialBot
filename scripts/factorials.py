"""Factorial detection and the math behind the answers."""

import math
import re
from dataclasses import dataclass

from . import config

# Matches "10!", "10 !" and "10!!"; the lookbehind excludes "3.14!" and "x2!".
FACTORIAL_RE = re.compile(
    rf"(?<![\w.])(\d{{1,{config.MAX_INPUT_DIGITS}}})\s*(!!|!)"
)


@dataclass(frozen=True)
class Factorial:
    n: int
    double: bool = False

    @property
    def label(self) -> str:
        return f"{self.n}{'!!' if self.double else '!'}"

    @property
    def is_trivial(self) -> bool:
        return self.n < 2


def find_factorals(text: str) -> list[Factorial]:
    """Every factorial in a message, in the order it appears."""
    found: list[Factorial] = []
    for match in FACTORIAL_RE.finditer(text):
        n = int(match.group(1))
        if n > config.MAX_N:
            continue
        found.append(Factorial(n=n, double=match.group(2) == "!!"))
    return found


def exact(n: int) -> int:
    """n! for values small enough to show in chat."""
    return math.factorial(n)


def double_exact(n: int) -> int:
    """n!! = n × (n-2) × (n-4) × ... × 1."""
    return math.prod(range(n, 0, -2))


def log10_factorial(n: int) -> float:
    """log10(n!) without ever building n!."""
    if n < 2:
        return 0.0
    if n <= 5000:
        return math.fsum(math.log10(i) for i in range(2, n + 1))
    # Stirling, with the first correction term.
    return (
        n * math.log10(n / math.e)
        + 0.5 * math.log10(2 * math.pi * n)
        + 1 / (12 * n * math.log(10))
    )
