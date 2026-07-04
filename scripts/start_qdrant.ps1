# Start Qdrant locally without Docker
# Downloads Qdrant Windows binary if not present and starts it

$QDRANT_DIR = "$env:USERPROFILE\qdrant"
$QDRANT_EXE = "$QDRANT_DIR\qdrant.exe"
$QDRANT_VERSION = "v1.13.6"
$QDRANT_URL = "https://github.com/qdrant/qdrant/releases/download/$QDRANT_VERSION/qdrant-x86_64-pc-windows-msvc.zip"

# Download Qdrant if not present
if (-not (Test-Path $QDRANT_EXE)) {
    Write-Host "Downloading Qdrant $QDRANT_VERSION..." -ForegroundColor Yellow
    $ZIP = "$env:TEMP\qdrant.zip"
    Invoke-WebRequest -Uri $QDRANT_URL -OutFile $ZIP
    Expand-Archive -Path $ZIP -DestinationPath $QDRANT_DIR -Force
    Remove-Item $ZIP
    Write-Host "Downloaded Qdrant to $QDRANT_DIR" -ForegroundColor Green
}

# Check if already running
$running = Get-Process -Name "qdrant" -ErrorAction SilentlyContinue
if ($running) {
    Write-Host "Qdrant is already running (PID: $($running.Id))" -ForegroundColor Green
    exit
}

# Start Qdrant
Write-Host "Starting Qdrant..." -ForegroundColor Yellow
$LOG = "$env:TEMP\qdrant.log"
Start-Process -FilePath $QDRANT_EXE -ArgumentList "--storage-dir $QDRANT_DIR\storage" -NoNewWindow -RedirectStandardOutput $LOG -RedirectStandardError "${LOG}.err"
Write-Host "Qdrant started. Waiting for it to be ready..." -ForegroundColor Yellow

# Wait for it to be ready
$timeout = 30
$ready = $false
for ($i = 0; $i -lt $timeout; $i++) {
    Start-Sleep -Seconds 1
    try {
        $resp = Invoke-RestMethod -Uri "http://localhost:6333/healthz" -ErrorAction SilentlyContinue
        if ($resp -eq "healthz check passed") {
            $ready = $true
            break
        }
    } catch {}
}
if ($ready) {
    Write-Host "Qdrant is ready at http://localhost:6333" -ForegroundColor Green
} else {
    Write-Host "Qdrant may not be ready. Check $LOG for details." -ForegroundColor Red
}

Write-Host "`nTo start the API: uvicorn app.main:app --reload" -ForegroundColor Cyan
