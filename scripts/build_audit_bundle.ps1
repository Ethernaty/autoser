$ErrorActionPreference = 'Stop'

$root = Get-Location
$bundle = Join-Path $root 'audit_bundle'

if (Test-Path $bundle) {
  Remove-Item -Recurse -Force $bundle
}
New-Item -ItemType Directory -Path $bundle | Out-Null

function Ensure-Dir([string]$path) {
  if (-not (Test-Path $path)) { New-Item -ItemType Directory -Path $path | Out-Null }
}

function Copy-IfExists([string]$src, [string]$dst) {
  if (Test-Path $src) {
    $dstDir = Split-Path -Parent $dst
    Ensure-Dir $dstDir
    Copy-Item -Force $src $dst
  }
}

function Copy-Globs([string]$base, [string[]]$patterns, [string]$destRoot) {
  foreach ($pattern in $patterns) {
    $items = Get-ChildItem -Path $base -Recurse -File -Include $pattern -ErrorAction SilentlyContinue
    foreach ($item in $items) {
      $rel = $item.FullName.Substring($base.Length).TrimStart('\','/')
      $dest = Join-Path $destRoot $rel
      Ensure-Dir (Split-Path -Parent $dest)
      Copy-Item -Force $item.FullName $dest
    }
  }
}

# Backend files
$backendBase = Join-Path $root 'backend'
$backendDest = Join-Path $bundle 'backend'

if (Test-Path $backendBase) {
  Copy-Globs -base $backendBase -patterns @('*.py','*.sql','*.yaml','*.yml','*.json') -destRoot $backendDest

  Copy-IfExists (Join-Path $backendBase 'requirements.txt') (Join-Path $backendDest 'requirements.txt')
  Copy-IfExists (Join-Path $backendBase 'pyproject.toml') (Join-Path $backendDest 'pyproject.toml')
  Copy-IfExists (Join-Path $backendBase 'Dockerfile') (Join-Path $backendDest 'Dockerfile')
  Copy-IfExists (Join-Path $backendBase 'docker-compose.yml') (Join-Path $backendDest 'docker-compose.yml')
  Copy-IfExists (Join-Path $backendBase 'alembic.ini') (Join-Path $backendDest 'alembic.ini')
  Copy-IfExists (Join-Path $backendBase '.env.example') (Join-Path $backendDest '.env.example')
  Copy-IfExists (Join-Path $backendBase 'app\main.py') (Join-Path $backendDest 'app\main.py')
}

# Frontend files
$frontendBase = Join-Path $root 'frontend'
$frontendDest = Join-Path $bundle 'frontend'

if (Test-Path $frontendBase) {
  Copy-Globs -base $frontendBase -patterns @('*.ts','*.tsx','*.js','*.json') -destRoot $frontendDest

  Copy-IfExists (Join-Path $frontendBase 'package.json') (Join-Path $frontendDest 'package.json')
  Copy-IfExists (Join-Path $frontendBase 'tsconfig.json') (Join-Path $frontendDest 'tsconfig.json')
  Copy-IfExists (Join-Path $frontendBase 'next.config.js') (Join-Path $frontendDest 'next.config.js')
  Copy-IfExists (Join-Path $frontendBase 'postcss.config.js') (Join-Path $frontendDest 'postcss.config.js')
  Copy-IfExists (Join-Path $frontendBase 'tailwind.config.js') (Join-Path $frontendDest 'tailwind.config.js')
  Copy-IfExists (Join-Path $frontendBase '.env.example') (Join-Path $frontendDest '.env.example')
}

# DevOps / Infrastructure
Copy-IfExists (Join-Path $root 'docker-compose.yml') (Join-Path $bundle 'docker-compose.yml')
Copy-IfExists (Join-Path $root 'Makefile') (Join-Path $bundle 'Makefile')
Copy-IfExists (Join-Path $root 'scripts') (Join-Path $bundle 'scripts')
Copy-IfExists (Join-Path $root '.github\workflows') (Join-Path $bundle '.github\workflows')

# Remove excluded patterns if they slipped in
$excludeNames = @('venv','__pycache__','.pytest_cache','node_modules','.next','dist','build','coverage')
Get-ChildItem -Path $bundle -Recurse -Directory | Where-Object { $excludeNames -contains $_.Name } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $bundle -Recurse -File | Where-Object { $_.Extension -in @('.log','.sqlite') } | Remove-Item -Force -ErrorAction SilentlyContinue

# Create zip
$zipPath = Join-Path $root 'audit_bundle.zip'
if (Test-Path $zipPath) { Remove-Item -Force $zipPath }
Compress-Archive -Path (Join-Path $bundle '*') -DestinationPath $zipPath

# Report size and file count
$fileCount = (Get-ChildItem -Path $bundle -Recurse -File | Measure-Object).Count
$zipInfo = Get-Item $zipPath
$sizeMB = [math]::Round($zipInfo.Length / 1MB, 2)

"FILES=$fileCount"
"ZIP_SIZE_MB=$sizeMB"
"ZIP_PATH=$zipPath"
