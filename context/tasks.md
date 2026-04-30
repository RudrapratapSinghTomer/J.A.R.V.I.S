# ✅ Task List & Current Priorities
> Model: check this at the start of each session to understand what's pending.
> User: update this as tasks complete or change priority.
> **Hard Rules:** Zero billing · Absolute local-only · Telegram only · Security always-on

---

## 🔴 High Priority (This Week)

### Phase 1: Memory Foundation
- [ ] `pip install cognee feedparser pip-audit`
- [ ] Create `J.A.R.V.I.S/memory/cognee_bridge.py`
- [ ] Wire `cognee-mcp` server into Ruflo config
- [ ] Test memory round-trip: store → recall → verify
- [ ] Load `context/*.md` files into Cognee on startup

### Phase 4: Semantic Intelligence (IN PROGRESS)
- [x] Create `core/semantic_router.py`
- [x] Update `core/intent_router.py` with hybrid logic
- [/] Pull `nomic-embed-text` for local embeddings
- [ ] Test semantic intent switching (Weather vs Search vs System)

### Phase 12: Secure Terminal Access
- [ ] Create `skills/terminal_skill.py`
- [/] Integrate Face ID Guard hook into Terminal intent

### Phase 2: Model Import from Google Drive (LATER)
- [ ] `pip install gdown`
- [ ] Download weights: `gdown --folder https://drive.google.com/drive/folders/1qpxL_7k6SPrFX5oKEDuRhWdmNn3BW3VJ -O ~/.jarvis/models/`
- [ ] Check format: GGUF already? or `.safetensors` needing conversion?
- [ ] Create Ollama `Modelfile` pointing to downloaded weights
- [ ] Register: `ollama create jarvis-gemma -f Modelfile` + test

---

## 🟡 Medium Priority (Next 2 Weeks)

### Phase 3: Hermes Agent Integration
- [ ] Install Hermes Agent
- [ ] **IMPORTANT:** Set `memory: provider: cognee` — disable Hermes' built-in Honcho memory
- [ ] Run `hermes claw migrate` to import OpenClaw skills
- [ ] Point Hermes at `jarvis-gemma` model (local Ollama)
- [ ] Test Hermes ↔ Ruflo MCP bridge

### Phase 4: Telegram Gateway (Priority Channel)
- [ ] Create Telegram bot via @BotFather (free, no billing)
- [ ] Add `TELEGRAM_BOT_TOKEN` to `~/.jarvis/.env`
- [ ] Configure `allowed_users` whitelist in Hermes config (security!)
- [ ] `hermes gateway start` — test message from phone

### Phase 5: Security Scanning (Always-On)
- [ ] `sudo apt install lynis`
- [ ] `pip install pip-audit`
- [ ] Create `J.A.R.V.I.S/scripts/security_scan.sh`
- [ ] Set cron: daily 2 AM IST = `30 20 * * *` (UTC)
- [ ] Add session-start hook: JARVIS reads latest scan report on startup
- [ ] Test: run scan manually, verify report generated at `~/.jarvis/security/`

---

## 🟢 Lower Priority (Month+)

### Phase 6: Autonomous Learning (IST Night Cron)
- [ ] Create `J.A.R.V.I.S/skills/autonomous_learner.py`
- [ ] Set cron: daily 1 AM IST = `30 19 * * *` (UTC)
- [ ] Sources: ArXiv AI/ML, HN (100+ points), r/LocalLLaMA, Linux Security, NVD CVE feed
- [ ] Test: morning session shows overnight knowledge added to Cognee
- [ ] Verify CVE feed → security-aware learning working

### Phase 7: Model Fine-tuning
- [ ] Check hardware: `nvidia-smi` (GPU) or `lscpu` (for CPU-only path)
- [ ] GPU: `pip install unsloth`
- [ ] CPU fallback: `llama.cpp finetune` (slower but free)
- [ ] Export Cognee conversations as instruction fine-tuning data
- [ ] Run first LoRA pass on `jarvis-gemma` weights
- [ ] Re-register fine-tuned model in Ollama

---

## ✅ Previously Blocked — Now Resolved
- ~~GPU VRAM?~~ → Design for **CPU-safe path** (QLoRA / llama.cpp finetune)
- ~~Channel?~~ → **Telegram only** (no Discord)
- ~~Claude setup?~~ → **Not used.** Custom Gemma weights from personal Drive.
- ~~Privacy level?~~ → **Absolute local. Zero billing.**
- ~~Learning frequency?~~ → **Daily, 1 AM IST**

---

## 📝 Notes
- Cron times: IST = UTC+5:30 → IST 1 AM = 19:30 UTC · IST 2 AM = 20:30 UTC
- Security scan runs 30min AFTER learning so scan catches any new files
- Never install a tool requiring payment/billing — find free alternative or skip
- `awesome-llm-apps` = reference only, never deploy
- `OpenJarvis` = reference only, never deploy

---
*Model: mark tasks [x] when done. Add new tasks from conversations.*
