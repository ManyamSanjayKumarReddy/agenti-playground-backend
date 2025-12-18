# AI Project Builder – Runtime & Agentic Execution Platform

## Overview

AI Project Builder is an **agentic, backend-first execution platform** designed to:

* Generate Python projects using AI agents
* Run projects inside isolated Docker containers
* Provide **fully interactive WebSocket terminals** (xterm.js compatible)
* Manage runtime state via PostgreSQL (Tortoise ORM)
* Serve as a foundation for a **web-based AI IDE**

The platform intentionally avoids REST-based execution in favor of **persistent WebSocket terminals**, similar to Replit or GitHub Codespaces.

---

## Core Principles

| Principle                 | Description                                            |
| ------------------------- | ------------------------------------------------------ |
| DB as Source of Truth     | PostgreSQL stores container metadata and runtime state |
| Docker Isolation          | Each project runs in its own container                 |
| WebSocket-First Execution | All command execution is interactive via PTY           |
| Agent-Friendly            | Designed for AI agent orchestration and automation     |
| Backend-First             | UI is a client, not a controller                       |

---

## Current Architecture (Implemented)

```
Client (Web UI)
   │
   ├── REST APIs (metadata, files, lifecycle)
   │
   └── WebSocket (interactive terminal)
        │
FastAPI Backend
   │
   ├── PostgreSQL (runtime state)
   ├── Docker Engine
   └── AI Agent Pipeline
```

---

## Implemented Features (As of Now)

### Runtime & Container Management

| Feature                                  | Status      |
| ---------------------------------------- | ----------- |
| DB-backed runtime repository             | ✅ Completed |
| Docker ↔ DB reconciliation on startup    | ✅ Completed |
| Container create / start / stop / delete | ✅ Completed |
| Auto-reattach to existing containers     | ✅ Completed |
| CPU & RAM limits                         | ✅ Completed |
| WebSocket terminal (PTY-based)           | ✅ Completed |
| Process manager (legacy)                 | ❌ Removed   |

---

### API Capabilities

| Category           | Details                                 |
| ------------------ | --------------------------------------- |
| Project generation | AI agents generate full Python projects |
| File listing       | Read-only file listing per project      |
| File reading       | Read any project file                   |
| Runtime status     | Container lifecycle status              |
| Execution          | Interactive WebSocket terminal          |

---

## New Required Features (Requested)

The following are **approved, required features**, ordered by **business and architectural priority**.

---

## 🚀 Phase 1 – File Management & Editor Backend (Highest Priority)

### Objective

Enable **full CRUD operations** on project files and folders to support a web-based editor.

### Required Capabilities

| Feature           | Description                     |
| ----------------- | ------------------------------- |
| Create file       | Create new files in any project |
| Create folder     | Create nested directories       |
| Read file         | Already implemented             |
| Update file       | Save edited file contents       |
| Delete file       | Remove files                    |
| Delete folder     | Remove directories recursively  |
| Rename / move     | Rename files & folders          |
| Project-level ops | Bulk actions (future-safe)      |

### New APIs (Planned)

| Method | Endpoint                        | Purpose               |
| ------ | ------------------------------- | --------------------- |
| POST   | `/projects/{name}/files/create` | Create file or folder |
| PUT    | `/projects/{name}/files/write`  | Save file             |
| DELETE | `/projects/{name}/files/delete` | Delete file/folder    |
| POST   | `/projects/{name}/files/rename` | Rename / move         |

### Notes

* All paths **must be relative**
* Strict project root isolation
* Atomic writes (no partial saves)
* UI editor (Monaco / CodeMirror) will consume these APIs

---

## 🔐 Phase 2 – Security Hardening (High Priority)

### Objective

Make the platform safe for **multi-user and production environments**.

### Planned Hardening Measures

| Area          | Action                           |
| ------------- | -------------------------------- |
| Docker user   | Run containers as non-root       |
| Privileges    | `no-new-privileges` flag         |
| Capabilities  | Drop Linux capabilities          |
| Seccomp       | Restrictive seccomp profile      |
| FS isolation  | Read-only root FS where possible |
| Network       | Restrict container networking    |
| Rate limiting | API & WebSocket limits           |

### Outcome

* Prevent container breakout
* Minimize blast radius
* Production-ready security posture

---

## 🛠️ Phase 3 – Admin & Ops (Critical for Scale)

### Objective

Provide **operational visibility and control** for administrators.

### Admin APIs

| Feature           | Description                       |
| ----------------- | --------------------------------- |
| List runtimes     | All projects & container states   |
| Health metrics    | Runtime health                    |
| Orphan cleanup    | Detect & remove unused containers |
| Force stop/remove | Admin override                    |
| Disk usage        | Per-project usage                 |
| Audit logs        | Runtime & file operations         |

### Example Admin Endpoints

| Method | Endpoint                    |
| ------ | --------------------------- |
| GET    | `/admin/runtimes`           |
| POST   | `/admin/runtimes/{id}/stop` |
| DELETE | `/admin/runtimes/{id}`      |
| GET    | `/admin/health`             |

---

## Priority Roadmap (Final)

| Priority | Phase   | Focus                     |
| -------- | ------- | ------------------------- |
| 🔴 P0    | Phase 1 | File editor CRUD backend  |
| 🔴 P0    | Phase 1 | Folder management         |
| 🟠 P1    | Phase 2 | Docker security hardening |
| 🟠 P1    | Phase 2 | Privilege reduction       |
| 🟡 P2    | Phase 3 | Admin & ops APIs          |
| 🟡 P2    | Phase 3 | Cleanup jobs & monitoring |

---

## What Is Explicitly NOT Included (Yet)

* Authentication / RBAC
* Multi-tenant isolation
* Billing / quotas
* CI/CD integrations

These will be added **after** core stability.

---

## Final Notes

* The platform is **already stable and functional**
* Upcoming work is **feature expansion**, not refactoring
* WebSocket terminal is the **execution authority**
* REST APIs are **control and metadata only**

---
