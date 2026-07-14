from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import gradio as gr
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Gradio가 설치되어 있지 않습니다. install_windows.bat을 먼저 실행하거나 "
        '".\\.venv\\Scripts\\python.exe -m pip install -r requirements-windows.txt"를 실행하세요.'
    ) from exc

from lyrics_to_srt import (
    AlignmentError,
    DEVICE_CHOICES,
    MODEL_CHOICES,
    SUPPORTED_AUDIO_EXTENSIONS,
    align_lyrics_to_srt,
)


PROJECT_ROOT = Path(__file__).resolve().parent
TEST_DIR = PROJECT_ROOT / "test"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"


def path_from_text(value: str) -> Path:
    return Path(value.strip().strip('"').strip("'"))


def find_default_audio() -> str:
    if not TEST_DIR.exists():
        return ""
    candidates = [
        path
        for path in TEST_DIR.iterdir()
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS
        and path.name.lower() != "jfk.flac"
    ]
    if not candidates:
        return ""
    candidates.sort(key=lambda item: (item.stat().st_mtime, item.stat().st_size), reverse=True)
    return str(candidates[0])


def find_default_lyrics() -> str:
    lyrics_path = TEST_DIR / "lyrics.txt"
    return str(lyrics_path) if lyrics_path.exists() else ""


def default_status() -> str:
    audio_path = find_default_audio()
    lyrics_path = find_default_lyrics()
    lines = [
        f"음원: {audio_path or '없음'}",
        f"가사: {lyrics_path or '없음'}",
        f"출력 폴더: {DEFAULT_OUTPUT_DIR}",
    ]
    return "\n".join(lines)


def _extract_path(file_value: Any) -> Path:
    if file_value is None:
        raise AlignmentError("필수 파일이 업로드되지 않았습니다.")
    if isinstance(file_value, (str, Path)):
        return Path(file_value)
    if isinstance(file_value, dict):
        value = file_value.get("path") or file_value.get("name")
        if value:
            return Path(value)
    name = getattr(file_value, "name", None)
    if name:
        return Path(name)
    raise AlignmentError("업로드된 파일 경로를 확인할 수 없습니다.")


def convert(
    audio_file: Any,
    lyrics_file: Any,
    model_name: str,
    language: str,
    use_demucs: bool,
    use_vad: bool,
    output_dir: str,
    auto_adjust_model: bool,
) -> tuple[str, str | None, str | None]:
    logs: list[str] = []

    def collect_log(message: str) -> None:
        logs.append(message)

    try:
        audio_path = _extract_path(audio_file)
        lyrics_path = _extract_path(lyrics_file)
        target_dir = Path(output_dir.strip()) if output_dir and output_dir.strip() else Path("output")
        result = align_lyrics_to_srt(
            audio=audio_path,
            lyrics=lyrics_path,
            output_dir=target_dir,
            language=language.strip() or "ko",
            model_name=model_name,
            use_demucs=use_demucs,
            use_vad=use_vad,
            device="auto",
            auto_adjust_model=auto_adjust_model,
            log_callback=collect_log,
        )
        return "\n".join(result.logs), str(result.srt_path), str(result.json_path)
    except AlignmentError as exc:
        logs.append(f"오류: {exc}")
    except ModuleNotFoundError as exc:
        logs.append(
            "오류: 필요한 Python 패키지가 설치되어 있지 않습니다. "
            f"install_windows.bat을 먼저 실행하세요. 누락된 모듈: {exc.name}"
        )
    except Exception as exc:
        logs.append(f"오류: 변환 중 예기치 않은 문제가 발생했습니다: {exc}")

    return "\n".join(logs), None, None


def convert_from_paths(
    audio_path_text: str,
    lyrics_path_text: str,
    model_name: str,
    language: str,
    use_demucs: bool,
    use_vad: bool,
    output_dir: str,
    device: str,
    auto_adjust_model: bool,
) -> tuple[str, str | None, str | None]:
    logs: list[str] = []

    def collect_log(message: str) -> None:
        logs.append(message)

    try:
        if not audio_path_text.strip():
            raise AlignmentError("음원 경로가 비어 있습니다.")
        if not lyrics_path_text.strip():
            raise AlignmentError("가사 TXT 경로가 비어 있습니다.")
        target_dir = Path(output_dir.strip()) if output_dir and output_dir.strip() else DEFAULT_OUTPUT_DIR
        result = align_lyrics_to_srt(
            audio=path_from_text(audio_path_text),
            lyrics=path_from_text(lyrics_path_text),
            output_dir=target_dir,
            language=language.strip() or "ko",
            model_name=model_name,
            use_demucs=use_demucs,
            use_vad=use_vad,
            device=device,
            auto_adjust_model=auto_adjust_model,
            log_callback=collect_log,
        )
        return "\n".join(result.logs), str(result.srt_path), str(result.json_path)
    except AlignmentError as exc:
        logs.append(f"오류: {exc}")
    except ModuleNotFoundError as exc:
        logs.append(
            "오류: 필요한 Python 패키지가 설치되어 있지 않습니다. "
            f"install_windows.bat을 먼저 실행하세요. 누락된 모듈: {exc.name}"
        )
    except Exception as exc:
        logs.append(f"오류: 변환 중 예기치 않은 문제가 발생했습니다: {exc}")

    return "\n".join(logs), None, None


def refresh_defaults() -> tuple[str, str, str]:
    return find_default_audio(), find_default_lyrics(), default_status()


def build_app() -> gr.Blocks:
    with gr.Blocks(title="음악 + 가사 TXT → SRT") as demo:
        gr.Markdown("# 음악 + 가사 TXT → SRT")

        with gr.Tab("로컬 파일"):
            with gr.Row():
                audio_path = gr.Textbox(label="음원 경로", value=find_default_audio(), scale=3)
                lyrics_path = gr.Textbox(label="가사 TXT 경로", value=find_default_lyrics(), scale=2)

            with gr.Row():
                output_dir = gr.Textbox(label="출력 폴더", value=str(DEFAULT_OUTPUT_DIR), scale=2)
                model_name = gr.Dropdown(
                    label="Whisper 모델",
                    choices=list(MODEL_CHOICES),
                    value="large-v3",
                    scale=1,
                )
                device = gr.Dropdown(label="장치", choices=list(DEVICE_CHOICES), value="auto", scale=1)
                language = gr.Textbox(label="언어 코드", value="ko", scale=1)

            with gr.Row():
                use_demucs = gr.Checkbox(label="Demucs", value=False)
                use_vad = gr.Checkbox(label="VAD", value=False)
                auto_adjust_model = gr.Checkbox(label="VRAM 자동 조정", value=True)
                refresh_button = gr.Button("새로고침")
                convert_button = gr.Button("변환 시작", variant="primary")

            status_box = gr.Textbox(label="현재 입력", value=default_status(), lines=3)
            log_box = gr.Textbox(label="진행 로그", lines=14)

            with gr.Row():
                srt_download = gr.File(label="SRT")
                json_download = gr.File(label="JSON")

            refresh_button.click(
                fn=refresh_defaults,
                inputs=[],
                outputs=[audio_path, lyrics_path, status_box],
            )
            convert_button.click(
                fn=convert_from_paths,
                inputs=[
                    audio_path,
                    lyrics_path,
                    model_name,
                    language,
                    use_demucs,
                    use_vad,
                    output_dir,
                    device,
                    auto_adjust_model,
                ],
                outputs=[log_box, srt_download, json_download],
            )

        with gr.Tab("업로드"):
            with gr.Row():
                audio_file = gr.File(
                    label="음악 파일",
                    file_types=[".mp3", ".wav", ".flac", ".m4a"],
                    type="filepath",
                )
                lyrics_file = gr.File(label="가사 TXT", file_types=[".txt"], type="filepath")

            with gr.Row():
                upload_output_dir = gr.Textbox(label="출력 폴더", value=str(DEFAULT_OUTPUT_DIR), scale=2)
                upload_model_name = gr.Dropdown(
                    label="Whisper 모델",
                    choices=list(MODEL_CHOICES),
                    value="large-v3",
                    scale=1,
                )
                upload_language = gr.Textbox(label="언어 코드", value="ko", scale=1)

            with gr.Row():
                upload_use_demucs = gr.Checkbox(label="Demucs", value=False)
                upload_use_vad = gr.Checkbox(label="VAD", value=False)
                upload_auto_adjust_model = gr.Checkbox(label="VRAM 자동 조정", value=True)
                upload_convert_button = gr.Button("변환 시작", variant="primary")

            upload_log_box = gr.Textbox(label="진행 로그", lines=14)

            with gr.Row():
                upload_srt_download = gr.File(label="SRT")
                upload_json_download = gr.File(label="JSON")

            upload_convert_button.click(
                fn=convert,
                inputs=[
                    audio_file,
                    lyrics_file,
                    upload_model_name,
                    upload_language,
                    upload_use_demucs,
                    upload_use_vad,
                    upload_output_dir,
                    upload_auto_adjust_model,
                ],
                outputs=[upload_log_box, upload_srt_download, upload_json_download],
            )

    return demo


if __name__ == "__main__":
    build_app().launch(inbrowser=True)
