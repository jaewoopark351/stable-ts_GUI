@echo off
chcp 65001 >nul
setlocal

if not exist "%~dp0.venv\Scripts\python.exe" (
    echo .venv를 찾을 수 없습니다. install_windows.bat을 먼저 실행하세요.
    exit /b 1
)

echo 예제 입력 경로를 실제 파일로 바꾼 뒤 사용하세요.
"%~dp0.venv\Scripts\python.exe" "%~dp0lyrics_to_srt.py" ^
  --audio "%~dp0input\song.mp3" ^
  --lyrics "%~dp0input\lyrics.txt" ^
  --output "%~dp0output\song.srt" ^
  --language ko ^
  --model large-v3 ^
  --device auto ^
  --demucs ^
  --vad
