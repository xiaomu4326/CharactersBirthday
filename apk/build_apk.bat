@echo off
REM ============================================================================
REM  CharactersBirthday - Android APK 构建脚本（本机专用）
REM
REM  为什么要这个脚本：
REM  1) 用户级 %USERPROFILE%\.gradle\gradle.properties 里有一行
REM         org.gradle.java.home=D:/Java/jdk-25
REM     （给 Fabric Loom 用的）。Flutter 自带的 Kotlin 2.0.21 解析不了 JDK 25
REM     的版本串，Gradle 会直接抛 java.lang.IllegalArgumentException: 25.0.5.0.2。
REM     项目级 gradle.properties 覆盖不了它，只能用 GRADLE_OPTS 显式指定 JDK 17。
REM  2) 打包中间文件如果落在系统 %TEMP%（常被安全软件/沙箱限制），Python 编译
REM     步骤会 PermissionError。这里把 TEMP 指到项目内的 .buildtmp。
REM
REM  用法：双击本文件，或在本目录执行 build_apk.bat
REM  产物：apk\build\apk\CharactersBirthday.apk
REM
REM  ！！注意：本脚本不带签名，产出的 APK 是 debug 签名。
REM  装到「已安装正式签名版本」的手机上会报 INSTALL_FAILED_UPDATE_INCOMPATIBLE。
REM  要出可覆盖安装的包，请改用同目录的签名脚本：
REM      pwsh -File build_apk_signed.ps1 -KeystoreInfo "<keystore 说明文件.txt>"
REM ============================================================================
setlocal
cd /d "%~dp0"

set "JAVA_DIR=C:\Program Files\Eclipse Adoptium\jdk-17.0.21.9-hotspot"
if not exist "%JAVA_DIR%\bin\java.exe" (
    echo [警告] 没找到 JDK 17：%JAVA_DIR%
    echo        请先运行  flutter config --jdk-dir "你的 JDK 17 路径"
    echo        然后把本脚本里的 JAVA_DIR 改成同一路径。
    pause
    exit /b 1
)

set "GRADLE_OPTS=-Dorg.gradle.java.home=\"%JAVA_DIR%\""
set "TEMP=%~dp0.buildtmp"
set "TMP=%~dp0.buildtmp"
if not exist "%TEMP%" mkdir "%TEMP%"

python -m flet.cli build apk --no-rich-output
if errorlevel 1 (
    echo.
    echo [失败] 构建未完成，看上面的日志。
    pause
    exit /b 1
)

echo.
echo [完成] apk\build\apk\CharactersBirthday.apk
pause
