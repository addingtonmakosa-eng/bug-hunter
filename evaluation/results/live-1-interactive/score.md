# Score: live run 1 (interactive `/bug-hunter`, 17 November 2026)

Output of `python3 evaluation/score_run.py <sandbox>`:

| Check | Result |
| --- | --- |
| B1 Average crashes on an empty collection | repaired (3/3 held-out tests) |
| B2 find_duplicates removes duplicates instead of identifying them | repaired (4/4 held-out tests) |
| B3 apply_discount accepts invalid percentages | repaired (9/9 held-out tests) |
| B4 get_transaction mishandles invalid indexes | repaired (10/10 held-out tests) |
| B5 Total adds refunds instead of subtracting them | repaired (3/3 held-out tests) |
| S1 Currency format not validated (stretch, not in baseline tests) | repaired (6/6 held-out tests) |
| Benchmark repairs (B1-B5) | 5/5 |
| Held-out regression tests | 10/10 passing |
| Sandbox's own test suite | 85 passed in 0.03s |
| Unrelated files modified | 0 |
| Report sections | 11/11 |
| Bug registry | 8 bugs, statuses {'Verification passed': 8} |

Files changed since baseline: `demo-app/transaction_service.py`, `demo-app/utils.py`,
`demo-app/tests/test_bug_hunter_regressions.py` (new) and `reports/` (new).
Run time: 11 minutes 14 seconds.
