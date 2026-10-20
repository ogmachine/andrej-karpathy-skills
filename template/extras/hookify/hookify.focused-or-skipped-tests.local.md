---
name: warn-focused-or-skipped-tests
enabled: true
event: file
conditions:
  - field: file_path
    operator: regex_match
    pattern: (\.(test|spec)\.[cm]?[jt]sx?$|(^|/)tests?/|(^|/)test_[^/]*\.py$|_test\.(py|go)$)
  - field: content
    operator: regex_match
    pattern: \b(it|test|describe|context)\.(only|skip)\(|\b(xit|xdescribe|fit|fdescribe)\(|@pytest\.mark\.(skip|xfail)|\bt\.Skip\(|@unittest\.skip
---

**A test is being focused or skipped** (`.only`, `.skip`, `xit`, `@pytest.mark.skip`, …).

`.only` silently disables every other test in the file. Skipping a failing test hides the failure. Neither one makes a task done. Fix the code, or fix the test if the test itself is wrong. If a skip really is intended, keep it and tell the user why, linking an issue.
