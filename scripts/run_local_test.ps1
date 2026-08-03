Param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8011,
    [string]$PythonExe = ".\.venv\Scripts\python.exe",
    [int]$HealthTimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"

function Test-HealthEndpoint {
    Param(
        [string]$Url
    )

    try {
        $null = Invoke-RestMethod -Method Get -Uri $Url -TimeoutSec 3
        return $true
    }
    catch {
        return $false
    }
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $scriptRoot "..")
Set-Location $projectRoot

$healthUrl = "http://$HostAddress`:$Port/health"
$askUrl = "http://$HostAddress`:$Port/ask"
$startedServer = $false
$serverProcess = $null

$identityQuery = -join @([char]0x0645, [char]0x0646, ' ', [char]0x0647, [char]0x064A, ' ', [char]0x0646, [char]0x0633, [char]0x064A, [char]0x0645, [char]0x061F)
$projectQuery = -join @([char]0x0645, [char]0x0627, ' ', [char]0x0647, [char]0x0648, ' ', [char]0x0647, [char]0x062F, [char]0x0641, ' ', [char]0x0627, [char]0x0644, [char]0x0645, [char]0x0634, [char]0x0631, [char]0x0648, [char]0x0639, [char]0x061F)
$greetingQuery = -join @([char]0x0645, [char]0x0631, [char]0x062D, [char]0x0628, [char]0x0627)

if (-not (Test-HealthEndpoint -Url $healthUrl)) {
    $env:AMEER_DEBUG = "1"
    $env:AMEER_HOST = $HostAddress
    $env:AMEER_PORT = "$Port"

    $serverArgs = @("start_ameer.py")

    Write-Host "[INFO] Starting local server in debug mode..."
    $serverProcess = Start-Process -FilePath $PythonExe -ArgumentList $serverArgs -PassThru
    $startedServer = $true

    $deadline = (Get-Date).AddSeconds($HealthTimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-HealthEndpoint -Url $healthUrl) {
            break
        }
        Start-Sleep -Milliseconds 500
    }

    if (-not (Test-HealthEndpoint -Url $healthUrl)) {
        if ($serverProcess -and -not $serverProcess.HasExited) {
            Stop-Process -Id $serverProcess.Id -Force
        }
        throw "Server did not become healthy within $HealthTimeoutSeconds seconds."
    }
}
else {
    Write-Host "[INFO] Reusing existing server at $healthUrl"
}

$tests = @(
    @{ Name = "Identity"; Query = $identityQuery; MaxResults = 5 },
    @{ Name = "Project"; Query = $projectQuery; MaxResults = 5 },
    @{ Name = "Greeting"; Query = $greetingQuery; MaxResults = 5 }
)

Write-Host ""
Write-Host "[INFO] Running API tests against $askUrl"

foreach ($test in $tests) {
    $body = @{
        query = $test.Query
        max_results = $test.MaxResults
    } | ConvertTo-Json -Depth 5

    $response = Invoke-RestMethod `
        -Method Post `
        -Uri $askUrl `
        -ContentType "application/json; charset=utf-8" `
        -Body $body

    $buildId = $response.build_id
    $commit = $response.commit
    $responsePort = $response.port
    $finalReply = $response.reply

    Write-Host ""
    Write-Host "===== $($test.Name) ====="
    Write-Host "build_id: $buildId"
    Write-Host "commit: $commit"
    Write-Host "port: $responsePort"
    Write-Host "final reply: $finalReply"
}

if ($startedServer -and $serverProcess -and -not $serverProcess.HasExited) {
    Write-Host ""
    Write-Host "[INFO] Stopping local test server (PID: $($serverProcess.Id))"
    Stop-Process -Id $serverProcess.Id -Force
}

Write-Host ""
Write-Host "[INFO] Local test run completed successfully."
