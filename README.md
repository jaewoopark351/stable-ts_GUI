[한국어 문서](README_KO.md)

# stable-ts GUI Lyrics to SRT for Windows

This project is a Windows GUI workflow for turning a music file and an exact
lyrics TXT file into line-based SRT subtitles. It keeps the stable-ts source in
this repository and adds a focused GUI/CLI layer for lyrics alignment.

Unlike normal Whisper transcription, this workflow does not ask Whisper to write
new text. It uses stable-ts forced alignment with `model.align(..., original_split=True)`
so the provided lyrics are aligned to the audio line by line.

## Features

- Gradio GUI with local-file and upload tabs
- CLI support through `lyrics_to_srt.py`
- Whisper model choices: `large-v3`, `medium`, and `small`
- Device choices: `auto`, `cuda`, and `cpu`
- Automatic model downshift based on VRAM or CPU mode
- Optional Demucs vocal separation
- Optional VAD
- SRT output
- Alignment JSON output

## Supported Input

Audio files:

- `.mp3`
- `.wav`
- `.flac`
- `.m4a`

Lyrics files:

- `.txt`
- UTF-8 or UTF-8 with BOM is recommended

## Requirements

- Windows
- Python 3.11
- FFmpeg available in `PATH`
- CUDA-capable PyTorch installed in `.venv` if you want to use an NVIDIA GPU

All project Python commands should use:

```bat
.\.venv\Scripts\python.exe
```

Do not use global `python` or global `pip` for this project.

## Windows Installation

1. Install FFmpeg and make sure `ffmpeg` is available in `PATH`.
2. Install Python 3.11.
3. From this project folder, run:

```bat
install_windows.bat
```

The installer creates `.venv` if needed, installs this repository in editable
mode, installs the Windows requirements, checks `stable_whisper`, prints NVIDIA
and PyTorch/CUDA status, and runs `pip check`.

For GPU use, make sure the PyTorch installed inside `.venv` is a CUDA build that
matches your system. Confirm it with:

```bat
.\.venv\Scripts\python.exe -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.version.cuda)"
```

## Run the GUI

Use the provided launcher:

```bat
run_gui.bat
```

Or run it directly with the project virtual environment:

```bat
.\.venv\Scripts\python.exe app.py
```

The GUI opens a Gradio app. The local-file tab auto-fills the newest supported
audio file in `test` except `jfk.flac`, plus `test\lyrics.txt` when present.
The default output folder is `output`.

## CLI Example

`run_cli_example.bat` contains an editable example command. Replace the example
input paths with real files before running it.

Direct CLI example:

```bat
.\.venv\Scripts\python.exe lyrics_to_srt.py ^
  --audio "input\song.mp3" ^
  --lyrics "input\lyrics.txt" ^
  --output "output\song.srt" ^
  --language ko ^
  --model large-v3 ^
  --device auto
```

Useful options:

- `--model`: `large-v3`, `medium`, or `small`
- `--device`: `auto`, `cuda`, or `cpu`
- `--demucs`: use Demucs vocal separation
- `--vad`: use VAD
- `--json-output`: set the alignment JSON output path
- `--no-auto-model-adjust`: disable automatic model downshift

## Writing the Lyrics TXT

- Put one subtitle line per TXT line.
- Empty lines are removed.
- Leading and trailing spaces are removed.
- The file should match the song order exactly.
- Repeated choruses must be written again where they occur.
- Section labels such as `[Verse]` or `[Chorus]` are not removed automatically.
- The workflow does not correct, translate, or rewrite lyrics.

Alignment quality can drop when the TXT order differs from the audio, when
repeated sections are missing, or when lyrics include text that is not sung.

## Output Files

When only an output folder is provided, output files are created as:

- `output\song.srt`
- `output\song_alignment.json`

If `--output` is provided, the SRT path follows that value. If `--json-output`
is not provided, the JSON file is created next to the SRT with
`_alignment.json` added to the SRT stem.

The output folders are created automatically.

## Models and VRAM

The default GUI model is `large-v3`. With VRAM automatic adjustment enabled:

- `large-v3` is kept when enough CUDA VRAM is available.
- `large-v3` can be lowered to `medium` or `small` when free VRAM is limited.
- On CPU, `large-v3` is lowered to `medium` unless automatic adjustment is
  disabled.
- If you explicitly choose `medium` or `small`, that choice is kept.

The current approximate free-VRAM thresholds are:

- `large-v3`: 11.0 GiB
- `medium`: 5.5 GiB
- `small`: 2.5 GiB

The first use of a model may download model files through stable-ts/Whisper.
CPU alignment can be very slow, especially with larger models.

## Current Limits and Notes

- This is a lyrics forced-alignment workflow, not a general transcription tool.
- The provided lyrics must be accurate and in the same order as the audio.
- Demucs and VAD can improve some music cases but may increase processing time.
- FFmpeg is required for audio handling.
- Generated SRT, alignment JSON, model caches, and temporary files are local
  artifacts.
- Do not permanently store user-uploaded audio or lyrics files in the repository.

## Original Project and License

Based on stable-ts by Jian.
Windows GUI and lyrics-to-SRT workflow added by Jaewoo Park.

- Original stable-ts repository: https://github.com/jianfch/stable-ts
- License: MIT, see [LICENSE](LICENSE)
