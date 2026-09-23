# Video to SRT

**Free, offline subtitles for your Shorts and Reels, ready to import into CapCut.**

Drop in an English `.mp4`, get an `.srt` subtitle file with accurate timestamps, and import it into CapCut for free. You don't need CapCut Pro, an API key, or a subscription. Everything runs on your own Mac, and your videos never leave your computer.

```
1
00:00:00,000 --> 00:00:00,740
Despite enormous

2
00:00:00,740 --> 00:00:01,780
concerns about

3
00:00:01,780 --> 00:00:02,380
confusion
```

---

## Why this exists

CapCut's auto-captions need a Pro subscription, but importing an `.srt` subtitle file is free. This app makes that `.srt` file for you, using OpenAI's Whisper speech-recognition model running locally on Apple Silicon.

## Features

- **Free and private.** Transcription runs on your Mac. No accounts, no uploads to the cloud, no per-minute fees.
- **Works offline** after a one-time model download.
- **Built for Shorts / Reels / TikTok.** One short line per caption (max 22 characters), so CapCut's big caption fonts never wrap it into a wall of text.
- **Readable captions.** Splits at sentence ends and natural pauses, and never leaves a dangling "the", "and" or "of" at the end of a caption.
- **Horizontal mode** for YouTube-style videos (up to 2 balanced lines of 42 characters).
- **Word-level timing**, so captions appear exactly when the words are spoken.
- **Simple web page.** Drag, drop, download.

## Requirements

| Requirement | Why | Install |
|---|---|---|
| Mac with Apple Silicon (M1, M2, M3, M4 or newer) | The speech model uses Apple's MLX framework | none |
| [Homebrew](https://brew.sh) | Installs the tools below | See [brew.sh](https://brew.sh) |
| [ffmpeg](https://ffmpeg.org) | Pulls the audio out of your video | `brew install ffmpeg` |
| [uv](https://docs.astral.sh/uv/) | Installs Python and the app's dependencies | `brew install uv` |
| About 3 GB of free disk space | Speech model (~1.6 GB) and Python packages | none |

> Intel Macs, Windows and Linux are **not supported** right now, because the app uses [mlx-whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper), which only runs on Apple Silicon. See [Contributing](#contributing) if you'd like to help add them.

## Installation

1. Install the tools (skip any you already have):
   ```bash
   brew install ffmpeg uv
   ```
2. Download this project:
   ```bash
   git clone https://github.com/khan57/video-to-srt.git
   ```
   Or click **Code → Download ZIP** on GitHub and unzip it.
3. Go into the folder:
   ```bash
   cd video-to-srt
   ```

That's it. `uv` installs the right Python version and every dependency automatically the first time you run the app.

## Usage

1. Start the app:
   ```bash
   uv run video-to-srt
   ```
   Your browser opens at **http://127.0.0.1:8000**. If it doesn't, open that address yourself.
2. Drag your `.mp4` onto the page, or click the box to pick one.
3. Choose your options (the defaults suit Shorts/Reels):
   - **Video:** `Shorts / Reels (vertical)`, `Auto-detect` or `Horizontal (YouTube)`
   - **Caption length:** `Auto`, `Short (3 words)`, `Medium (5 words)` or `Long (8 words)`
4. Click **Generate subtitles** and wait. A timer shows progress.
5. Click **Download .srt**. The file has the same name as your video.
6. To stop the app, press **Ctrl+C** in the Terminal.

> **First run:** the app downloads the Whisper speech model (~1.6 GB) and saves it in `~/.cache/huggingface`. This happens once. After that, the app starts quickly and works without internet.

### Importing into CapCut

1. Open your project in CapCut.
2. Go to **Text → Local captions → Import** (on some versions: **Captions → Import captions**).
3. Pick the downloaded `.srt` file.
4. Style the captions however you like: font, colour, stroke, position.

Tip: if a caption still wraps onto two lines in CapCut, make the font slightly smaller or regenerate with **Caption length: Short (3 words)**.

## Options explained

### Video

| Option | Caption style | Best for |
|---|---|---|
| **Shorts / Reels (vertical)** *(default)* | 1 line, max 22 characters | YouTube Shorts, Instagram Reels, TikTok |
| **Auto-detect** | Picks vertical or horizontal from the video's dimensions (including phone rotation) | Mixed content |
| **Horizontal (YouTube)** | Up to 2 balanced lines, max 42 characters each | Regular widescreen video |

### Caption length

| Option | Behaviour |
|---|---|
| **Auto** *(default)* | Fills the line as much as fits. Breaks at sentence ends, at pauses longer than 0.6 s, and after at most 5 s. |
| **Short (3 words)** | Punchy, fast-paced captions |
| **Medium (5 words)** | A balance of pace and readability |
| **Long (8 words)** | Fewer, longer captions (the line limit above still applies) |

## Performance

On an M1 Mac, a 1-minute video usually transcribes in a few seconds to under half a minute. Newer chips are faster. Long videos work, but they take proportionally longer.

## Limitations

- **English only.** The model is told the audio is English.
- **MP4 only.** Convert other formats first, for example `ffmpeg -i input.mov output.mp4`.
- **Apple Silicon only** (see [Requirements](#requirements)).
- **Accuracy depends on the audio.** Loud music, heavy accents, overlapping speakers or unusual names can cause mistakes. Always skim the captions in CapCut before publishing.
- One video is processed at a time. If you upload several, they wait in a queue.

## Troubleshooting

| Problem | Fix |
|---|---|
| `command not found: uv` | Run `brew install uv`, then open a new Terminal window. |
| `ffmpeg is not installed` | Run `brew install ffmpeg`. |
| `Address already in use` | The app is already running in another Terminal window. Use that one, or close it with **Ctrl+C**. |
| "Only .mp4 files are supported" | Convert the video: `ffmpeg -i input.mov output.mp4`. |
| "Could not read audio from the video" | The video has no audio track, or the file is damaged. |
| First run seems stuck on "Downloading the speech model" | It's a ~1.6 GB download. Check your internet connection and give it time. |
| Captions are in the wrong place or wrap in CapCut | Resize or reposition them in CapCut, or use **Short (3 words)**. |

## How it works

```
 your .mp4
    │
    ▼
 ffmpeg ────────────► 16 kHz mono audio
    │
    ▼
 Whisper large-v3-turbo (mlx-whisper, on your Mac's GPU)
    │                 word-by-word text with timestamps
    ▼
 caption builder ───► groups words into short, readable captions
    │
    ▼
 your .srt
```

### Project structure

```
video-to-srt/
├── app/
│   ├── main.py          # Web server (FastAPI): upload, job status, download
│   ├── transcribe.py    # ffmpeg audio extraction, orientation detection, Whisper
│   ├── srt.py           # Turns timed words into captions and writes the SRT format
│   └── static/
│       └── index.html   # The drag-and-drop web page
├── tests/
│   └── test_srt.py      # Unit tests
├── pyproject.toml       # Dependencies and the `video-to-srt` command
└── README.md
```

### API

The web page uses a small local API that you can also script against:

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/jobs` | Form fields: `file` (the .mp4), `layout` (`vertical` / `auto` / `horizontal`), optional `max_words` (1–30). Returns `{"id": "..."}`. |
| `GET` | `/api/jobs/{id}` | Status: `queued`, `extracting`, `downloading-model`, `transcribing`, `done` or `error` |
| `GET` | `/api/jobs/{id}/srt` | Downloads the finished `.srt` |

Example:
```bash
curl -F "file=@myvideo.mp4" -F "layout=vertical" http://127.0.0.1:8000/api/jobs
```

The server listens only on `127.0.0.1`, so other devices on your network can't reach it.

## Development

```bash
uv sync            # install dependencies, including dev tools
uv run pytest      # run the tests
uv run uvicorn app.main:app --reload   # run the server with auto-reload, no browser pop-up
```

To tweak caption rules, edit the constants at the top of [`app/srt.py`](app/srt.py): `PORTRAIT`, `LANDSCAPE`, `MAX_DURATION`, `PAUSE_BREAK` and `WEAK_ENDINGS`.

## Contributing

Contributions are welcome. Ideas that would help:

- Support for Intel Macs, Windows and Linux (for example with [faster-whisper](https://github.com/SYSTRAN/faster-whisper))
- More input formats (`.mov`, `.mkv`, `.webm`)
- Other languages
- A progress percentage for long videos
- An in-browser caption editor before download

To contribute:
1. Fork the repository and create a branch.
2. Make your change and add tests where it makes sense.
3. Run `uv run pytest` and make sure everything passes.
4. Open a pull request describing what you changed and why.

Found a bug? Please open an issue with your macOS version, chip (M1/M2/…), and the error message.

## Credits

- [OpenAI Whisper](https://github.com/openai/whisper): the speech-recognition model (MIT License)
- [mlx-whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper) by Apple's MLX team: Whisper on Apple Silicon (MIT License)
- [mlx-community/whisper-large-v3-turbo](https://huggingface.co/mlx-community/whisper-large-v3-turbo): converted model weights
- [FFmpeg](https://ffmpeg.org), [FastAPI](https://fastapi.tiangolo.com), [uv](https://docs.astral.sh/uv/)

This project isn't affiliated with CapCut, ByteDance, OpenAI or Apple.

## License

Released under the [MIT License](LICENSE). You're free to use, copy, modify and share it, including for commercial use.
