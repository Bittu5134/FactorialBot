"""Turns a factorial into a message worth replying with."""

import random
from dataclasses import dataclass

from . import config
from .factorials import (
    Factorial,
    digits,
    double_exact,
    exact,
    scientific_text,
    trailing_zeros,
)

_RNG = random.Random()


@dataclass(frozen=True)
class Answer:
    headline: str
    detail: str = ""
    footer: str = config.DEFAULT_FOOTER

    @property
    def text(self) -> str:
        lines = [f"### {self.headline}"]
        if self.detail:
            lines.append(self.detail)
        if self.footer:
            lines.append(f"-# {self.footer}")
        return "\n".join(lines)


EXACT_HEADLINES = (
    "{label} = {value}",
    "The factorial of {label} is {value}",
    "{label} is {value}, allegedly",
    "Okay fine, {label} = {value}",
    "{label} works out to {value}",
)

EXACT_TAILS = (
    "Yes, I counted. You're welcome.",
    "That's {count} digits of pure productivity.",
    "I did the math so you didn't have to. You still should.",
    "Write that down, it's going on the test.",
    "I was told not to compute this. I computed it anyway.",
    "Somebody had to multiply all of those. It was me.",
)

BIG_HEADLINES = (
    "{label} has {digits} digits",
    "The factorial of {label} has {digits} digits",
    "{label}? That's {digits} digits of nope",
    "Let's talk about {label}: {digits} digits",
)

BIG_TAILS = (
    "It ends in {zeros} zeros and starts around {sci}. I'm not typing the rest.",
    "That's {zeros} trailing zeros, starting with {sci}. You're on your own for the middle.",
    "Starts with {sci}, ends in {zeros} zeros. Everything in between is your problem.",
    "{zeros} zeros at the end, {sci} at the front. The middle is classified.",
    "Roughly {sci}, with {zeros} zeros dragging behind it. Happy now?",
)

HUGE_TAILS = (
    "**{digits} digits.** Reading that out loud at one digit per second would take {read_time}.",
    "**{digits} digits**, {zeros} of them zeros at the end. That's {read_time} of reading, if you're bored.",
    "It starts with {sci} and ends with {zeros} zeros. The other {digits} digits are between you and God.",
)

DOUBLE_TAILS = (
    "Double factorial, so I only multiplied every other number. Commitment issues, but faster.",
    "That's a double factorial: n × (n-2) × (n-4) × ... You asked, I answered.",
    "It's the double factorial. Every other number gets a turn. Very democratic.",
)

TRIVIAL_ZERO = (
    "One. Don't think about it too hard.",
    "0! is 1. Math agreed to this and we all moved on.",
    "One. A single unit of nothing. Beautiful.",
    "Yes, one. The empty product has one job and it does it.",
)

TRIVIAL_ONE = (
    "One. The most exciting factorial there is.",
    "Multiplication by one. Thrilling stuff.",
    "One. Don't spend it all at once.",
)

SASS = (
    "Nobody asked, but here we are.",
    "This message has been peer reviewed by nobody.",
    "I'm not a calculator. I'm a calculator with opinions.",
    "You're welcome, I think.",
)

READ_TIME_UNITS = (
    (60, 1, "second"),
    (3600, 60, "minute"),
    (86_400, 3_600, "hour"),
    (31_557_600, 86_400, "day"),
    (31_557_600 * 100, 31_557_600, "year"),
)


def _read_time(digit_count: int) -> str:
    """Reading a number aloud, one digit per second."""
    for limit, divisor, unit in READ_TIME_UNITS:
        if digit_count < limit:
            amount = max(1, round(digit_count / divisor))
            return f"{amount:,} {unit}{'s' if amount != 1 else ''}"
    return f"{digit_count // (31_557_600 * 100):,} centuries"


def _pick(pool: tuple[str, ...], rng: random.Random, **values: object) -> str:
    return rng.choice(pool).format(**values)
    