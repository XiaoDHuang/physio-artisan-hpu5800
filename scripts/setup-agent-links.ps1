# Recreate cross-tool symlinks to .agents/ (Claude Code, Cursor, Codex).
# Run from repo root:  powershell -ExecutionPolicy Bypass -File scripts/setup-agent-links.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$agents = Join-Path $root ".agents"

if (-not (Test-Path (Join-Path $agents "commands"))) {
    throw "Missing .agents/commands — clone the repo or restore .agents/ first."
}

function Ensure-DirLink {
    param(
        [string]$LinkPath,
        [string]$TargetPath
    )
    $parent = Split-Path $LinkPath -Parent
    if (-not (Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    if (Test-Path $LinkPath) {
        $item = Get-Item $LinkPath -Force
        if ($item.LinkType -in @("SymbolicLink", "Junction") -and $item.Target -contains $TargetPath) {
            Write-Host "OK (exists): $LinkPath"
            return
        }
        Remove-Item $LinkPath -Force -Recurse
    }
    try {
        New-Item -ItemType SymbolicLink -Path $LinkPath -Target $TargetPath -Force | Out-Null
        Write-Host "SYMLINK: $LinkPath -> $TargetPath"
    } catch {
        New-Item -ItemType Junction -Path $LinkPath -Target $TargetPath -Force | Out-Null
        Write-Host "JUNCTION: $LinkPath -> $TargetPath"
    }
}

$links = @(
    @{ Link = ".claude\commands"; Target = "commands" },
    @{ Link = ".claude\skills";   Target = "skills" },
    @{ Link = ".cursor\commands"; Target = "commands" },
    @{ Link = ".cursor\skills";   Target = "skills" },
    @{ Link = ".codex\commands";  Target = "commands" },
    @{ Link = ".codex\skills";    Target = "skills" }
)

foreach ($entry in $links) {
    Ensure-DirLink `
        -LinkPath (Join-Path $root $entry.Link) `
        -TargetPath (Join-Path $agents $entry.Target)
}

Write-Host "Done. Canonical agent config lives in .agents/"
