@echo off
set "PYTHON_EXE=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
where python >nul 2>nul && set "PYTHON_EXE=python"
"%PYTHON_EXE%" nber_digest.py --config config.json --refresh --send

