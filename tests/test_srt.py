from fastapi.testclient import TestClient

from app.main import app
from app.srt import MAX_LINE_CHARS, PORTRAIT, Word, format_timestamp, group_words, to_srt


def words(text: str, start: float = 0.0, step: float = 0.3) -> list[Word]:
    out = []
    t = start
    for w in text.split():
        out.append(Word(" " + w, t, t + step - 0.05))
        t += step
    return out


def test_format_timestamp():
    assert format_timestamp(0) == "00:00:00,000"
    assert format_timestamp(1.25) == "00:00:01,250"
    assert format_timestamp(3725.5) == "01:02:05,500"
    assert format_timestamp(-1) == "00:00:00,000"


def test_sentence_end_starts_new_caption():
    caps = group_words(words("Hello there. How are you?"))
    assert [c.text for c in caps] == ["Hello there.", "How are you?"]


def test_pause_starts_new_caption():
    ws = words("one two") + words("three four", start=5.0)
    caps = group_words(ws)
    assert [c.text for c in caps] == ["one two", "three four"]


def test_lines_and_duration_limits():
    ws = words(" ".join(["word"] * 60), step=0.2)
    caps = group_words(ws)
    for c in caps:
        lines = c.text.split("\n")
        assert len(lines) <= 2
        assert all(len(line) <= MAX_LINE_CHARS for line in lines)
        assert c.end - c.start <= 5.0


def test_max_words():
    caps = group_words(words("a b c d e f g"), max_words=3)
    assert [c.text for c in caps] == ["a b c", "d e f", "g"]


def test_no_overlap_and_srt_shape():
    ws = [Word("Hi", 0.0, 1.5), Word("there", 1.2, 2.0)]
    caps = group_words(ws, max_words=1)
    assert caps[0].end <= caps[1].start
    srt = to_srt(caps)
    assert srt.startswith("1\n00:00:00,000 --> 00:00:01,200\nHi\n\n2\n")


def test_rejects_non_mp4():
    client = TestClient(app)
    res = client.post("/api/jobs", files={"file": ("clip.mov", b"x", "video/quicktime")})
    assert res.status_code == 400
    assert "mp4" in res.json()["detail"].lower()


def test_portrait_is_single_short_line():
    ws = words("Despite enormous concerns about confusion and accidents, the switch went smoothly.", step=0.25)
    caps = group_words(ws, layout=PORTRAIT)
    for c in caps:
        assert "\n" not in c.text
        assert len(c.text) <= PORTRAIT.max_line_chars


def test_caption_does_not_end_on_small_word():
    ws = words("Despite enormous concerns about confusion and accidents, the switch went smoothly.", step=0.25)
    for layout_caps in (group_words(ws), group_words(ws, layout=PORTRAIT), group_words(ws, max_words=3)):
        for c in layout_caps[:-1]:
            assert c.text.split()[-1].lower() not in {"the", "a", "and", "of", "to"}, c.text
