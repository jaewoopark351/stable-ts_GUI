# Windows용 음악 + 가사 TXT -> SRT 변환

이 저장소의 원본 stable-ts 코드를 직접 수정하지 않고, `app.py`와 `lyrics_to_srt.py`를 통해 음악 파일과 정확한 가사 TXT를 줄 단위 SRT 자막으로 변환합니다. 변환은 새 받아쓰기(`transcribe`)가 아니라 stable-ts의 `model.align(..., original_split=True)` forced alignment를 사용합니다.

## 설치

1. FFmpeg를 설치하고 PATH에 등록합니다.
2. Python 3.11을 설치합니다.
3. 이 폴더에서 `install_windows.bat`을 실행합니다.

설치 스크립트는 `.venv`를 만들고 다음 Python만 사용합니다.

```bat
.\.venv\Scripts\python.exe
```

전역 `python` 또는 전역 `pip`로 실행하지 마세요.

## CUDA 및 PyTorch

`install_windows.bat`은 `nvidia-smi`를 먼저 확인하고, 설치 후 `torch.cuda.is_available()` 결과를 출력합니다. CUDA용 PyTorch가 필요한 경우에는 현재 NVIDIA 드라이버와 Python 3.11에 맞는 PyTorch 설치 명령을 먼저 확인한 뒤 진행하세요. CPU 전용 PyTorch를 실수로 설치하지 않도록 주의하세요.

RTX 5070 Ti에서 GPU를 사용하려면 `.venv` 안의 PyTorch가 CUDA 빌드여야 합니다. 현재 공식 PyTorch 설치 페이지 기준 Windows + pip에서는 CUDA 12.8 빌드를 선택할 수 있습니다.

```bat
.\.venv\Scripts\python.exe -m pip install --upgrade --force-reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
```

설치 후 반드시 확인하세요.

```bat
.\.venv\Scripts\python.exe -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.version.cuda)"
```

`torch.cuda.is_available()`가 `True`가 아니면 GPU를 쓰지 못합니다.

## GUI 실행

```bat
run_gui.bat
```

또는 직접 실행:

```bat
.\.venv\Scripts\python.exe app.py
```

GUI는 기본적으로 `test` 폴더의 최신 음악 파일과 `test\lyrics.txt`를 자동으로 입력합니다. 로컬 파일 탭에서 경로를 확인한 뒤 `변환 시작`을 누르면 `output` 폴더에 SRT와 JSON이 생성됩니다.

기본 모델은 `large-v3`입니다. `VRAM 자동 조정`이 켜져 있으면 CUDA VRAM 여유가 부족할 때 `medium` 또는 `small`로 자동 하향됩니다. CUDA가 잡히지 않는 CPU 환경에서는 `large-v3`가 매우 느릴 수 있어 자동 조정 시 `medium`으로 낮춥니다. RTX 5070 Ti에서 CUDA PyTorch가 정상 설치되어 있고 VRAM 여유가 충분하면 `large-v3`를 그대로 사용합니다.

처음 테스트할 때는 `Demucs`와 `VAD`를 끈 상태로 시작하는 것을 권장합니다. 결과가 나오면 `VAD`를 켜거나 `VRAM 자동 조정`을 끄고 다시 시도하세요. 업로드 탭에서는 파일을 직접 올려서 같은 변환을 실행할 수 있습니다.

## CLI 실행

```bat
.\.venv\Scripts\python.exe lyrics_to_srt.py ^
  --audio "input\song.mp3" ^
  --lyrics "input\lyrics.txt" ^
  --output "output\song.srt" ^
  --language ko ^
  --model large-v3 ^
  --device auto
```

선택 옵션:

- `--model`: `large-v3`, `medium`, `small`
- `--device`: `auto`, `cuda`, `cpu`
- `--demucs`: Demucs 보컬 분리 사용
- `--vad`: VAD 사용
- `--json-output`: 정렬 결과 JSON 경로 지정
- `--no-auto-model-adjust`: VRAM/CPU 상태에 따른 모델 자동 하향 조정 끄기

## 가사 TXT 작성 규칙

- UTF-8 또는 UTF-8 BOM TXT를 사용합니다.
- 빈 줄은 제거됩니다.
- 각 줄의 앞뒤 공백은 제거됩니다.
- 한 줄이 하나의 SRT 자막 단위가 됩니다.
- `[Verse]`, `[Chorus]` 같은 문구는 자동 삭제하지 않습니다.
- 반복 후렴은 실제 노래 순서대로 직접 적어야 합니다.
- 가사를 자동 수정하거나 번역하지 않습니다.

가사와 음원의 순서가 다르거나 반복 구간이 누락되면 정렬 정확도가 낮아질 수 있습니다.

## 출력

기본 출력:

- `output\song.srt`
- `output\song_alignment.json`

출력 폴더가 없으면 자동 생성됩니다. 한글 경로와 한글 파일명은 `pathlib.Path` 기반으로 처리합니다.

## 문제 해결

FFmpeg 오류:

```text
FFmpeg를 찾을 수 없습니다. FFmpeg를 설치하고 PATH에 등록한 뒤 다시 실행하세요.
```

Demucs 오류:

```text
Demucs가 설치되어 있지 않습니다.
```

보컬 분리가 필요하면 다음 명령을 `.venv` Python으로 실행하세요.

```bat
.\.venv\Scripts\python.exe -m pip install demucs
```

필수 패키지 import 오류가 나면 `install_windows.bat`을 다시 실행하세요.

## 검증 명령

```bat
.\.venv\Scripts\python.exe -c "import sys; print(sys.executable)"
.\.venv\Scripts\python.exe -c "import stable_whisper; print('stable-ts import OK')"
.\.venv\Scripts\python.exe -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.version.cuda)"
.\.venv\Scripts\python.exe lyrics_to_srt.py --help
.\.venv\Scripts\python.exe -m pip check
```
