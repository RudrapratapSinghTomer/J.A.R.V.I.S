# 🧠 JARVIS Long-Term Memory
> Auto-updated by JARVIS as it learns. Treat as ground truth about the user.
> Last Updated: 2026-04-20 · Session 3

---

## 👤 Identity
- **Name:** Rudrapratap
- **OS:** Linux
- **Workspace:** `/home/rudrapratap/Desktop/J.A.R.V.I.S`
- **Primary Language:** Python
- **Location:** Indore, Madhya Pradesh, India 🇮🇳
- **Timezone:** IST (UTC+5:30)
- **Active Hours:** Day — JARVIS should run learning/training jobs at night (IST)

---

## 🖥️ Local Setup
- **LLM Backend:** Ollama + local Gemma 2/4 (weights from personal Google Drive)
- **Custom Weights:** Google Drive `/1qpxL_7k6SPrFX5oKEDuRhWdmNn3BW3VJ` → import as GGUF via Ollama Modelfile
- **Orchestrator:** Ruflo (MCP-compliant)
- **AI Tool:** JARVIS (custom Python assistant)
- **Code Editor:** VS Code (inferred from workspace)
- **Previous AI Tools Used:** OpenClaw (had a security audit session)

---

## 🎯 Goals & Vision
- Build a fully local, self-improving, **zero-cost**, privacy-first personal AI assistant
- All inference runs locally — no API calls, no subscriptions, no billing ever
- Cloud fallback ONLY for free-tier services (no money involved)
- Create an AI that learns from the internet daily (while sleeping, IST nights)
- Enable model fine-tuning and weight persistence using custom Gemma weights
- Connect via **Telegram** for remote access (priority channel)
- Multi-channel personal assistant (voice, text, mobile)
- **Security-aware:** JARVIS must always flag vulnerabilities and run daily security scans

---

## ⚙️ Technical Preferences
- **Privacy:** Absolute local-only. Zero external API calls. Zero billing.
- **Architecture:** Modular, MCP-compliant tools
- **Models:** Local GGUF weights via Ollama only (Gemma 2/4 from personal Drive)
- **Security:** JARVIS must proactively report any vulnerability or security risk found. Daily scan mandatory.
- **Approach:** Build on open-source foundations, customize to needs
- **Channel:** Telegram only (no Discord)
- **Learning:** Daily autonomous web learning — schedule during IST night hours

---

## 💡 Decisions Made
- **Hermes Agent:** adopted as core self-improving + Telegram gateway layer
- **Cognee:** single memory system (no duplicate memory stores)
- **OpenClaw:** skills import only via `hermes claw migrate` — not running as server
- **OpenJarvis:** NOT deployed — borrow patterns only
- **G0DM0D3:** reference only — AutoTune EMA pattern for intent_router
- **Fine-tuning:** Unsloth + LoRA on local Gemma weights (CPU/low VRAM path if GPU unknown)
- **Zero-cost rule:** If a tool or step requires payment, find free alternative or skip
- **Telegram:** First and only remote channel
- **Security scans:** Daily Lynis + dependency audit + port scan (cron at IST night)

---

## 📅 Conversation History Summaries
- **2026-04-18:** Security audit of OpenClaw + Ollama setup
- **2026-04-19:** Integrating JARVIS with Ruflo, MCP tool wrapping, security controls
- **2026-04-20 (AM):** Repository analysis, master integration plan, context files setup
- **2026-04-20 (PM):** User confirmed: Indore IST, Telegram only, zero billing, daily learning at night, deduplication of stack, security always-on

---

## 🔑 Preferences
- Concise responses by default; detailed when asked
- Markdown formatting in responses
- Prefers to understand WHY, not just HOW
- Appreciates architecture diagrams and comparisons
- Interested in cutting-edge AI research (ArXiv, NousResearch)

---
*This file is maintained by JARVIS. Model: add new memories here as you learn them.*
