---
name: warn-python-breakpoints
enabled: true
event: file
conditions:
  - field: file_path
    operator: regex_match
    pattern: \.py$
  - field: content
    operator: regex_match
    pattern: \bbreakpoint\(\)|\bpdb\.set_trace\(|(^|\n)\s*import i?pdb\b
---

**A Python breakpoint was added** (`breakpoint()` / `pdb`).

It will hang tests and CI waiting for input. Remove it before running the suite or reporting the task done.
