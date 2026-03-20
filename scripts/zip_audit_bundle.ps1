$ErrorActionPreference = 'Stop'

$root = Get-Location
$bundle = Join-Path $root 'audit_bundle'
$zipPath = Join-Path $root 'audit_bundle.zip'

if (-not (Test-Path $bundle)) {
  throw "audit_bundle folder not found at $bundle"
}

if (Test-Path $zipPath) {
  Remove-Item -Force $zipPath
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($bundle, $zipPath, [System.IO.Compression.CompressionLevel]::Optimal, $false)

$fileCount = (Get-ChildItem -Path $bundle -Recurse -File | Measure-Object).Count
$zipInfo = Get-Item $zipPath
$sizeMB = [math]::Round($zipInfo.Length / 1MB, 2)

"FILES=$fileCount"
"ZIP_SIZE_MB=$sizeMB"
"ZIP_PATH=$zipPath"
