# Agent Rules

- Work only inside `C:\Vtuber_Souorce_Code\stable-ts-main`.
- Do not modify parent folders or sibling projects.
- Keep the original stable-ts source, license, and credits intact unless the user explicitly approves a minimal source change.
- Use only the project virtual environment at `.venv`.
- Do not use global `python`, global `pip`, or system Python for installs, tests, or runs.
- Use `.\.venv\Scripts\python.exe` for every Python command after the virtual environment exists.
- If `.venv` does not exist, create it with `py -3.11 -m venv .venv`.
- Do not commit or permanently store user-uploaded audio or lyrics files.
- Treat generated SRT, alignment JSON, model caches, and temporary files as local artifacts.
