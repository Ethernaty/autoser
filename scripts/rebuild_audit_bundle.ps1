$ErrorActionPreference = 'Stop'

$root = Get-Location
$bundle = Join-Path $root 'audit_bundle'
$zipPath = Join-Path $root 'audit_bundle.zip'

if (Test-Path $bundle) {
  Remove-Item -Recurse -Force $bundle
}
New-Item -ItemType Directory -Path $bundle | Out-Null
New-Item -ItemType Directory -Path (Join-Path $bundle 'backend') | Out-Null
New-Item -ItemType Directory -Path (Join-Path $bundle 'frontend') | Out-Null

$excludeDirs = @('.venv','venv','node_modules','.next','dist','build','coverage','__pycache__','.pytest_cache')

function Ensure-Dir([string]$path) {
  if (-not (Test-Path $path)) { New-Item -ItemType Directory -Path $path | Out-Null }
}

function Copy-IfExists([string]$src, [string]$dst) {
  if (Test-Path $src) {
    Ensure-Dir (Split-Path -Parent $dst)
    Copy-Item -Force $src $dst
  }
}

# Copy backend/app
$backendSrc = Join-Path $root 'backend\app'
$backendDst = Join-Path $bundle 'backend\app'
if (Test-Path $backendSrc) {
  $xd = @()
  foreach ($d in $excludeDirs) { $xd += '/XD'; $xd += $d }
  robocopy $backendSrc $backendDst /E /NFL /NDL /NJH /NJS /NC /NS @xd | Out-Null
}

# Backend configs
Copy-IfExists (Join-Path $root 'backend\requirements.txt') (Join-Path $bundle 'backend\requirements.txt')
Copy-IfExists (Join-Path $root 'backend\alembic.ini') (Join-Path $bundle 'backend\alembic.ini')
Copy-IfExists (Join-Path $root 'backend\docker-compose.yml') (Join-Path $bundle 'backend\docker-compose.yml')
Copy-IfExists (Join-Path $root 'backend\.env.example') (Join-Path $bundle 'backend\.env.example')
Copy-IfExists (Join-Path $root 'backend\app\main.py') (Join-Path $bundle 'backend\app\main.py')

# Copy frontend/src
$frontendSrc = Join-Path $root 'frontend\src'
$frontendDst = Join-Path $bundle 'frontend\src'
if (Test-Path $frontendSrc) {
  $xd = @()
  foreach ($d in $excludeDirs) { $xd += '/XD'; $xd += $d }
  robocopy $frontendSrc $frontendDst /E /NFL /NDL /NJH /NJS /NC /NS @xd | Out-Null
}

# Frontend configs
Copy-IfExists (Join-Path $root 'frontend\package.json') (Join-Path $bundle 'frontend\package.json')
Copy-IfExists (Join-Path $root 'frontend\tsconfig.json') (Join-Path $bundle 'frontend\tsconfig.json')
Copy-IfExists (Join-Path $root 'frontend\next.config.js') (Join-Path $bundle 'frontend\next.config.js')
Copy-IfExists (Join-Path $root 'frontend\postcss.config.js') (Join-Path $bundle 'frontend\postcss.config.js')
Copy-IfExists (Join-Path $root 'frontend\tailwind.config.js') (Join-Path $bundle 'frontend\tailwind.config.js')

# Remove any excluded dirs that slipped in
Get-ChildItem -Path $bundle -Recurse -Directory | Where-Object { $excludeDirs -contains $_.Name } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Zip (overwrite)
if (Test-Path $zipPath) { Remove-Item -Force $zipPath }
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($bundle, $zipPath, [System.IO.Compression.CompressionLevel]::Optimal, $false)

$fileCount = (Get-ChildItem -Path $bundle -Recurse -File | Measure-Object).Count
$zipInfo = Get-Item $zipPath
$sizeMB = [math]::Round($zipInfo.Length / 1MB, 2)

"FILES=$fileCount"
"ZIP_SIZE_MB=$sizeMB"
