| S.No | Pending Item                             | Description                                                           | Priority |
| ---: | ---------------------------------------- | --------------------------------------------------------------------- | -------- |
|    1 | Runtime Repository (DB-backed)           | Replace in-memory `runtime_registry` with Tortoise ORM repository     | High     |
|    2 | Docker ↔ DB Reconciliation on Startup    | On FastAPI startup, sync DB runtimes with existing Docker containers  | High     |
|    3 | Update `docker_manager` to Use DB        | Persist container name, status, image in PostgreSQL instead of memory | High     |
|    4 | Update `executor` to Update DB           | Store `last_command`, update runtime status in DB after exec          | High     |
|    5 | Remove In-Memory Registry Completely     | Delete `runtime_registry` and all references                          | High     |
|    6 | Auto-Reattach Existing Containers        | If container exists, reattach runtime from DB instead of recreating   | Medium   |
|    7 | Runtime Auto-Start on Exec (Optional UX) | If exec called and runtime stopped, auto-start it                     | Medium   |
|    8 | WebSocket Terminal Backend               | Interactive terminal with PTY, stdin/stdout streaming                 | Medium   |
|    9 | Long-Running Process Handling            | Support `npm run dev`, `uvicorn`, background processes                | Medium   |
|   10 | Docker Security Hardening                | Non-root user, CPU/RAM limits, no-new-privileges                      | Medium   |
|   11 | Command Presets API                      | Backend-defined safe presets (Install, Build, Run)                    | Low      |
|   12 | Runtime Cleanup Job                      | Periodic cleanup of orphaned containers                               | Low      |
|   13 | DB Migrations Strategy                   | Introduce Aerich for schema migrations                                | Low      |
|   14 | Admin Runtime Dashboard APIs             | List all runtimes, status, health                                     | Low      |
