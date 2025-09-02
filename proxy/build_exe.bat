@echo off
echo Installing PyInstaller if not already installed...
pip install pyinstaller

echo Building executable from proxy.py...
pyinstaller --onefile proxy.py

echo Done! Executable should be in the dist folder.
pause