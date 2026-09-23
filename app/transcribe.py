"""Audio extraction (ffmpeg) and speech-to-text (mlx-whisper)."""

import json
import shutil
import subprocess
from pathlib import Path

from .srt import Word

MODEL = "mlx-community/whisper-large-v3-turbo"


def extract_audio(video: Path, wav: Path) -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is not installed. Run: brew install ffmpeg")
    result = subprocess.run(
        ["ffmpeg", "-nostdin", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(wav)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        tail = "\n".join(result.stderr.strip().splitlines()[-5:])
        raise RuntimeError(f"Could not read audio from the video.\n{tail}")


def is_portrait(video: Path) -> bool:
    """True for vertical video (Reels/Shorts/TikTok), accounting for phone rotation metadata."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height:stream_side_data=rotation:stream_tags=rotate",
            "-of", "json", str(video),
        ],
        capture_output=True,
        text=True,
    )
    try:
        stream = json.loads(result.stdout)["streams"][0]
    except (json.JSONDecodeError, KeyError, IndexError):
        return False
    width, height = stream.get("width", 0), stream.get("height", 0)
    rotation = stream.get("tags", {}).get("rotate")
    for side in stream.get("side_data_list", []):
        rotation = side.get("rotation", rotation)
    if rotation is not None and abs(int(rotation)) % 180 == 90:
        width, height = height, width
    return height > width


def transcribe(wav: Path) -> list[Word]:
    import mlx_whisper  # imported lazily: slow to import and not needed for tests

    result = mlx_whisper.transcribe(
        str(wav),
        path_or_hf_repo=MODEL,
        language="en",
        word_timestamps=True,
        condition_on_previous_text=False,  # reduces repeated-phrase hallucinations
    )
    words: list[Word] = []
    for segment in result.get("segments", []):
        for w in segment.get("words", []):
            words.append(Word(w["word"], float(w["start"]), float(w["end"])))
    return words


def model_is_cached() -> bool:
    try:
        from huggingface_hub import try_to_load_from_cache

        return isinstance(try_to_load_from_cache(MODEL, "config.json"), str)
    except Exception:
        return False
