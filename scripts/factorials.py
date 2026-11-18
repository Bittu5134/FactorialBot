"""Factorial detection and the math behind the answers."""

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
