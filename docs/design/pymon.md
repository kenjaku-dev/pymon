# pymon — Design Document

## 1. Requirements

### Functional
- Monitor CPU, memory, disk, network, processes, sensors, GPU, system info.
- Refresh live data at configurable interval.
- Sort/filter processes; kill process with confirmation.
- Export snapshots (JSON/CSV).
- Configurable thresholds, columns, row cap, theme.

### Non-functional
- Linux-first; degrade gracefully when optional deps/tools absent.
- UI must not block on collection (background worker).
- Resilient to per-subsystem collection failures.

### Out of scope
- Remote/multi-host monitoring (future).
- Windows/macOS full support (best-effort).

## 2. High-level architecture
- `PymonApp` (Textual) owns UI and a `SystemCollector`.
- Worker thread collects `SystemSnapshot`; `_apply` updates widgets on UI thread.
- Panels are stateless renderers receiving `(snapshot, config)`.
- Config persisted to JSON.

## 3. Key trade-offs
- Single-process TUI vs client/server: simpler, lower overhead; no remote.
- In-memory history (sparklines) vs persistence: low memory, resets on restart.
- Cached system info (30s TTL) vs live: reduces overhead; uptime slightly stale.
- Per-panel isolation in `_apply`: minor overhead, prevents one widget failure from blocking others.

## 4. Failure modes
- Collection errors recorded in `snapshot.errors`; UI shows count.
- Optional GPU/disk/network failures don't crash app.
- `_collecting` guard prevents overlapping collections.
- Thread-safe collector via lock.

## 5. Data model
- `SystemSnapshot` aggregates subsystem dataclasses.
- `ProcessInfo` includes pid, ppid, cmdline, rss, etc.

## 6. Future
- Plugin entry points for collectors/panels.
- Remote monitoring agent.
- Cross-platform abstraction.