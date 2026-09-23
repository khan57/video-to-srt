"""Turn word-level timestamps into short, readable SRT captions."""

from dataclasses import dataclass

MAX_DURATION = 5.0  # seconds per caption
PAUSE_BREAK = 0.6  # a silence longer than this starts a new caption
SENTENCE_END = (".", "?", "!")
# Words that read badly as the last word of a caption ("...accidents, the").
WEAK_ENDINGS = {
    "a", "an", "the", "and", "or", "but", "of", "to", "in", "on", "at", "for",
    "with", "by", "from", "as", "is", "was", "that", "this", "my", "your", "his",
    "her", "their", "our", "its", "i", "we", "you", "he", "she", "they", "it",
}


@dataclass
class Layout:
    max_line_chars: int
    max_lines: int


LANDSCAPE = Layout(max_line_chars=42, max_lines=2)
PORTRAIT = Layout(max_line_chars=22, max_lines=1)  # vertical video: big text, narrow frame
MAX_LINE_CHARS = LANDSCAPE.max_line_chars


@dataclass
class Word:
    text: str
    start: float
    end: float


@dataclass
class Caption:
    start: float
    end: float
    text: str


def format_timestamp(seconds: float) -> str:
    """0 -> '00:00:00,000'"""
    ms = max(0, round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def wrap_lines(words: list[str], max_chars: int) -> list[str]:
    """Greedy word wrap."""
    lines: list[str] = []
    current = ""
    for w in words:
        candidate = f"{current} {w}" if current else w
        if current and len(candidate) > max_chars:
            lines.append(current)
            current = w
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _fits(words: list[str], layout: Layout) -> bool:
    return len(wrap_lines(words, layout.max_line_chars)) <= layout.max_lines


def _balanced(words: list[str], layout: Layout) -> str:
    """Two-line captions read best when the lines are roughly equal length."""
    text = " ".join(words)
    if len(text) <= layout.max_line_chars or layout.max_lines < 2:
        return text
    best = None
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        if len(a) > layout.max_line_chars or len(b) > layout.max_line_chars:
            continue
        score = abs(len(a) - len(b))
        if best is None or score < best[0]:
            best = (score, a, b)
    if best is None:
        return "\n".join(wrap_lines(words, layout.max_line_chars))
    return f"{best[1]}\n{best[2]}"


def _is_weak(word: Word) -> bool:
    return word.text.lower().strip(".,!?;:\"'") in WEAK_ENDINGS and not word.text.endswith((",", ".", "?", "!"))


def group_words(
    words: list[Word], max_words: int | None = None, layout: Layout = LANDSCAPE
) -> list[Caption]:
    captions: list[Caption] = []
    group: list[Word] = []

    def emit(ws: list[Word]) -> None:
        texts = [w.text for w in ws]
        captions.append(Caption(ws[0].start, ws[-1].end, _balanced(texts, layout)))

    def flush(forced: bool) -> None:
        """forced=True means we are splitting mid-phrase, so carry a dangling small word forward."""
        nonlocal group
        if not group:
            return
        carry: list[Word] = []
        if forced:
            while len(group) > 1 and _is_weak(group[-1]):
                carry.insert(0, group.pop())
        emit(group)
        group = carry

    for word in words:
        text = word.text.strip()
        if not text:
            continue
        word = Word(text, word.start, word.end)
        if group:
            prev = group[-1]
            too_long = word.end - group[0].start > MAX_DURATION
            paused = word.start - prev.end > PAUSE_BREAK
            sentence_done = prev.text.endswith(SENTENCE_END)
            overflow = not _fits([w.text for w in group] + [text], layout)
            too_many = max_words is not None and len(group) >= max_words
            if paused or sentence_done:
                flush(forced=False)
            elif too_long or overflow or too_many:
                flush(forced=True)
        group.append(word)
    flush(forced=False)

    # Never let one caption overlap the next.
    for cur, nxt in zip(captions, captions[1:]):
        if cur.end > nxt.start:
            cur.end = nxt.start
    return captions


def to_srt(captions: list[Caption]) -> str:
    blocks = [
        f"{i}\n{format_timestamp(c.start)} --> {format_timestamp(c.end)}\n{c.text}\n"
        for i, c in enumerate(captions, start=1)
    ]
    return "\n".join(blocks)
