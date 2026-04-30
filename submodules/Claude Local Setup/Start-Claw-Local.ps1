param(
    [string]$Model = "gemma4:latest",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ClawArgs
)

$repoRoot = Join-Path $PSScriptRoot "claw-code"
$binary = Join-Path $repoRoot "rust\target\release\claw.exe"

if (-not (Test-Path -LiteralPath $binary)) {
    Write-Error "claw.exe was not found at $binary"
    exit 1
}

$env:OPENAI_BASE_URL = "http://127.0.0.1:11434/v1"
$env:OPENAI_API_KEY = "local-dev-token"
Remove-Item Env:ANTHROPIC_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:ANTHROPIC_AUTH_TOKEN -ErrorAction SilentlyContinue
Remove-Item Env:ANTHROPIC_BASE_URL -ErrorAction SilentlyContinue

if ($ClawArgs.Count -eq 0) {
    & $binary --model $Model
} else {
    & $binary --model $Model @ClawArgs
}
