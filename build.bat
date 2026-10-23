@echo off
REM 打包 CharactersBirthday 为多文件 exe，并把 data 目录放到 exe 同级
cd /d "%~dp0"

python -m PyInstaller --noconfirm --clean --onedir --windowed --name CharactersBirthday main.py
if errorlevel 1 exit /b 1

REM 将 data 目录复制到 exe 同级（dist\CharactersBirthday\）
xcopy /E /I /Y data "dist\CharactersBirthday\data" >nul

echo.
echo 打包完成：dist\CharactersBirthday\
echo 整个 dist\CharactersBirthday 文件夹可整体复制到任意位置运行。
pause
