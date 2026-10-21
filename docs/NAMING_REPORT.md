# Naming Analysis Report — pymon

Scope: all Python source under `src/pymon/` and tests under `tests/`.

## Summary

- Items analyzed: ~180 (classes, functions, methods, variables, constants)
- Issues found: 19
- Critical: 0
- Major: 6
- Minor: 13

No misleading names that change behavior were found. Most issues are abbreviation/clarity and single-letter variables in non-trivial scopes.

---

## Major Issues (6)

### src/pymon/ui/panels.py — `CpuPanel.update_data`
**Current**: `st = _usage_style(c, thr).split()[0]`
**Issue**: `st` is an opaque abbreviation for "style".
**Suggestion**: `style = _usage_style(c, thr).split()[0]`
**Reason**: Full word improves readability.

### src/pymon/ui/panels.py — `MemoryPanel.update_data`
**Current**: `ss = _usage_style(m.swap_percent, thr).split()[0]`
**Issue**: `ss` abbreviation for swap style.
**Suggestion**: `swap_style = ...`
**Reason**: Disambiguates from `st`/`style`.

### src/pymon/collectors/system.py — `_collect_cpu`
**Current**: `la = psutil.getloadavg()`
**Issue**: `la` abbreviation for load average.
**Suggestion**: `load_avg = psutil.getloadavg()`
**Reason**: Matches the field name `CpuInfo.load_avg`.

### src/pymon/collectors/system.py — `_collect_memory`
**Current**: `vm = psutil.virtual_memory(); sm = psutil.swap_memory()`
**Issue**: `vm`/`sm` abbreviations.
**Suggestion**: `virtual_mem`, `swap_mem`
**Reason**: Clearer at a glance.

### src/pymon/app.py — `_selected_pid`
**Current**: `rk` for row key.
**Issue**: Abbreviation in a non-trivial scope.
**Suggestion**: `row_key`
**Reason**: Matches Textual's `RowKey` concept.

### src/pymon/app.py — `action_toggle_filter`
**Current**: `fb` for filter bar.
**Issue**: Abbreviation.
**Suggestion**: `filter_bar`
**Reason**: Clarity.

---

## Minor Issues (13)

- `thr` → `threshold` in panels/collector (minor, widely used).
- `t` → `text` in panel `update_data` methods (acceptable for short scope but repeated).
- `m` → `memory` in `MemoryPanel`.
- `n` → `iface`/`interface` in `NetworkPanel`.
- `d` → `disk`/`partition` in `DiskPanel`.
- `p` → `process` in collector loops (acceptable in small loops).
- `i`/`c` loop counters in `CpuPanel` per-core loop (acceptable).
- `io` → `disk_io` in `_collect_disk_io` (minor).
- `util` → `utilization` in `_collect_gpu` (AMD/NVIDIA).
- `mem_used_mb`/`mem_total_mb` are clear; keep.
- `cmdline` is clear.
- `process_tree` boolean lacks `is_` prefix, but follows project `show_*` convention.
- `_num` nested helper in `_collect_gpu_amd` is generic; rename to `_to_number`.

---

## Convention Notes

- Python `snake_case` for functions/variables and `PascalCase` for classes is followed consistently.
- Booleans use mixed prefixes (`show_all_interfaces`, `process_sort_desc`, `process_tree`). Project convention is acceptable, but consider `is_*` for new booleans.
- Constants (`_SPARK_BLOCKS`, `_PSEUDO_FS`) use `UPPER_SNAKE_CASE` correctly.
- Private helpers consistently use leading underscore.
- Well-known abbreviations (`pid`, `ppid`, `rss`, `cpu`, `mem`, `io`, `url`) are acceptable.

---

## Suggested Renaming (Priority)

### Medium (clarity)
1. `st` → `style` (`panels.py`)
2. `ss` → `swap_style` (`panels.py`)
3. `la` → `load_avg` (`system.py`)
4. `vm`/`sm` → `virtual_mem`/`swap_mem` (`system.py`)
5. `rk` → `row_key` (`app.py`)
6. `fb` → `filter_bar` (`app.py`)

### Low (convention)
1. `thr` → `threshold`
2. `util` → `utilization`
3. `_num` → `_to_number`

---

## Conclusion

Naming is generally consistent and follows Python conventions. No critical misleading names. Suggested changes are cosmetic and can be applied incrementally; none affect behavior.