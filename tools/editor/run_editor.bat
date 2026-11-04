@echo off
rem Terra Universalis editor: double-click to start, then use the browser tab that opens.
cd /d "%~dp0\..\.."
python -I tools\editor\server.py %*
pause
