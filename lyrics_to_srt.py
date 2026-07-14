from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional


MODEL_CHOICES = ("large-v3", "medium", "small")
DEVICE_CHOICES = ("auto", "cuda", "cpu")
SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a"}
MODEL_VRAM_THRESHOLDS_GIB = {
    "large-v3": 11.0,
    "medium": 5.5,
    "small": 2.5,
}

MODEL_CACHE: dict[tuple[str, str], object] = {}


class AlignmentError(RuntimeError):
    """User-facing conversion error."""


@dataclass
class ConversionResult:
    srt_path: Path
    json_path: Path
    logs: list[str]
    lyric_line_count: int
    segment_count: int


def read_lyrics(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8-sig")
    lines = [line.strip() for line in text.splitlines()]
    cleaned = [line for line in lines if line]
    if not cleaned:
        raise AlignmentError("가사 TXT에 변환할 줄이 없습니다. 빈 줄이 아닌 가사를 입력하세요.")
    return cleaned


def check_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise AlignmentError("FFmpeg를 찾을 수 없습니다. FFmpeg를 설치하고 PATH에 등록한 뒤 다시 실행하세요.")


def check_demucs_available() -> None:
    if importlib.util.find_spec("demucs") is None:
        raise AlignmentError(
            "Demucs가 설치되어 있지 않습니다. 보컬 분리를 사용하려면 먼저 "
            '".\\.venv\\Scripts\\python.exe -m pip install demucs" 명령으로 설치하세요.'
        )


def validate_audio_path(path: Path) -> Path:
    if not path.exists():
        raise AlignmentError(f"음악 파일을 찾을 수 없습니다: {path}")
    if not path.is_file():
        raise AlignmentError(f"음악 입력은 파일이어야 합니다: {path}")
    if path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_AUDIO_EXTENSIONS))
        raise AlignmentError(f"지원하지 않는 음악 파일 형식입니다: {path.suffix} (지원: {supported})")
    return path


def validate_lyrics_path(path: Path) -> Path:
    if not path.exists():
        raise AlignmentError(f"가사 TXT 파일을 찾을 수 없습니다: {path}")
    if not path.is_file():
        raise AlignmentError(f"가사 입력은 파일이어야 합니다: {path}")
    if path.suffix.lower() != ".txt":
        raise AlignmentError("가사 파일은 UTF-8 TXT 형식이어야 합니다.")
    return path


def build_output_paths(
    audio_path: Path,
    output: Optional[Path] = None,
    json_output: Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> tuple[Path, Path]:
    if output is None:
        base_dir = output_dir if output_dir is not None else Path("output")
        output = base_dir / f"{audio_path.stem}.srt"
    elif output.suffix.lower() != ".srt":
        output = output.with_suffix(".srt")

    if json_output is None:
        json_output = output.with_name(f"{output.stem}_alignment.json")
    elif json_output.suffix.lower() != ".json":
        json_output = json_output.with_suffix(".json")

    output.parent.mkdir(parents=True, exist_ok=True)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    return output, json_output


def emit_log(logs: list[str], message: str, callback: Optional[Callable[[str], None]]) -> None:
    logs.append(message)
    if callback is not None:
        callback(message)


def resolve_device(device: str, logs: list[str], callback: Optional[Callable[[str], None]] = None) -> str:
    import torch

    if device == "auto":
        resolved = "cuda" if torch.cuda.is_available() else "cpu"
    elif device == "cuda":
        if not torch.cuda.is_available():
            raise AlignmentError("CUDA를 사용할 수 없습니다. --device auto 또는 --device cpu로 다시 실행하세요.")
        resolved = "cuda"
    else:
        resolved = "cpu"

    cuda_text = "사용 가능" if torch.cuda.is_available() else "사용 불가"
    emit_log(logs, f"장치 선택: {resolved} (CUDA {cuda_text})", callback)
    return resolved


def get_cuda_vram_gib() -> tuple[float, float]:
    import torch

    props = torch.cuda.get_device_properties(0)
    total_gib = props.total_memory / (1024 ** 3)
    try:
        free_bytes, total_bytes = torch.cuda.mem_get_info(0)
        free_gib = free_bytes / (1024 ** 3)
        total_gib = total_bytes / (1024 ** 3)
    except Exception:
        free_gib = total_gib
    return free_gib, total_gib


def select_model_for_hardware(
    requested_model: str,
    device: str,
    auto_adjust_model: bool,
    logs: list[str],
    callback: Optional[Callable[[str], None]] = None,
) -> str:
    if not auto_adjust_model:
        emit_log(logs, f"모델 자동 조정 해제: {requested_model}", callback)
        return requested_model

    if requested_model != "large-v3":
        emit_log(logs, f"모델 자동 조정: 요청 모델 {requested_model} 유지", callback)
        return requested_model

    if device != "cuda":
        adjusted = "medium"
        emit_log(
            logs,
            "CUDA를 사용할 수 없어 CPU 기준으로 모델을 medium으로 낮춥니다. "
            "large-v3를 강제로 쓰려면 자동 조정을 끄세요.",
            callback,
        )
        return adjusted

    free_gib, total_gib = get_cuda_vram_gib()
    emit_log(logs, f"GPU VRAM: 사용 가능 {free_gib:.1f} GiB / 전체 {total_gib:.1f} GiB", callback)
    for model_name in MODEL_CHOICES:
        if free_gib >= MODEL_VRAM_THRESHOLDS_GIB[model_name]:
            if model_name != requested_model:
                emit_log(
                    logs,
                    f"VRAM 여유가 부족해 모델을 {requested_model}에서 {model_name}으로 낮춥니다.",
                    callback,
                )
            else:
                emit_log(logs, "VRAM 여유가 충분해 large-v3를 사용합니다.", callback)
            return model_name

    emit_log(logs, "VRAM 여유가 매우 적어 small 모델을 사용합니다.", callback)
    return "small"


def get_model(model_name: str, device: str, logs: list[str], callback: Optional[Callable[[str], None]] = None):
    import stable_whisper

    cache_key = (model_name, device)
    if cache_key in MODEL_CACHE:
        emit_log(logs, f"모델 캐시 재사용: {model_name} / {device}", callback)
        return MODEL_CACHE[cache_key]

    emit_log(logs, f"모델 로딩 시작: {model_name} / {device}", callback)
    model = stable_whisper.load_model(model_name, device=device)
    MODEL_CACHE[cache_key] = model
    emit_log(logs, f"모델 로딩 완료: {model_name}", callback)
    return model


def align_lyrics_to_srt(
    audio: Path | str,
    lyrics: Path | str,
    output: Optional[Path | str] = None,
    language: str = "ko",
    model_name: str = "large-v3",
    use_demucs: bool = False,
    use_vad: bool = False,
    json_output: Optional[Path | str] = None,
    device: str = "auto",
    output_dir: Optional[Path | str] = None,
    auto_adjust_model: bool = True,
    log_callback: Optional[Callable[[str], None]] = None,
) -> ConversionResult:
    logs: list[str] = []

    if model_name not in MODEL_CHOICES:
        raise AlignmentError(f"지원하지 않는 모델입니다: {model_name}")
    if device not in DEVICE_CHOICES:
        raise AlignmentError(f"지원하지 않는 장치 값입니다: {device}")

    audio_path = validate_audio_path(Path(audio))
    lyrics_path = validate_lyrics_path(Path(lyrics))
    srt_path, json_path = build_output_paths(
        audio_path=audio_path,
        output=Path(output) if output is not None else None,
        json_output=Path(json_output) if json_output is not None else None,
        output_dir=Path(output_dir) if output_dir else None,
    )

    emit_log(logs, f"음악 파일: {audio_path}", log_callback)
    emit_log(logs, f"가사 파일: {lyrics_path}", log_callback)
    emit_log(logs, f"SRT 출력: {srt_path}", log_callback)
    emit_log(logs, f"JSON 출력: {json_path}", log_callback)

    check_ffmpeg()
    emit_log(logs, "FFmpeg 확인 완료", log_callback)

    lyric_lines = read_lyrics(lyrics_path)
    alignment_text = "\n".join(lyric_lines)
    emit_log(logs, f"가사 줄 수: {len(lyric_lines)}", log_callback)
    emit_log(
        logs,
        "주의: 가사와 음원의 순서가 다르거나 반복 구간이 누락된 경우 정렬 정확도가 낮아질 수 있습니다.",
        log_callback,
    )

    if use_demucs:
        check_demucs_available()
        emit_log(logs, "Demucs 보컬 분리 사용", log_callback)
    else:
        emit_log(logs, "Demucs 보컬 분리 미사용", log_callback)

    emit_log(logs, f"VAD 사용: {'예' if use_vad else '아니오'}", log_callback)
    resolved_device = resolve_device(device, logs, log_callback)
    effective_model_name = select_model_for_hardware(
        model_name,
        resolved_device,
        auto_adjust_model,
        logs,
        log_callback,
    )
    model = get_model(effective_model_name, resolved_device, logs, log_callback)

    emit_log(logs, "forced alignment 시작", log_callback)
    result = model.align(
        str(audio_path),
        alignment_text,
        language=language,
        original_split=True,
        denoiser="demucs" if use_demucs else None,
        vad=use_vad,
        verbose=False,
    )
    if result is None:
        raise AlignmentError("정렬 결과가 비어 있습니다. 가사와 음원 길이 또는 순서를 확인하세요.")

    segment_count = len(result)
    if segment_count != len(lyric_lines):
        emit_log(
            logs,
            f"주의: 가사 줄 수({len(lyric_lines)})와 정렬 세그먼트 수({segment_count})가 다릅니다.",
            log_callback,
        )

    result.to_srt_vtt(str(srt_path), segment_level=True, word_level=False)
    emit_log(logs, f"SRT 저장 완료: {srt_path}", log_callback)
    result.save_as_json(str(json_path), ensure_ascii=False)
    emit_log(logs, f"JSON 저장 완료: {json_path}", log_callback)
    emit_log(logs, "변환 완료", log_callback)

    return ConversionResult(
        srt_path=srt_path,
        json_path=json_path,
        logs=logs,
        lyric_line_count=len(lyric_lines),
        segment_count=segment_count,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="stable-ts forced alignment로 음악 파일과 가사 TXT를 줄 단위 SRT로 변환합니다."
    )
    parser.add_argument("--audio", required=True, type=Path, help="입력 음악 파일 경로(mp3/wav/flac/m4a)")
    parser.add_argument("--lyrics", required=True, type=Path, help="UTF-8 또는 UTF-8 BOM 가사 TXT 경로")
    parser.add_argument("--output", required=True, type=Path, help="생성할 SRT 파일 경로")
    parser.add_argument("--language", default="ko", help="가사 언어 코드(기본값: ko)")
    parser.add_argument("--model", default="large-v3", choices=MODEL_CHOICES, help="Whisper 모델")
    parser.add_argument("--demucs", action="store_true", help="Demucs 보컬 분리 사용")
    parser.add_argument("--vad", action="store_true", help="VAD 기반 무음 억제 사용")
    parser.add_argument("--json-output", type=Path, help="정렬 결과 JSON 저장 경로")
    parser.add_argument("--device", default="auto", choices=DEVICE_CHOICES, help="실행 장치")
    parser.add_argument(
        "--no-auto-model-adjust",
        action="store_true",
        help="VRAM/CPU 상태에 따른 large-v3 자동 하향 조정을 끕니다.",
    )
    return parser


def print_logs(lines: Iterable[str]) -> None:
    for line in lines:
        print(line)


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        parser.print_help()
        return 2

    args = parser.parse_args(argv)
    try:
        result = align_lyrics_to_srt(
            audio=args.audio,
            lyrics=args.lyrics,
            output=args.output,
            language=args.language,
            model_name=args.model,
            use_demucs=args.demucs,
            use_vad=args.vad,
            json_output=args.json_output,
            device=args.device,
            auto_adjust_model=not args.no_auto_model_adjust,
        )
    except AlignmentError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1
    except ModuleNotFoundError as exc:
        print(
            "오류: 필요한 Python 패키지가 설치되어 있지 않습니다. "
            "install_windows.bat을 먼저 실행한 뒤 다시 시도하세요.",
            file=sys.stderr,
        )
        print(f"누락된 모듈: {exc.name}", file=sys.stderr)
        return 1
    except Exception as exc:  # keep CLI user-facing without hiding the failure type
        print(f"오류: 변환 중 예기치 않은 문제가 발생했습니다: {exc}", file=sys.stderr)
        return 1

    print_logs(result.logs)
    print(f"SRT: {result.srt_path}")
    print(f"JSON: {result.json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
