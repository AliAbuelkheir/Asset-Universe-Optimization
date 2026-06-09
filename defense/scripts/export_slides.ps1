param(
    [string]$DeckPath = (Join-Path $PSScriptRoot '..\slides\defense.pptx'),
    [string]$OutputDir = (Join-Path $PSScriptRoot '..\slides\current'),
    [int]$Width = 1920,
    [int]$Height = 1080,
    [int]$TimeoutSeconds = 180,
    [switch]$Worker,
    [string]$ManifestPath
)

$ErrorActionPreference = 'Stop'

function Resolve-FullPath {
    param([Parameter(Mandatory = $true)][string]$Path)

    $executionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path)
}

function Assert-SafeOutputDir {
    param([Parameter(Mandatory = $true)][string]$Path)

    $fullPath = Resolve-FullPath $Path
    $repoRoot = Resolve-FullPath (Join-Path $PSScriptRoot '..\..')
    $defenseRoot = Resolve-FullPath (Join-Path $PSScriptRoot '..')
    $slidesRoot = Resolve-FullPath (Join-Path $PSScriptRoot '..\slides')
    $driveRoot = [System.IO.Path]::GetPathRoot($fullPath).TrimEnd('\')
    $trimmed = $fullPath.TrimEnd('\')

    $blocked = @(
        $driveRoot,
        $repoRoot.TrimEnd('\'),
        $defenseRoot.TrimEnd('\'),
        $slidesRoot.TrimEnd('\')
    )

    if ($blocked -contains $trimmed) {
        throw "Refusing to replace unsafe output directory: $fullPath"
    }

    $parent = Split-Path -Parent $fullPath
    if (-not $parent) {
        throw "Output directory must have a parent directory: $fullPath"
    }

    $fullPath
}

function Stop-ProcessTree {
    param([Parameter(Mandatory = $true)][int]$ProcessId)

    $children = Get-CimInstance Win32_Process -Filter "ParentProcessId=$ProcessId" -ErrorAction SilentlyContinue
    foreach ($child in $children) {
        Stop-ProcessTree -ProcessId ([int]$child.ProcessId)
    }

    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

function ConvertTo-QuotedArgument {
    param([Parameter(Mandatory = $true)][string]$Value)

    '"' + $Value.Replace('"', '\"') + '"'
}

function Test-PngSet {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][int]$ExpectedCount,
        [Parameter(Mandatory = $true)][int]$ExpectedWidth,
        [Parameter(Mandatory = $true)][int]$ExpectedHeight
    )

    Add-Type -AssemblyName System.Drawing

    $files = Get-ChildItem -LiteralPath $Path -Filter 'slide-*.png' -File | Sort-Object Name
    if ($files.Count -ne $ExpectedCount) {
        throw "Expected $ExpectedCount PNG files, found $($files.Count)."
    }

    for ($i = 1; $i -le $ExpectedCount; $i++) {
        $expectedName = 'slide-{0:D3}.png' -f $i
        $file = $files[$i - 1]

        if ($file.Name -ne $expectedName) {
            throw "Expected $expectedName at position $i, found $($file.Name)."
        }

        if ($file.Length -le 0) {
            throw "Exported file is empty: $($file.FullName)"
        }

        $image = [System.Drawing.Image]::FromFile($file.FullName)
        try {
            if ($image.Width -ne $ExpectedWidth -or $image.Height -ne $ExpectedHeight) {
                throw "Expected $expectedName to be ${ExpectedWidth}x${ExpectedHeight}, found $($image.Width)x$($image.Height)."
            }
        }
        finally {
            $image.Dispose()
        }
    }
}

function Export-SlidesWithPowerPoint {
    param(
        [Parameter(Mandatory = $true)][string]$SourceDeck,
        [Parameter(Mandatory = $true)][string]$Destination,
        [Parameter(Mandatory = $true)][int]$ExportWidth,
        [Parameter(Mandatory = $true)][int]$ExportHeight,
        [Parameter(Mandatory = $true)][string]$ExportManifestPath
    )

    $powerPoint = $null
    $presentation = $null
    $ownsPowerPoint = $false

    try {
        if (-not (Test-Path -LiteralPath $SourceDeck -PathType Leaf)) {
            throw "Deck not found: $SourceDeck"
        }

        if (Test-Path -LiteralPath $Destination) {
            Remove-Item -LiteralPath $Destination -Recurse -Force
        }
        New-Item -ItemType Directory -Path $Destination -Force | Out-Null

        $existingPowerPointIds = @(Get-Process POWERPNT -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)
        $powerPoint = New-Object -ComObject PowerPoint.Application
        Start-Sleep -Milliseconds 500
        $currentPowerPointIds = @(Get-Process POWERPNT -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)
        $ownsPowerPoint = @($currentPowerPointIds | Where-Object { $existingPowerPointIds -notcontains $_ }).Count -gt 0

        $msoTrue = -1
        $msoFalse = 0

        $presentation = $powerPoint.Presentations.Open($SourceDeck, $msoTrue, $msoFalse, $msoFalse)
        $slideCount = [int]$presentation.Slides.Count

        for ($i = 1; $i -le $slideCount; $i++) {
            $name = 'slide-{0:D3}.png' -f $i
            $target = Join-Path $Destination $name
            $slide = $presentation.Slides.Item($i)
            try {
                $slide.Export($target, 'PNG', $ExportWidth, $ExportHeight)
            }
            finally {
                [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($slide)
            }
        }

        [pscustomobject]@{
            deckPath = $SourceDeck
            outputDir = $Destination
            slideCount = $slideCount
            width = $ExportWidth
            height = $ExportHeight
            exportedAt = (Get-Date).ToString('o')
        } | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $ExportManifestPath -Encoding UTF8
    }
    finally {
        if ($presentation -ne $null) {
            try {
                $presentation.Close()
            }
            finally {
                [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($presentation)
            }
        }

        if ($powerPoint -ne $null) {
            try {
                if ($ownsPowerPoint) {
                    $powerPoint.Quit()
                }
            }
            finally {
                [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($powerPoint)
            }
        }

        [GC]::Collect()
        [GC]::WaitForPendingFinalizers()
    }
}

$resolvedDeck = Resolve-FullPath $DeckPath
$resolvedOutput = Assert-SafeOutputDir $OutputDir

if ($Worker) {
    if (-not $ManifestPath) {
        throw 'Worker mode requires -ManifestPath.'
    }

    Export-SlidesWithPowerPoint `
        -SourceDeck $resolvedDeck `
        -Destination $resolvedOutput `
        -ExportWidth $Width `
        -ExportHeight $Height `
        -ExportManifestPath (Resolve-FullPath $ManifestPath)
    exit 0
}

if ($TimeoutSeconds -lt 1) {
    throw 'TimeoutSeconds must be at least 1.'
}

$outputParent = Split-Path -Parent $resolvedOutput
New-Item -ItemType Directory -Path $outputParent -Force | Out-Null

$runId = [guid]::NewGuid().ToString('N')
$stagingDir = Join-Path $outputParent ('.current-staging-' + $runId)
$manifest = Join-Path $outputParent ('.current-staging-' + $runId + '.json')
$stdout = Join-Path $outputParent ('.current-staging-' + $runId + '.out.log')
$stderr = Join-Path $outputParent ('.current-staging-' + $runId + '.err.log')

$powerShellExe = Join-Path $PSHOME 'powershell.exe'
if (-not (Test-Path -LiteralPath $powerShellExe -PathType Leaf)) {
    $powerShellExe = (Get-Command powershell.exe -ErrorAction Stop).Source
}

$arguments = @(
    '-NoProfile'
    '-ExecutionPolicy Bypass'
    ('-File ' + (ConvertTo-QuotedArgument $PSCommandPath))
    '-Worker'
    ('-DeckPath ' + (ConvertTo-QuotedArgument $resolvedDeck))
    ('-OutputDir ' + (ConvertTo-QuotedArgument $stagingDir))
    ('-Width ' + $Width)
    ('-Height ' + $Height)
    ('-ManifestPath ' + (ConvertTo-QuotedArgument $manifest))
) -join ' '

$process = $null
try {
    $process = Start-Process `
        -FilePath $powerShellExe `
        -ArgumentList $arguments `
        -PassThru `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr

    $finished = $process.WaitForExit($TimeoutSeconds * 1000)
    if (-not $finished) {
        Stop-ProcessTree -ProcessId $process.Id
        throw "Slide export timed out after $TimeoutSeconds seconds. Previous snapshot was left unchanged."
    }

    # Complete redirected stream handling before reading ExitCode in Windows PowerShell.
    $process.WaitForExit()
    $process.Refresh()
    $rawExitCode = [string]$process.ExitCode
    $exitCode = if ([string]::IsNullOrWhiteSpace($rawExitCode)) { $null } else { [int]$rawExitCode }

    if (-not (Test-Path -LiteralPath $manifest -PathType Leaf)) {
        $workerError = if (Test-Path -LiteralPath $stderr) { Get-Content -LiteralPath $stderr -Raw } else { '' }
        $exitDetail = if ($null -ne $exitCode) { " with exit code $exitCode" } else { '' }
        throw "Slide export worker failed$exitDetail and did not produce a manifest. Previous snapshot was left unchanged.`n$workerError"
    }

    $metadata = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
    Test-PngSet `
        -Path $stagingDir `
        -ExpectedCount ([int]$metadata.slideCount) `
        -ExpectedWidth $Width `
        -ExpectedHeight $Height

    $backupDir = Join-Path $outputParent ('.current-backup-' + $runId)
    if (Test-Path -LiteralPath $resolvedOutput) {
        Move-Item -LiteralPath $resolvedOutput -Destination $backupDir -Force
    }

    try {
        Move-Item -LiteralPath $stagingDir -Destination $resolvedOutput -Force
    }
    catch {
        if (Test-Path -LiteralPath $backupDir) {
            Move-Item -LiteralPath $backupDir -Destination $resolvedOutput -Force
        }
        throw
    }

    if (Test-Path -LiteralPath $backupDir) {
        Remove-Item -LiteralPath $backupDir -Recurse -Force
    }

    Write-Host ("Exported {0} slides to {1} at {2}x{3}." -f $metadata.slideCount, $resolvedOutput, $Width, $Height)
}
finally {
    if (Test-Path -LiteralPath $stagingDir) {
        Remove-Item -LiteralPath $stagingDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    Remove-Item -LiteralPath $manifest, $stdout, $stderr -Force -ErrorAction SilentlyContinue
}
