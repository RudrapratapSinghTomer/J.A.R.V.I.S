# 📁 Active & Planned Projects
> JARVIS tracks these to maintain context across sessions.
> Model: reference this when user mentions project names.

---

## 🔴 Active Projects

### J.A.R.V.I.S — Personal AI System
- **Status:** In active development
- **Goal:** Fully local, self-improving, privacy-first personal AI
- **Current Phase:** Phase 1 — Memory Foundation
- **Stack:** Python + Ollama (Gemma2) + Ruflo (MCP) + Cognee (memory)
- **Path:** `/home/rudrapratap/Desktop/J.A.R.V.I.S`
- **Next Steps:**
  - Install and configure Cognee memory engine
  - Set up Hermes Agent with Cognee integration
  - Import OpenClaw skills into Hermes
  - Build P0 MCP tool servers (filesystem, shell)
  - Deploy Telegram gateway

---

## 🟡 Planned Projects

### Autonomous Learning Module
- **Goal:** JARVIS learns from internet without user intervention
- **Components:** Web scraper cron + Cognee.remember() + LoRA fine-tuning
- **Status:** Designed (see master integration plan)
- **Start:** After Phase 1 (memory foundation) complete

### Local Claude Integration
- **Goal:** Route Ruflo through local Claude setup
- **Status:** Future — waiting for local Claude weights or API setup
- **Notes:** Will configure via Hermes config.yaml once Claude endpoint is ready

### Fine-tuning Pipeline
- **Goal:** Weekly auto-fine-tuning of Gemma2 on conversation history
- **Components:** Unsloth + LoRA + Ollama model registration
- **Status:** Planned (Phase 6)

---

## ✅ Completed Projects

### OpenClaw Security Audit
- Hardened local Ollama installation
- Secured API endpoints
- Implemented sandboxing for tool execution

### Ruflo + JARVIS MCP Integration
- Wrapped J.A.R.V.I.S tools as MCP-compliant servers
- Implemented security controls (rate limiting, audit logging, encryption)
- Deployed locally

---
*Model: update project status as work progresses. Ask user if unsure about current state.*
