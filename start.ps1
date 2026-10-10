[CmdletBinding()]
param([Alias('SkipBrowser')][switch]$NoBrowser)

$ErrorActionPreference = 'Stop'
$ProjectRoot = $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$ViteEntry = Join-Path $ProjectRoot 'node_modules\vite\bin\vite.js'
$RuntimeRoot = Join-Path $ProjectRoot '.runtime'
$StatePath = Join-Path $RuntimeRoot 'processes.json'
$BackendUrl = 'http://127.0.0.1:8765'
$FrontendUrl = 'http://127.0.0.1:5173'

function Wait-Ready {
    param([string]$Url, [System.Diagnostics.Process]$Process, [int]$Seconds)
    $Deadline = (Get-Date).AddSeconds($Seconds)
    do {
        $Process.Refresh()
        if ($Process.HasExited) { throw "A local service exited with code $($Process.ExitCode). See the logs in $RuntimeRoot." }
        try {
            $Response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
            if ($Response.StatusCode -eq 200) { return }
        } catch { }
        Start-Sleep -Milliseconds 400
    } while ((Get-Date) -lt $Deadline)
    throw "The service did not become ready at $Url. See the logs in $RuntimeRoot."
}

function Test-PortAvailable {
    param([int]$Port)
    $Probe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
    try { $Probe.Start() } catch { throw "Local port $Port is already in use. If Kamayan is running, open $FrontendUrl. Otherwise close the application using that port and retry." }
    finally { $Probe.Stop() }
}

if (-not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) { throw 'Python dependencies are missing. Run .\setup.ps1 first.' }
if (-not (Test-Path -LiteralPath $ViteEntry -PathType Leaf)) { throw 'Frontend dependencies are missing. Run .\setup.ps1 first.' }
$NodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
if (-not $NodeCommand) { throw 'Node.js is missing. Install Node.js 20 or later.' }
Test-PortAvailable 8765
Test-PortAvailable 5173
New-Item -ItemType Directory -Path $RuntimeRoot -Force | Out-Null
$BackendProcess = $null
$FrontendProcess = $null
try {
    Write-Host 'Starting local ASL recognition...'
    $BackendProcess = Start-Process -FilePath $VenvPython -ArgumentList @('-m', 'uvicorn', 'backend.app:app', '--host', '127.0.0.1', '--port', '8765') -WorkingDirectory $ProjectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $RuntimeRoot 'backend.stdout.log') -RedirectStandardError (Join-Path $RuntimeRoot 'backend.stderr.log') -PassThru
    Wait-Ready "$BackendUrl/health" $BackendProcess 60
    $ModelStatus = Invoke-RestMethod -Uri "$BackendUrl/model-status" -TimeoutSec 5
    if (-not $ModelStatus.ready) { throw "The local model is unavailable: $($ModelStatus.error). Run .\setup.ps1 and inspect the required research assets." }
    Write-Host "Loaded $($ModelStatus.model) on $($ModelStatus.device)."
    Write-Host 'Starting the studio...'
    $FrontendProcess = Start-Process -FilePath $NodeCommand.Source -ArgumentList @(('"' + $ViteEntry + '"'), '--host', '127.0.0.1', '--port', '5173', '--strictPort') -WorkingDirectory $ProjectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $RuntimeRoot 'frontend.stdout.log') -RedirectStandardError (Join-Path $RuntimeRoot 'frontend.stderr.log') -PassThru
    Wait-Ready $FrontendUrl $FrontendProcess 30
    [ordered]@{ backend = $BackendProcess.Id; frontend = $FrontendProcess.Id; root = $ProjectRoot; started = (Get-Date).ToString('o') } | ConvertTo-Json | Set-Content -LiteralPath $StatePath -Encoding UTF8
    Write-Host "Kamayan is ready: $FrontendUrl" -ForegroundColor Green
    Write-Host "Local process IDs: backend $($BackendProcess.Id), studio $($FrontendProcess.Id). Logs: $RuntimeRoot"
    Write-Host 'To close this launch, use the process IDs above in Stop-Process -Id <id1>,<id2>.'
    if (-not $NoBrowser) { Start-Process $FrontendUrl }
} catch {
    foreach ($OwnedProcess in @($FrontendProcess, $BackendProcess)) {
        if ($OwnedProcess) {
            $OwnedProcess.Refresh()
            if (-not $OwnedProcess.HasExited) { Stop-Process -Id $OwnedProcess.Id -ErrorAction SilentlyContinue }
        }
    }
    throw
}
