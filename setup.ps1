[CmdletBinding()]
param([string]$PythonPath,[switch]$Offline,[switch]$EvaluationSamples)
$ErrorActionPreference='Stop'
$ProjectRoot=$PSScriptRoot
$VenvPython=Join-Path $ProjectRoot '.venv\Scripts\python.exe'
function Invoke-Checked {
    param([string]$Command,[string[]]$Arguments)
    & $Command @Arguments
    if($LASTEXITCODE -ne 0){throw "Setup failed with exit code $LASTEXITCODE."}
}
Push-Location $ProjectRoot
try {
    if($Offline){
        if(-not(Test-Path -LiteralPath $VenvPython)){throw 'Python environment missing. Run setup.ps1 online once.'}
        if(-not(Test-Path -LiteralPath '.\node_modules\vite\bin\vite.js')){throw 'Frontend dependencies missing. Run setup.ps1 online once.'}
        if(-not(Test-Path -LiteralPath '.\research\samples\how2sign-sentence.mp4')){throw 'Demo sample missing. Run setup.ps1 -EvaluationSamples online once.'}
        Write-Host 'Offline demo environment ready. No AI models will load.' -ForegroundColor Green
        return
    }
    if(-not(Test-Path -LiteralPath $VenvPython)){
        if(-not $PythonPath){
            $Bundled='C:\Users\ASUS\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
            if(Test-Path -LiteralPath $Bundled){$PythonPath=$Bundled}
            else{$PythonPath=(Get-Command python.exe -ErrorAction Stop).Source}
        }
        Invoke-Checked $PythonPath @('-m','venv',(Join-Path $ProjectRoot '.venv'))
    }
    Invoke-Checked $VenvPython @('-m','pip','install','-r',(Join-Path $ProjectRoot 'backend\requirements-demo.txt'))
    if(-not(Test-Path -LiteralPath '.\node_modules\vite\bin\vite.js')){
        $Npm=(Get-Command npm.cmd -ErrorAction Stop).Source
        if(Test-Path -LiteralPath '.\package-lock.json'){Invoke-Checked $Npm @('ci')}
        else{Invoke-Checked $Npm @('install')}
    }
    if($EvaluationSamples -or -not(Test-Path -LiteralPath '.\research\samples\how2sign-sentence.mp4')){
        Invoke-Checked $VenvPython @('-m','backend.fetch_demo')
    }
    Write-Host 'Static bilingual demo ready. Run .\start.ps1. No ASL models were installed.' -ForegroundColor Green
} finally {Pop-Location}
