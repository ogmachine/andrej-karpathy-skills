---
name: warn-debug-leftovers
enabled: true
event: file
conditions:
  - field: file_path
    operator: regex_match
    pattern: \.(js|jsx|ts|tsx|mjs|cjs|mts|cts|vue|svelte|astro)$
  - field: file_path
    operator: regex_match
    pattern: ^(?!(.*/)?(scripts?|bin|cli)/)(?!.*\.(test|spec)\.).*$
  - field: content
    operator: regex_match
    pattern: \bconsole\.(log|debug)\(|(^|\n)\s*debugger\b
---

**Debug output added to application code** (`console.log` / `debugger`).

If it's temporary, remove it before you report the task done. If the output should stay, use the project's logger instead so it can be filtered and silenced.
