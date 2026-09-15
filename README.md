# Agentbay — AI Project Generation Service

## Quick Start

### Prerequisites
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager

### Setup
```bash
uv sync
cp .env.example .env
# fill in OPENAI_API_KEY / GROQ_API_KEY and set INTERNAL_SECRET

uv run uvicorn agent_v1.api.main:app --reload
```

Access the API at **http://localhost:8000/docs**

---

## Overview

Agentbay is an **internal-only code-generation service**. It has no
end-user auth, no database, and no container/runtime layer of its
own — those concerns live in [ZeroTo](../../zeroto-backend), the
platform that calls this service.

```
ZeroTo control plane
   │  X-Internal-Secret header (same trust pattern ZeroTo's
   │  own node <-> control-plane calls use)
   ▼
Agentbay (this service)
   │
   ├── LangGraph pipeline: planner -> architect -> coder
   │     generates a Python project onto local scratch disk
   │
   └── File tools: list / read / write / delete / rename,
         scoped to a single project's directory
```

ZeroTo is responsible for: who the end user is, which org they
belong to, quotas/plans, where the generated project actually runs
(containers, volumes, terminal, ingress), and the finished "deploy"
step. Agentbay only ever answers "generate this" or "read/write this
file," for a project directory it's told about by name.

---

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness check (no auth) |
| GET | `/projects` | List generated project directories |
| POST | `/projects/generate` | Run the planner/architect/coder pipeline for a prompt |
| GET | `/projects/{name}/files` | List files in a project |
| GET | `/projects/{name}/files/read` | Read a file |
| POST | `/projects/{name}/files/write` | Create/update a file |
| DELETE | `/projects/{name}/files/delete` | Delete a file |
| PUT | `/projects/{name}/files/rename` | Rename/move a file or folder |
| POST | `/projects/{name}/folders/create` | Create a folder |
| DELETE | `/projects/{name}/folders/delete` | Delete a folder recursively |

Every route except `/health` requires `X-Internal-Secret: <INTERNAL_SECRET>`.

---

## What lives here vs. what moved to ZeroTo

| Concern | Where |
| --- | --- |
| Prompt -> generated project files | Agentbay (this service) |
| File CRUD on a generated project | Agentbay (this service) |
| End-user auth, orgs, plans/quotas | ZeroTo |
| Container lifecycle, terminal, live preview | ZeroTo |
| Ingress, TLS, deploy | ZeroTo |
| Persistent/durable storage of a project | ZeroTo (+ R2 snapshotting, planned) |

---
