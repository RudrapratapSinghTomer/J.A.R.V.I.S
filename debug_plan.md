# Debug Plan

## Observed Failure
- Latest async runtime log stops at `Initializing memory system...`, before the assistant reaches the final ready prompt.
- `core/intent_router.py` calls `asyncio.wait_for()` and catches `asyncio.TimeoutExpired` without importing `asyncio`.
- Latest successful startup still shows the configured local LLM/model is not ready, and memory begins initializing without completing.
- The refreshed security scan finds a dependency CVE, but the monitor parsed the report as clean.
- Importing speech output prints pygame's support banner into terminal output.

## Root Cause
- `main_async.py` awaited memory initialization during startup. Cognee/LiteLLM/tiktoken startup can block or run long enough to prevent the voice assistant from becoming ready.
- The async router slow path would raise `NameError` as soon as a non-fast-path command reached the LLM route.
- Cognee context loading depends on the configured local model. Starting it while that model is unavailable creates a background task with no useful completion path.
- `pip-audit` exits with code 1 when vulnerabilities are found; the scan script treated that as a command failure, and the monitor did not match `vulnerability`/`CVE-` lines.
- `PYGAME_HIDE_SUPPORT_PROMPT` was not set before importing pygame.

## Fix
- Restore `TIKTOKEN_CACHE_DIR` setup before Cognee/LiteLLM can be imported from the async entry point.
- Move Cognee initialization and context loading into a background thread with explicit timeouts.
- Import `asyncio` in the intent router.
- Skip memory startup when the configured local LLM is not ready, without changing Ollama/model configuration.
- Parse dependency vulnerability lines as security warnings and stop labeling normal pip-audit findings as command failures.
- Set `PYGAME_HIDE_SUPPORT_PROMPT` before pygame import.

## Verification
- Compile the touched Python files.
- Refresh the security scan and confirm `security_monitor.get_latest_report()` reports warnings when CVEs are present.
- Import `core.speech_output` and confirm only the explicit test output appears.
- If audio hardware and Ollama are available, start `python main_async.py` and confirm it reaches the ready prompt even when memory is still loading.
