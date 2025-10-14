param(
    [string]$Prefix = "$env:USERPROFILE/.trif"
)

$source = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Join-Path $source '..'
$toolchain = Join-Path $Prefix 'toolchain'
$bin = Join-Path $Prefix 'bin'

New-Item -ItemType Directory -Force -Path $toolchain | Out-Null
New-Item -ItemType Directory -Force -Path $bin | Out-Null

if (Test-Path $toolchain) {
    Remove-Item -Recurse -Force (Join-Path $toolchain '*')
}
Copy-Item -Recurse -Force (Join-Path $root '*') $toolchain

$wrapper = Join-Path $bin 'trif.ps1'
@"
param([string[]]$Args)
$python = if ($env:PYTHON) { $env:PYTHON } else { 'python' }
& $python -m trif_lang @Args
"@ | Set-Content -Encoding UTF8 $wrapper

Write-Host "Trif installed to $toolchain"
Write-Host "Add $bin to your PATH and invoke via 'trif.ps1 -- help'"
