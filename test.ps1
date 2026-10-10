[CmdletBinding()]
param([switch]$SkipFrontend)

$ErrorActionPreference = 'Stop'
$ProjectRoot = $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'

function Invoke-Checked {
    param([string]$Command, [string[]]$Arguments)
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Verification failed with exit code $LASTEXITCODE`: $Command" }
}

if (-not (Test-Path -LiteralPath $VenvPython)) { throw 'Run .\setup.ps1 before testing.' }
foreach ($SampleName in @('sentence_manifest.json', 'how2sign-sentence.mp4')) {
    if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot "research\samples\$SampleName") -PathType Leaf)) { throw "Real-video test asset is missing: $SampleName. For authorized private evaluation, run .\setup.ps1 -EvaluationSamples first." }
}
Push-Location $ProjectRoot
try {
    Write-Host 'Checking static English/Filipino captions and local speech. No AI models will load.'
    Invoke-Checked $VenvPython @('-m', 'pytest', 'backend/test_demo.py', 'backend/test_speech.py', '-v')
    if (-not $SkipFrontend) {
        $NpmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
        if (-not $NpmCommand) { throw 'Node.js/npm is missing.' }
        Write-Host 'Checking transcript behavior and the production frontend build...'
        Invoke-Checked $NpmCommand.Source @('test')
        Invoke-Checked $NpmCommand.Source @('run', 'build')
    }
    Write-Host 'All executed checks passed. See docs\VALIDATION.md for observed real-video results and remaining limits.' -ForegroundColor Green
} finally { Pop-Location }
