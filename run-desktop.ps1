#requires -version 5.1
<#
.SYNOPSIS
    Chay app RetroHub (files/app.py) tren may desktop, khong can may handheld.

.DESCRIPTION
    App duoc viet cho TrimUI: PySDL2 dua vao DLL SDL2 co san trong firmware, du
    lieu nam duoi SDCARD_PATH. Desktop khong co ca hai, nen script nay tao:

      - venv rieng + pysdl2-dll  -> DLL SDL2/SDL2_ttf/SDL2_image cho Windows
      - mot thu muc "the SD" gia  -> Roms/Themes/Imgs/Emus ma app can

    Khong sua gi trong files/: moi thu chi qua bien moi truong.

.PARAMETER SdCardDir
    Thu muc dong vai the SD. Mac dinh .sdcard-desktop canh script.

.PARAMETER VenvDir
    Thu muc venv. Mac dinh .venv-desktop canh script.

.PARAMETER PythonExe
    Python nen dung de tao venv. Mac dinh: python trong PATH, roi py -3.

.PARAMETER UpgradePackages
    Cai lai/cap nhat pysdl2-dll (va yt-dlp) ke ca khi da co.

.PARAMETER WithYouTube
    Cai them yt-dlp (chi can cho tab YouTube).

.PARAMETER RecreateVenv
    Xoa venv cu roi tao lai.

.PARAMETER NoLaunch
    Chuan bi xong thi dung, khong mo app (dung de kiem tra moi truong).

.PARAMETER WindowSize
    Kich thuoc cua so, dang WxH (vi du 1280x720). Mac dinh 70% man hinh.

.PARAMETER FullScreen
    Chay toan man hinh nhu tren may cam tay, khong co thanh tieu de.

.EXAMPLE
    .\run-desktop.ps1

.EXAMPLE
    .\run-desktop.ps1 -SdCardDir D:\rhsd -WithYouTube
#>
[CmdletBinding()]
param(
    [string]$SdCardDir = (Join-Path $PSScriptRoot ".sdcard-desktop"),
    [string]$VenvDir = (Join-Path $PSScriptRoot ".venv-desktop"),
    [string]$PythonExe,
    [switch]$WithYouTube,
    [switch]$UpgradePackages,
    [switch]$RecreateVenv,
    [switch]$NoLaunch,
    [string]$WindowSize,
    [switch]$FullScreen
)

$ErrorActionPreference = "Stop"

$AppDir = Join-Path $PSScriptRoot "files"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

function Write-Step($Message) { Write-Host "[run-desktop] $Message" }

function Get-BasePython {
    if ($PythonExe) {
        if (-not (Test-Path -LiteralPath $PythonExe)) {
            throw "Khong thay Python tai '$PythonExe'."
        }
        return @($PythonExe)
    }
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { return @($cmd.Source) }
    $cmd = Get-Command py -ErrorAction SilentlyContinue
    if ($cmd) { return @($cmd.Source, "-3") }
    throw "Khong tim thay Python. Cai Python 3.9+ hoac truyen -PythonExe <duong dan>."
}

function Test-PythonModule($Python, $Module) {
    & $Python -c "import $Module" 2>$null
    return ($LASTEXITCODE -eq 0)
}

function Invoke-Python($Python, [string[]]$Arguments) {
    $head = @($Python | Select-Object -First 1)
    $tail = @($Python | Select-Object -Skip 1)
    & $head[0] ($tail + $Arguments)
    if ($LASTEXITCODE -ne 0) {
        throw "Lenh python that bai (exit $LASTEXITCODE): $($Arguments -join ' ')"
    }
}

if (-not (Test-Path -LiteralPath (Join-Path $AppDir "app.py"))) {
    throw "Khong thay files\app.py - chay script nay tu thu muc goc cua repo."
}

# ---------------------------------------------------------------------------
# 1. venv + pysdl2-dll
# ---------------------------------------------------------------------------
if ($RecreateVenv -and (Test-Path -LiteralPath $VenvDir)) {
    Write-Step "Xoa venv cu: $VenvDir"
    Remove-Item -LiteralPath $VenvDir -Recurse -Force
}

if (-not (Test-Path -LiteralPath $VenvPython)) {
    $basePython = Get-BasePython
    $head = @($basePython | Select-Object -First 1)
    $tail = @($basePython | Select-Object -Skip 1)
    $version = (& $head[0] ($tail + @("-c", "import sys;print('%d.%d' % sys.version_info[:2])"))).Trim()
    if ([version]$version -lt [version]"3.9") {
        throw "Can Python 3.9 tro len, dang co $version."
    }
    Write-Step "Tao venv ($version): $VenvDir"
    Invoke-Python $basePython @("-m", "venv", $VenvDir)
}

$packages = @("pysdl2-dll")
$modules = @("sdl2dll")
if ($WithYouTube) { $packages += "yt-dlp"; $modules += "yt_dlp" }

# pip chi chay khi thieu thu vien hoac nguoi dung yeu cau cap nhat: moi lan cai
# la mot vong ra mang, ma lan chay thuong ngay sau lan dau tien khong can gi.
$missing = @($modules | Where-Object { -not (Test-PythonModule $VenvPython $_) })
if ($missing.Count -gt 0 -or $UpgradePackages) {
    Write-Step "Cai/cap nhat: $($packages -join ', ')"
    Invoke-Python @($VenvPython) (@("-m", "pip", "install", "--quiet",
        "--disable-pip-version-check", "--upgrade") + $packages)
}

# app.py tu dat PYSDL2_DLL_PATH vao duong dan Linux (/usr/trimui/lib...), ma
# vendor/sdl2/dll.py chi dung pysdl2-dll khi bien nay CHUA duoc dat - nen phai
# tro no vao DLL cua venv truoc khi app khoi dong.
$dllPath = (& $VenvPython -c "import sdl2dll;print(sdl2dll.get_dllpath())").Trim()
if (-not (Test-Path -LiteralPath (Join-Path $dllPath "SDL2.dll"))) {
    throw "pysdl2-dll khong co SDL2.dll trong '$dllPath'."
}

# ---------------------------------------------------------------------------
# 2. "the SD" gia
# ---------------------------------------------------------------------------
foreach ($sub in @("Roms", "Imgs", "Emus", "Themes", "System\etc")) {
    $full = Join-Path $SdCardDir $sub
    if (-not (Test-Path -LiteralPath $full)) {
        New-Item -ItemType Directory -Path $full -Force | Out-Null
    }
}

# ---------------------------------------------------------------------------
# 3. Chay app
# ---------------------------------------------------------------------------
$env:SDCARD_PATH = (Resolve-Path -LiteralPath $SdCardDir).Path
$env:PYSDL2_DLL_PATH = $dllPath
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

# Mac dinh chay trong cua so de co thanh tieu de (minimize / maximize / close).
# May cam tay khong co trinh quan ly cua so nen ben do khong bao gio dat bien
# nay - xem rh/engine.py desktop_window_size().
if ($FullScreen) {
    Remove-Item Env:\RETROHUB_WINDOWED -ErrorAction SilentlyContinue
    Remove-Item Env:\RETROHUB_WINDOW_SIZE -ErrorAction SilentlyContinue
} else {
    $env:RETROHUB_WINDOWED = "1"
    if ($WindowSize) { $env:RETROHUB_WINDOW_SIZE = $WindowSize }
}

Write-Step "SDCARD_PATH      = $env:SDCARD_PATH"
Write-Step "PYSDL2_DLL_PATH  = $env:PYSDL2_DLL_PATH"
Write-Step "Python           = $VenvPython"
if ($FullScreen) {
    Write-Step "Che do           = toan man hinh (giong may cam tay)"
} elseif ($WindowSize) {
    Write-Step "Che do           = cua so $WindowSize"
} else {
    Write-Step "Che do           = cua so 70% man hinh"
}

if ($NoLaunch) {
    Write-Step "NoLaunch: moi truong san sang, khong mo app."
    exit 0
}

Write-Step "Mo RetroHub... (ESC hoac K: quay lai; nut X tren cua so: thoat)"
Push-Location $AppDir
try {
    & $VenvPython app.py
    $exitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

Write-Step "App thoat voi exit code $exitCode"
exit $exitCode