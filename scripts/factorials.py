"""Factorial detection and the math behind the answers."""

import math
import re
from dataclasses import dataclass

from . import config

# Matches "10!", "10 !" and "10!!"; the lookbehind excludes "3.14!" and "x2!".
FACTORIAL_RE = re.compile(rf"(?<![\w.])(\d{{1,{config.MAX_INPUT_DIGITS}}})\s*(!!|!)")


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


def log10_double_factorial(n: int) -> float:
    """log10(n!!), via the two-factorials-that-fit-in-one trick."""
    if n < 2:
        return 0.0
    if n % 2 == 0:
        half = n // 2
        return half * math.log10(2) + log10_factorial(half)
    half = (n - 1) // 2
    return log10_factorial(n) - (half * math.log10(2) + log10_factorial(half))


def digits(n: int, double: bool = False) -> int:
    """How many decimal digits n! (or n!!) has."""
    log = log10_double_factorial(n) if double else log10_factorial(n)
    return math.floor(log) + 1


def trailing_zeros(n: int, double: bool = False) -> int:
    """How many zeros sit at the end of n! (or n!!)."""
    if double:
        if n % 2:
            return 0  # odd numbers can't make a factor of ten
        return trailing_zeros(n // 2)
    zeros = 0
    power = 5
    while power <= n:
        zeros += n // power
        power *= 5
    return zeros


def scientific(n: int, double: bool = False) -> tuple[float, int]:
    """n! as (mantissa, exponent): 100! -> (9.3326, 157)."""
    log = log10_double_factorial(n) if double else log10_factorial(n)
    exponent = math.floor(log)
    mantissa = 10 ** (log - exponent)
    if mantissa >= 10:  # float rounding, keep the mantissa in [1, 10)
        mantissa /= 10
        exponent += 1
    return mantissa, exponent


def scientific_text(n: int, double: bool = False) -> str:
    """9.3326 × 10^157, ready for a Discord message."""
    mantissa, exponent = scientific(n, double)
    power = f"{exponent:,}" if exponent >= 10_000 else str(exponent)
    return f"{mantissa:.{config.MANTISSA_DIGITS}f} × 10^{power}"


__all__ = [
    "Factorial",
    "digits",
    "double_exact",
    "exact",
    "find_factorals",
    "log10_double_factorial",
    "log10_factorial",
    "scientific",
    "scientific_text",
    "trailing_zeros",
]
