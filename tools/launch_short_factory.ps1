[CmdletBinding()]
param(
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'

$RepoRoot = 'D:\HermesWorkspace\client-short-factory'
$JobsRoot = Join-Path $RepoRoot 'scratch\phase-0a-webui\jobs'
$CompositionProjectsRoot = Join-Path $RepoRoot 'scratch\creative-short-002-v1\composition-projects'
$RuntimeRoot = Join-Path $RepoRoot 'scratch\phase-0a-webui'
$Python = 'C:\Users\higes\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe'
$Port = 18765
$Origin = "http://127.0.0.1:$Port"
$StatePath = Join-Path $RuntimeRoot 'desktop-launcher-state.json'
$MutexName = 'Local\ShortFactoryReviewUiLauncher'
$BuildExtensions = @('.py', '.json', '.html', '.js', '.css')

function Show-LauncherError([string]$Message) {
    try {
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show(
            $Message,
            'Short Factory',
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Error
        ) | Out-Null
    }
    catch {
        Write-Error $Message
    }
}

function Get-PortListener {
    return Get-NetTCPConnection `
        -LocalAddress '127.0.0.1' `
        -LocalPort $Port `
        -State Listen `
        -ErrorAction SilentlyContinue |
        Select-Object -First 1
}

function Get-ExpectedServerProcess {
    $listener = Get-PortListener
    if ($null -eq $listener) {
        return $null
    }

    $process = Get-CimInstance Win32_Process `
        -Filter "ProcessId=$($listener.OwningProcess)" `
        -ErrorAction SilentlyContinue
    if ($null -eq $process) {
        return $null
    }

    $commandLine = [string]$process.CommandLine
    $expectedJobs = [regex]::Escape($JobsRoot)
    if (
        $commandLine -notmatch 'short_factory\s+review-ui' -or
        $commandLine -notmatch $expectedJobs -or
        $commandLine -notmatch '--port\s+18765'
    ) {
        throw "Port $Port is already used by another application."
    }
    return $process
}

function Get-ProcessCreatedUtc($Process) {
    return $Process.CreationDate.ToUniversalTime().ToString('o')
}

function Get-AppBuildFingerprint {
    $files = @(
        Get-ChildItem -LiteralPath (Join-Path $RepoRoot 'short_factory') `
            -Recurse `
            -File `
            -ErrorAction Stop |
            Where-Object { $BuildExtensions -contains $_.Extension.ToLowerInvariant() }
        Get-ChildItem -LiteralPath (Join-Path $RepoRoot 'config') `
            -Recurse `
            -File `
            -ErrorAction Stop |
            Where-Object { $BuildExtensions -contains $_.Extension.ToLowerInvariant() }
        Get-Item -LiteralPath (Join-Path $RepoRoot 'pyproject.toml') -ErrorAction Stop
        Get-Item -LiteralPath $PSCommandPath -ErrorAction Stop
    ) | Sort-Object FullName

    $manifest = New-Object System.Text.StringBuilder
    foreach ($file in $files) {
        $relativePath = $file.FullName.Substring($RepoRoot.Length).TrimStart('\', '/')
        $fileHash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        [void]$manifest.Append($relativePath.ToLowerInvariant())
        [void]$manifest.Append("`0")
        [void]$manifest.Append($fileHash)
        [void]$manifest.Append("`n")
    }

    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($manifest.ToString())
        return ([BitConverter]::ToString($sha256.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant()
    }
    finally {
        $sha256.Dispose()
    }
}

function Test-ServerHasCompositionRoot($Process) {
    $commandLine = [string]$Process.CommandLine
    $expectedRoot = [regex]::Escape($CompositionProjectsRoot)
    return (
        $commandLine -match '--composition-projects-root' -and
        $commandLine -match $expectedRoot
    )
}

function Test-ServerHasCurrentBuild($Process, [string]$BuildFingerprint) {
    if (-not (Test-Path -LiteralPath $StatePath -PathType Leaf)) {
        return $false
    }
    try {
        $state = Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json
        return (
            [int]$state.pid -eq [int]$Process.ProcessId -and
            [string]$state.process_created_utc -eq (Get-ProcessCreatedUtc $Process) -and
            [string]$state.build_fingerprint -eq $BuildFingerprint
        )
    }
    catch {
        return $false
    }
}

function Test-LaunchUrl([string]$Url) {
    return $Url -match '^http://127\.0\.0\.1:18765/#token=[A-Za-z0-9_-]{20,256}$'
}

function Find-LaunchUrl($Process) {
    $created = $Process.CreationDate.ToUniversalTime().AddSeconds(-2)

    if (Test-Path -LiteralPath $StatePath -PathType Leaf) {
        try {
            $state = Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json
            if (
                [int]$state.pid -eq [int]$Process.ProcessId -and
                [string]$state.process_created_utc -eq (Get-ProcessCreatedUtc $Process) -and
                (Test-LaunchUrl ([string]$state.launch_url))
            ) {
                return [string]$state.launch_url
            }
        }
        catch {
            # Ignore stale or partially written launcher state.
        }
    }

    $logs = Get-ChildItem -LiteralPath $RuntimeRoot `
        -Filter 'server-*.out.log' `
        -File `
        -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTimeUtc -ge $created } |
        Sort-Object LastWriteTimeUtc -Descending

    foreach ($log in $logs) {
        foreach ($line in (Get-Content -LiteralPath $log.FullName -ErrorAction SilentlyContinue)) {
            if ($line -match '^REVIEW_UI_URL\s+(http://127\.0\.0\.1:18765/#token=[A-Za-z0-9_-]{20,256})$') {
                return $Matches[1]
            }
        }
    }
    return $null
}

function Save-LauncherState(
    $Process,
    [string]$LaunchUrl,
    [string]$BuildFingerprint
) {
    $document = [ordered]@{
        schema_version = 2
        pid = [int]$Process.ProcessId
        process_created_utc = Get-ProcessCreatedUtc $Process
        launch_url = $LaunchUrl
        jobs_root = $JobsRoot
        composition_projects_root = $CompositionProjectsRoot
        build_fingerprint = $BuildFingerprint
        updated_at_utc = [DateTime]::UtcNow.ToString('o')
    }
    $temporary = "$StatePath.tmp"
    $document | ConvertTo-Json | Set-Content -LiteralPath $temporary -Encoding UTF8
    Move-Item -LiteralPath $temporary -Destination $StatePath -Force
}

function Stop-ReviewServerForRestart($Process, [string]$FailureMessage) {
    Stop-Process -Id $Process.ProcessId -ErrorAction Stop
    $deadline = (Get-Date).AddSeconds(10)
    while ((Get-PortListener) -and (Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 100
    }
    if (Get-PortListener) {
        throw $FailureMessage
    }
}

function Start-ReviewServer {
    if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
        throw "Hermes Python was not found: $Python"
    }
    New-Item -ItemType Directory -Path $RuntimeRoot -Force | Out-Null
    New-Item -ItemType Directory -Path $JobsRoot -Force | Out-Null
    New-Item -ItemType Directory -Path $CompositionProjectsRoot -Force | Out-Null

    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $stdout = Join-Path $RuntimeRoot "server-desktop-$stamp.out.log"
    $stderr = Join-Path $RuntimeRoot "server-desktop-$stamp.err.log"
    $arguments = @(
        '-B',
        '-m',
        'short_factory',
        'review-ui',
        '--jobs-root',
        $JobsRoot,
        '--composition-projects-root',
        $CompositionProjectsRoot,
        '--port',
        "$Port",
        '--no-browser'
    )

    Start-Process `
        -FilePath $Python `
        -ArgumentList $arguments `
        -WorkingDirectory $RepoRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr | Out-Null

    $deadline = (Get-Date).AddSeconds(15)
    while ((Get-Date) -lt $deadline) {
        $process = Get-ExpectedServerProcess
        if ($null -ne $process -and (Test-Path -LiteralPath $stdout -PathType Leaf)) {
            foreach ($line in (Get-Content -LiteralPath $stdout -ErrorAction SilentlyContinue)) {
                if ($line -match '^REVIEW_UI_URL\s+(http://127\.0\.0\.1:18765/#token=[A-Za-z0-9_-]{20,256})$') {
                    return [pscustomobject]@{
                        Process = $process
                        LaunchUrl = $Matches[1]
                    }
                }
            }
        }
        Start-Sleep -Milliseconds 200
    }

    $detail = ''
    if (Test-Path -LiteralPath $stderr -PathType Leaf) {
        $detail = (Get-Content -LiteralPath $stderr -Raw -ErrorAction SilentlyContinue).Trim()
    }
    if ($detail) {
        throw "Review server did not start. $detail"
    }
    throw 'Review server did not start within 15 seconds.'
}

$mutex = New-Object System.Threading.Mutex($false, $MutexName)
$hasMutex = $false
try {
    $hasMutex = $mutex.WaitOne([TimeSpan]::FromSeconds(20))
    if (-not $hasMutex) {
        throw 'Another Short Factory launcher is still starting.'
    }

    $buildFingerprint = Get-AppBuildFingerprint
    $server = Get-ExpectedServerProcess
    $launchUrl = $null
    if ($null -ne $server -and -not (Test-ServerHasCompositionRoot $server)) {
        Stop-ReviewServerForRestart `
            $server `
            'The legacy review server could not be restarted safely.'
        $server = $null
    }
    if (
        $null -ne $server -and
        -not (Test-ServerHasCurrentBuild $server $buildFingerprint)
    ) {
        Stop-ReviewServerForRestart `
            $server `
            'The outdated review server could not be restarted safely.'
        $server = $null
    }
    if ($null -ne $server) {
        $launchUrl = Find-LaunchUrl $server
        if (-not (Test-LaunchUrl ([string]$launchUrl))) {
            Stop-ReviewServerForRestart `
                $server `
                'The existing review server could not be restarted safely.'
            $server = $null
        }
    }

    if ($null -eq $server) {
        $started = Start-ReviewServer
        $server = $started.Process
        $launchUrl = $started.LaunchUrl
    }

    Save-LauncherState $server $launchUrl $buildFingerprint
    if (-not $NoBrowser) {
        Start-Process -FilePath $launchUrl | Out-Null
    }
    Write-Output $launchUrl
}
catch {
    Show-LauncherError $_.Exception.Message
    exit 1
}
finally {
    if ($hasMutex) {
        $mutex.ReleaseMutex()
    }
    $mutex.Dispose()
}
