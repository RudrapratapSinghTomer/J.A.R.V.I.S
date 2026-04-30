# Claude Local Setup

This folder contains a local build of `claw-code` configured to use your Ollama server instead of Anthropic.

## What is inside

- `claw-code\` - cloned source repo
- `Start-Claw-Local.ps1` - launches `claw` against Ollama
- `Doctor-Claw-Local.ps1` - launches `claw` and reminds you to run `/doctor`
- `Smoke-Test-Claw.ps1` - runs a tiny one-shot prompt for quick verification

## Default local wiring

These scripts set:

- `OPENAI_BASE_URL=http://127.0.0.1:11434/v1`
- `OPENAI_API_KEY=local-dev-token`

They also clear any Anthropic env vars in that shell session so `claw` stays local.

## Recommended first run

Open PowerShell in this folder and run:

```powershell
.\Doctor-Claw-Local.ps1
```

When `claw` opens, type:

```text
/doctor
```

## Start a normal local session

```powershell
.\Start-Claw-Local.ps1
```

To choose a different local model:

```powershell
.\Start-Claw-Local.ps1 -Model "qwen3:latest"
.\Start-Claw-Local.ps1 -Model "gemma4:latest"
```

## Run a one-shot prompt

```powershell
.\Start-Claw-Local.ps1 -Model "gemma4:latest" prompt "Summarize this repository"
```

## Fast smoke test

```powershell
.\Smoke-Test-Claw.ps1
```

## Notes

- `qwen3:latest` may respond slowly on local hardware, especially for first-token latency.
- `gemma4:latest` is a better default for quick validation on this machine.
- Rust and the Visual C++ build tools were installed so you can rebuild the repo later if needed.
