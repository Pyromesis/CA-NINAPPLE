<#
.SYNOPSIS
  Compila el IPA de un juego de Switch desde Windows.

.EXAMPLE
  .\build.ps1 -Game "C:\Juegos\BALLxPIT"

.EXAMPLE
  .\build.ps1 -Game "C:\Juegos\BALLxPIT" -SplitData -Entitlements

.NOTES
  Envuelve win\build_ipa_windows.py: pone la consola en UTF-8 (sin esto los
  simbolos del progreso rompen la salida con UnicodeEncodeError en una consola
  cp1252) y comprueba lo minimo antes de empezar. Cualquier opcion que no este
  aqui se pasa tal cual al driver.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Game,

    [Parameter(Position = 1)]
    [string]$Keys,

    [string]$Out,

    [switch]$SplitData,
    [switch]$Entitlements,
    [switch]$Check,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Extra
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$driver = Join-Path $root 'win\build_ipa_windows.py'

if (-not (Test-Path -LiteralPath $driver)) {
    throw "No encuentro $driver. Ejecuta este script desde la raiz del repositorio CA-NINAPPLE."
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw 'No hay python en el PATH. Instala Python 3.10 o posterior desde python.org y marca "Add python.exe to PATH".'
}

if (-not (Test-Path -LiteralPath $Game)) {
    throw "No existe la carpeta del juego: $Game"
}
if (-not $Keys) { $Keys = Join-Path $Game 'prod.keys' }
if (-not (Test-Path -LiteralPath $Keys)) {
    throw "No encuentro las llaves en $Keys. Pasa -Keys con la ruta de tu prod.keys."
}

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

if ($Check) {
    & python (Join-Path $root 'win\doctor.py')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$argv = @($driver, $Game, '-k', $Keys)
if ($Out) { $argv += @('-o', $Out) }
if ($SplitData) { $argv += '--split-data' }
if ($Entitlements) { $argv += '--entitlements' }
if ($Extra) { $argv += $Extra }

Write-Host "CA-NINAPPLE: $Game" -ForegroundColor Magenta
& python @argv
exit $LASTEXITCODE
