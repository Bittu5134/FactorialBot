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


def compose(
    f: Factorial, *, rng: random.Random | None = None, extra: str = ""
) -> Answer:
    """A full reply for one detected factorial."""
    rng = rng or _RNG

    if f.is_trivial:
        headline = f"{f.label} = 1"
        detail = _trivial(f, rng)
    elif f.n <= config.EXACT_MAX_N:
        value = _value(f)
        headline = _pick(EXACT_HEADLINES, rng, label=f.label, value=f"{value:,}")
        detail = _exact_answer(f, value, rng)
    else:
        headline = _pick(_headlines(f), rng, **_big_values(f))
        detail = _big_answer(f, rng)

    if extra:
        detail = f"{detail}\n{extra}"

    return Answer(headline=headline, detail=detail, footer=_pick(_FOOTERS, rng))


def refuse(n: int) -> Answer:
    """A polite no for numbers the bot refuses to multiply."""
    return Answer(
        headline="No.",
        detail=(
            f"{n:,}! would have more digits than I have patience. "
            f"Try something under {config.MAX_N:,}."
        ),
        footer="I have limits, and they're surprisingly low.",
    )


def refuse_negative(n: int) -> Answer:
    return Answer(
        headline="No.",
        detail=(
            f"{n:,}! is not a thing. Factorials count down to 1 and stop, "
            "not backwards into your feelings."
        ),
        footer="Try a number that exists.",
    )


def too_many(
    found: list[Factorial], limit: int = config.MAX_EXTRA_MENTIONS
) -> str:
    """A dismissive footnote for messages stuffed with factorials."""
    labels = ", ".join(f.label for f in found[:limit])
    hidden = len(found) - limit
    if hidden > 0:
        labels += f" and {hidden} more"
    return f"-# Also spotted {labels}. One factorial per message, please."


_FOOTERS = (
    config.DEFAULT_FOOTER,
    "FactorialBot • accuracy not guaranteed",
    "FactorialBot • I accept tips in factorials",
    "FactorialBot • this is not financial advice",
    "/factorial • /factstats",
)


def _headlines(f: Factorial) -> tuple[str, ...]:
    if f.double:
        return (
            "{label} has {digits} digits",
            "The double factorial of {label} has {digits} digits",
            "{label}? That's {digits} digits of double trouble",
        )
    return BIG_HEADLINES


def _big_values(f: Factorial) -> dict[str, object]:
    return {
        "label": f.label,
        "n": f.n,
        "digits": f"{digits(f.n, f.double):,}",
        "zeros": f"{trailing_zeros(f.n, f.double):,}",
        "sci": scientific_text(f.n, f.double),
    }


def _value(f: Factorial) -> int:
    return double_exact(f.n) if f.double else exact(f.n)


def _trivial(f: Factorial, rng: random.Random) -> str:
    pool = TRIVIAL_ZERO if f.n == 0 else TRIVIAL_ONE
    return rng.choice(pool)


def _exact_answer(f: Factorial, value: int, rng: random.Random) -> str:
    tail = _pick(
        EXACT_TAILS,
        rng,
        count=f"{len(str(value))}",
        label=f.label,
        value=f"{value:,}",
    )
    if rng.random() < 0.2:
        tail = f"{tail} {rng.choice(SASS)}"
    return tail


def _big_answer(f: Factorial, rng: random.Random) -> str:
    count = digits(f.n, f.double)
    zeros = trailing_zeros(f.n, f.double)
    values = {
        "digits": f"{count:,}",
        "zeros": f"{zeros:,}",
        "sci": scientific_text(f.n, f.double),
        "read_time": _read_time(count),
        "label": f.label,
    }

    if f.double:
        tail = _pick(DOUBLE_TAILS, rng, **values)
        if zeros:
            return f"{tail} It ends in {values['zeros']} zeros."
        return f"{tail} It ends in something odd, so no zeros there."

    if count >= 1_000_000:
        return _pick(HUGE_TAILS, rng, **values)
    return _pick(BIG_TAILS, rng, **values)


__all__ = ["Answer", "compose", "refuse", "refuse_negative", "too_many"]
