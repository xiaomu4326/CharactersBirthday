# CharactersBirthday —— 带签名的 Android 构建脚本
#
# 为什么需要它：`flet build` 每次重新渲染 android 工程时，签名配置来自环境变量；
# 少了这几个变量就会退回 debug 签名，装到「已安装正式签名版本」的手机上会报
# INSTALL_FAILED_UPDATE_INCOMPATIBLE。
#
# 用法（在仓库任意位置执行）：
#   pwsh -File apk/build_apk_signed.ps1
#   pwsh -File apk/build_apk_signed.ps1 -KeystoreInfo "D:\keys\charactersbirthday-keystore-info.txt"
#   pwsh -File apk/build_apk_signed.ps1 -DryRun          # 只校验口令能否读出，不构建
#
# 说明文件格式：由 keytool 生成时写入的 txt，含一行「store 口令：xxxx」。
# 口令不进仓库：本脚本只保存说明文件的路径（通过参数或环境变量传入）。

param(
    # keystore 说明文件路径；也可用环境变量 CHARACTERSBIRTHDAY_KEYSTORE_INFO 指定
    [string]$KeystoreInfo = $env:CHARACTERSBIRTHDAY_KEYSTORE_INFO,

    # keystore 路径；留空则取说明文件同目录下的 charactersbirthday-release.jks
    [string]$Keystore,

    # 只做校验，不真正构建
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot      # apk/ 的上一级 = 仓库根

if (-not $KeystoreInfo) {
    Write-Host "缺少 keystore 说明文件路径。" -ForegroundColor Yellow
    Write-Host '请用 -KeystoreInfo "<路径>\charactersbirthday-keystore-info.txt" 指定，'
    Write-Host '或设置环境变量 CHARACTERSBIRTHDAY_KEYSTORE_INFO。'
    exit 2
}
if (-not (Test-Path -LiteralPath $KeystoreInfo)) {
    Write-Host "说明文件不存在：$KeystoreInfo" -ForegroundColor Red
    exit 2
}

# 从说明文件里读出口令与 alias（口令只在内存里，不落盘）
$info = Get-Content -LiteralPath $KeystoreInfo -Raw -Encoding UTF8
$storePass = ([regex]::Match($info, 'store 口令：(.+)')).Groups[1].Value.Trim()
$alias = ([regex]::Match($info, 'alias\s*：(.+)')).Groups[1].Value.Trim()
$ksFromInfo = ([regex]::Match($info, 'keystore\s*：(.+)')).Groups[1].Value.Trim()

if (-not $Keystore) {
    $Keystore = if ($ksFromInfo) { $ksFromInfo } else {
        Join-Path (Split-Path -Parent $KeystoreInfo) 'charactersbirthday-release.jks'
    }
}
if (-not $storePass) { Write-Host "说明文件里没读到「store 口令：」。" -ForegroundColor Red; exit 2 }
if (-not $alias) { $alias = 'charactersbirthday' }
if (-not (Test-Path -LiteralPath $Keystore)) {
    Write-Host "keystore 不存在：$Keystore" -ForegroundColor Red
    exit 2
}

$env:FLET_ANDROID_SIGNING_KEY_STORE = $Keystore
$env:FLET_ANDROID_SIGNING_KEY_ALIAS = $alias
$env:FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD = $storePass
$env:FLET_ANDROID_SIGNING_KEY_PASSWORD = $storePass

Write-Host "keystore : $Keystore"
Write-Host "alias    : $alias"
Write-Host "口令     : 已读取（长度 $($storePass.Length)，不回显）"

if ($DryRun) {
    Write-Host "DryRun：环境变量已就绪，未执行构建。" -ForegroundColor Green
    exit 0
}

# 构建环境：Flutter 自带的 Kotlin 解析不了 JDK 25，必须显式指定 JDK 17；
# TEMP 指到仓库内，避开系统临时目录的权限问题。
$jdk17 = @(
    'C:\Users\Administrator\java\17.0.13+11',
    'C:\Program Files\Eclipse Adoptium\jdk-17.0.21.9-hotspot'
) | Where-Object { Test-Path (Join-Path $_ 'bin\java.exe') } | Select-Object -First 1

if (-not $jdk17) {
    Write-Host "没找到 JDK 17，请用 flutter config --jdk-dir 指定后重试。" -ForegroundColor Red
    exit 2
}

$tmp = Join-Path $repo '.buildtmp'
New-Item -ItemType Directory -Path $tmp -Force | Out-Null
$env:TEMP = $tmp
$env:TMP = $tmp
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$gp = Join-Path $env:USERPROFILE '.gradle\gradle.properties'
$hasGp = Test-Path -LiteralPath $gp
if ($hasGp) { $gpBackup = [System.IO.File]::ReadAllBytes($gp) }

try {
    if ($hasGp) {
        # 用户级配置里可能把 JDK 固定在 25，临时改成本机的 17，构建后还原
        $text = [System.IO.File]::ReadAllText($gp)
        $replaced = $text -replace '(?m)^org\.gradle\.java\.home=.*$',
            ('org.gradle.java.home=' + $jdk17.Replace('\', '/'))
        [System.IO.File]::WriteAllText($gp, $replaced, (New-Object System.Text.UTF8Encoding($false)))
    }

    # 模板路径相对 pyproject.toml，必须在 apk/ 目录内构建
    Push-Location (Join-Path $repo 'apk')
    try {
        & flet build apk . --arch arm64-v8a --yes --skip-flutter-doctor
        $code = $LASTEXITCODE
    } finally {
        Pop-Location
    }
} finally {
    if ($hasGp) { [System.IO.File]::WriteAllBytes($gp, $gpBackup) }
}

if ($code -ne 0) { Write-Host "构建失败（exit=$code）" -ForegroundColor Red; exit $code }

$apk = Join-Path $repo 'apk\build\apk\CharactersBirthday.apk'
$signer = Join-Path $env:LOCALAPPDATA 'Android\Sdk\build-tools\34.0.0\apksigner.bat'
if (-not (Test-Path $signer)) { $signer = 'C:\Users\Administrator\Android\sdk\build-tools\34.0.0\apksigner.bat' }
if (Test-Path $apk) {
    Write-Host ("产物: {0} ({1:N1} MB)" -f $apk, ((Get-Item $apk).Length / 1MB))
    if (Test-Path $signer) {
        & $signer verify --print-certs $apk 2>&1 |
            Select-String -Pattern 'certificate DN' |
            ForEach-Object { "签名: " + ($_.Line.Trim() -replace 'Signer #1 certificate DN: ', '') }
    }
}
