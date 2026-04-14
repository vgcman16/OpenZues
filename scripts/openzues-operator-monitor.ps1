param(
    [int]$Port = $(if ($env:OPENZUES_PORT) { [int]$env:OPENZUES_PORT } else { 8884 }),
    [int]$Cycles = 0,
    [int]$IntervalSeconds = 5,
    [int]$BrowserEvery = 3
)

$ErrorActionPreference = "Stop"
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $utf8NoBom
[Console]::OutputEncoding = $utf8NoBom
$OutputEncoding = $utf8NoBom
$env:PYTHONUTF8 = "1"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$watchDir = Join-Path $env:LOCALAPPDATA "OpenZues\watch"
$watchLog = Join-Path $watchDir "operator-monitor.log"
$watchScreenshot = Join-Path $watchDir "operator-monitor.png"
$browserUrl = "http://127.0.0.1:$Port/"
$browserSession = "openzues-operator-monitor-{0}" -f ([guid]::NewGuid().ToString("N"))
$agentBrowser = Get-Command "agent-browser.cmd" -ErrorAction SilentlyContinue

if (-not (Test-Path $python)) {
    Write-Error "Missing virtualenv Python at '$python'. Create the repo virtualenv first."
    exit 1
}

New-Item -ItemType Directory -Force -Path $watchDir | Out-Null

function Invoke-AgentBrowserStep {
    param(
        [string[]]$Arguments,
        [int]$TimeoutSeconds = 20
    )

    if (-not $agentBrowser) {
        return $false
    }

    $process = Start-Process `
        -FilePath $agentBrowser.Path `
        -ArgumentList (@("--session", $browserSession) + $Arguments) `
        -PassThru `
        -WindowStyle Hidden

    if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
        try {
            $process.Kill()
        } catch {
        }
        return $false
    }

    return ($process.ExitCode -eq 0)
}

function Update-BrowserArtifact {
    if (-not $agentBrowser) {
        return "agent-browser.cmd is not installed, so the browser heartbeat was skipped."
    }

    $startedAt = Get-Date
    $opened = Invoke-AgentBrowserStep -Arguments @("open", $browserUrl) -TimeoutSeconds 20
    if (-not $opened) {
        Start-Sleep -Seconds 1
        $opened = Invoke-AgentBrowserStep -Arguments @("open", $browserUrl) -TimeoutSeconds 20
        if (-not $opened) {
            return "browser open step timed out or failed after one retry."
        }
    }

    Invoke-AgentBrowserStep -Arguments @("wait", "2000") -TimeoutSeconds 10 | Out-Null
    $captured = Invoke-AgentBrowserStep -Arguments @("--annotate", "screenshot") -TimeoutSeconds 20
    if (-not $captured) {
        return "browser screenshot step timed out or failed."
    }

    $screenshotDir = Join-Path $env:USERPROFILE ".agent-browser\tmp\screenshots"
    if (-not (Test-Path $screenshotDir)) {
        return "browser screenshot completed, but no screenshot directory was found."
    }

    $latest = Get-ChildItem -Path $screenshotDir -Filter "*.png" -File -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -ge $startedAt.AddSeconds(-5) } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (-not $latest) {
        $latest = Get-ChildItem -Path $screenshotDir -Filter "*.png" -File -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1
    }

    if (-not $latest) {
        return "browser screenshot completed, but no fresh artifact was found."
    }

    Copy-Item -LiteralPath $latest.FullName -Destination $watchScreenshot -Force
    return "browser screenshot refreshed at $watchScreenshot ($($latest.Length) bytes)"
}

function Write-ConsoleBlock {
    param(
        [object]$Value
    )

    if ($null -eq $Value) {
        return
    }

    if ($Value -is [System.Array]) {
        $text = ($Value | ForEach-Object { "$_" }) -join [Environment]::NewLine
        if ($text) {
            Write-Host $text
        }
        return
    }

    Write-Host "$Value"
}

function Repair-WatchLogEncoding {
    if (-not (Test-Path $watchLog)) {
        return
    }

    $bytes = [System.IO.File]::ReadAllBytes($watchLog)
    if ($bytes.Length -eq 0) {
        return
    }

    if (
        $bytes.Length -ge 3 -and
        $bytes[0] -eq 0xEF -and
        $bytes[1] -eq 0xBB -and
        $bytes[2] -eq 0xBF
    ) {
        return
    }

    $prefixed = New-Object byte[] ($bytes.Length + 3)
    $prefixed[0] = 0xEF
    $prefixed[1] = 0xBB
    $prefixed[2] = 0xBF
    [System.Array]::Copy($bytes, 0, $prefixed, 3, $bytes.Length)
    [System.IO.File]::WriteAllBytes($watchLog, $prefixed)
}

Write-Host "OpenZues operator monitor"
Write-Host "  port: $Port"
Write-Host "  log: $watchLog"
Write-Host "  screenshot: $watchScreenshot"
Write-Host "  browser session: $browserSession"
Write-Host ""

Repair-WatchLogEncoding

$cycle = 0
while ($true) {
    $cycle += 1

    $watchOutput = & $python -m openzues.cli watch `
        --port $Port `
        --launch `
        --cycles 1 `
        --log-file $watchLog 2>&1

    if ($LASTEXITCODE -ne 0) {
        if ($watchOutput) {
            Write-ConsoleBlock $watchOutput
        }
        exit $LASTEXITCODE
    }

    if ($watchOutput) {
        Write-ConsoleBlock $watchOutput
    }

    if ($BrowserEvery -gt 0 -and (($cycle - 1) % $BrowserEvery -eq 0)) {
        $browserNote = Update-BrowserArtifact
        Write-Host "browser heartbeat: $browserNote"
        Repair-WatchLogEncoding
        Add-Content -Path $watchLog -Encoding utf8 -Value ("browser heartbeat: {0}`r`n" -f $browserNote)
    }

    $watchJson = & $python -m openzues.cli watch --port $Port --cycles 1 --json 2>$null
    if ($LASTEXITCODE -eq 0 -and $watchJson) {
        try {
            $payload = $watchJson | ConvertFrom-Json -Depth 100
            $mission = $payload.watched_mission
            if ($mission -and $mission.status -in @("completed", "failed") -and -not $mission.in_progress) {
                break
            }
        } catch {
        }
    }

    if ($Cycles -gt 0 -and $cycle -ge $Cycles) {
        break
    }

    Start-Sleep -Seconds $IntervalSeconds
    Write-Host ""
}
