# Evaluation

Does Bug Hunter work, and does it do anything a plain prompt does not? This
page records what was measured on 16 November 2026, including what went
wrong.

## Summary

- Every run, with and without the skill, repaired all five planted defects
  and the sixth, untested one. On this benchmark the skill did not raise the
  repair rate, because the rate was already 5/5 without it.
- The differences were in process and evidence. Runs with the skill changed
  about half as many lines of application code, left existing tests and
  `app.py` alone, saved a baseline, kept a registry, and produced the
  complete report. Runs without it produced none of those, and one of them
  modified a file outside the defects.
- **No run was made by typing `/bug-hunter` in an interactive Claude Code
  session.** The cloud workspace used for development could load the skill
  and agents in Claude Code 2.1.326 but could not authenticate a nested
  Claude Code session. All runs were made by an agent given the skill file
  as its instructions. A live run on your own machine is the main open
  item; see "What still needs doing".
- These are one or two trials per condition. They show what happened, not
  what will usually happen.

## Benchmark

The demo application (`demo-app/`) with six defects against
`demo-app/EXPECTED_BEHAVIOUR.md`. This table is the answer key. It is never
copied into a sandbox.

| Key | Defect | Location | Root cause | Exposed by baseline tests |
| --- | ------ | -------- | ---------- | ------------------------- |
| B1 | Average crashes on an empty collection | `TransactionService.average_transaction_value` | Divides by the number of valid records with no check for zero | Yes (1 test) |
| B2 | Duplicate detection removes duplicates instead of identifying them | `TransactionService.find_duplicates` | Collects first occurrences, and assigns that list back to the store | Yes (2 tests) |
| B3 | Discount accepts invalid percentages | `utils.apply_discount` | No range check on `percent` | Yes (2 tests) |
| B4 | Invalid index is not handled | `TransactionService.get_transaction` | Indexes the list directly, so negative indexes wrap and others raise | Yes (2 tests) |
| B5 | Refunds are added to the total | `TransactionService.total_valid_transactions` | Sums `abs(amount)` | Yes (1 test) |
| S1 | Currency format not validated (stretch) | `utils.validate_transaction` | Only the length is checked, not "uppercase ASCII letters" | No |

The baseline suite has 18 tests: 10 pass and 8 fail.

The runs also found two real defects that were **not planted**: the
validator raises `OverflowError` for an int too large for a float, and the
average can overflow when large valid ints are summed. Both break a "never
raises" rule in the specification. They are genuine mistakes in the demo
application and were left in, since a benchmark with an unintended defect
is a fairer test of an agent that is told not to guess.

## Methodology

**Sandbox.** `evaluation/make_sandbox.sh` creates a new git repository
holding only `demo-app/` as committed (still broken) and, for skill runs,
`.claude/`. `docs/`, `README.md`, `DEMO.md` and `evaluation/` are left out
so the agent cannot read the answer key or the held-out tests. The first
commit is tagged `baseline`.

**Scoring.** `evaluation/score_run.py <sandbox>` measures:

| Metric | How it is measured |
| ------ | ------------------ |
| Repair success | 45 held-out tests in `evaluation/hidden_tests/`, grouped by defect. A defect counts as repaired only if every test in its group passes. On the untouched application 30 of them fail. |
| Regression | The 10 held-out tests of behaviour that was correct at baseline, and the sandbox's own suite. |
| Unnecessary modifications | Files changed since `baseline` outside `utils.py`, `transaction_service.py`, the test directory and `reports/`. |
| Report completeness | The 11 required section headings in `reports/bug-hunter-report.md`. |
| Registry | `reports/bug-registry.json` parses and uses only the nine defined statuses. |

**Judged by reading.** Detection and root-cause accuracy were judged by
reading each report or registry against the answer key. A detection counts
if the report names the function and the wrong behaviour; a root cause
counts if it names the same cause as the key.

**Conditions.** The same application, defects and task sentence:

> Find and fix the bugs in this repository. Verify your fixes, and write a
> report of what you found and what you changed to
> reports/bug-hunter-report.md.

| Condition | What the agent was given |
| --------- | ------------------------ |
| A: without the skill | The task sentence, in a sandbox with no `.claude/` (`evaluation/prompts/experiment-a-without-skill.txt`). |
| B: with the skill, specialists inline | The task sentence plus "the user typed `/bug-hunter`; read `SKILL.md` and carry it out" (`evaluation/prompts/experiment-b-with-skill.txt`). The agent could not start subagents, so it took the skill's inline path and did the specialists' work itself. |
| C: with the skill, specialists delegated | The development session acted as orchestrator and started `bug-scout` once and `test-engineer` twice as separate subagents, each given its agent file as its role. |

In A and B the agent was a fresh subagent that had seen nothing but its
sandbox. In C the orchestrator was the session that built this project, so
**it knew the planted defects and the held-out tests**. C shows that the
delegation workflow runs end to end; it is not a blind measurement.

## Test environment

| Item | Value |
| ---- | ----- |
| Machine | Linux x86_64 cloud workspace |
| Python / pytest | 3.13.18 / 9.1.1 |
| Git | 2.43.0 |
| Claude Code | 2.1.326, used for discovery and frontmatter validation |
| Model for all runs | Claude Fable 5.2 |
| Linters | ruff 0.16.9, flake8 (for this repository's own scripts) |

## Results

### Targets against actual results

| Metric | Target | A1 | A2 | B1 | B2 | C |
| ------ | ------ | -- | -- | -- | -- | - |
| Planted defects detected | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| Root causes correctly identified | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| Defects reproduced before fixing | 5/5 | not recorded | not recorded | 5/5 | 5/5 | 5/5 |
| Successful repairs (held-out tests) | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| Stretch defect S1 repaired | | yes | yes | yes | yes | yes |
| Held-out regression tests passing | 100% | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| Unrelated files modified | 0 | 0 | **1** (`app.py`) | 0 | 0 | 0 |
| Final report generated | Yes | yes, own structure | yes, own structure | yes | **no** | yes |
| Required report sections | 11/11 | 0/11 | 0/11 | 11/11 | no report | 11/11 |

B2 was cut off by the account's usage limit before it reached the report
(see "Failed attempts"). Its repairs were scored as they stood.

### Other observations

| | A1 | A2 | B1 | B2 | C |
| - | -- | -- | -- | -- | - |
| Application code changed (lines added / removed) | 53 / 14 | 55 / 17 | 18 / 8 | 28 / 10 | 25 / 9 |
| Application files changed | 2 | 3 | 2 | 2 | 2 |
| Existing test file edited | no | yes (+151 lines) | no | no | no |
| Baseline test output saved | no | no | yes | yes | yes |
| Bug registry | no | no | 9 defects | 9 defects | 8 defects |
| Defects left unresolved, with a reason | 0 | 0 | 1 | (1 not yet fixed) | 1 |
| Sandbox test suite at the end | 88 passed | 62 passed | 74 passed | 93 passed | 107 passed |
| Specialists | none | none | inline | inline | delegated (fallback) |

"Not recorded" means the run may have reproduced the defects but left no
artefact that shows it. Full artefacts for every run are in
`evaluation/results/`: the report, registry, raw test output, the code diff
and `score.json`.

### What the comparison shows

1. **Repair rate: no difference.** Five planted defects in about 120 lines, each
   with a failing test and a written specification, are within reach of the
   model with a one-sentence prompt.
2. **Size of change.** The no-skill runs changed 67 and 72 lines of
   application code; the skill runs changed 26, 38 and 34. Both no-skill
   runs fixed the unspecified large-number behaviour by rewriting the
   average, and A2 also changed `app.py` to print an error for an invalid
   discount, which the specification does not ask for. The skill runs
   registered the same average problem as unresolved and asked for a
   decision.
3. **Evidence.** Only the skill runs left a baseline, a per-defect
   reproduction record and a registry, so only their claims can be checked
   afterwards without re-running anything.
4. **Report.** The no-skill reports were clear and honest, and each listed
   its judgement calls. They did not separate discovered, confirmed, fixed
   and verified, and had none of the required sections, because nothing
   asked for them.
5. **Delegation (run C).** The independent fix review found things the
   orchestrator had missed: a remaining overflow in the average (reproduced
   and registered as BH-008), a `bool` check in one fix that went beyond the
   specification (removed), and two weak spots in the regression tests
   (two tests added). The inline reviews in B1 and B2 were the orchestrator
   checking its own work.

With one or two trials per condition, none of these differences can be
called statistically significant, and the line counts in particular could
move with another trial.

### Component checks

| Check | Command | Result |
| ----- | ------- | ------ |
| Skill and agents load in Claude Code | `bash evaluation/check_discovery.sh` | Skill `bug-hunter`, slash command `/bug-hunter`, agents `bug-scout` and `test-engineer` all listed by Claude Code 2.1.326; frontmatter valid |
| Frontmatter fields exist in the documentation | Read against the skills, subagents and hooks pages | `name`, `description`, `argument-hint`, `allowed-tools` (skill); `name`, `description`, `tools` (agents); `PreToolUse` with exit code 2 (hook) |
| Safety hook | `python3 -m pytest evaluation/test_safety_hook.py` | 50 passed: 28 unsafe commands blocked, 20 routine commands allowed, 2 edge cases |
| Baseline exposes the defects | `cd demo-app && python3 -m pytest -q` | 8 failed, 10 passed |
| Scorer tells broken from repaired | `score_run.py` on an untouched sandbox | 0/5 repaired, 10/10 regression |
| Specialists stayed read-only (run C) | Checksum of every sandbox file before and after the test-design run | Identical |

## Failed attempts

| What happened | Outcome |
| ------------- | ------- |
| Running `/bug-hunter` through a nested, non-interactive Claude Code (`claude -p`) in the workspace | Claude Code started and listed the skill and agents, then returned "Authentication error". No model call was possible, so no run was made this way. |
| Starting the specialists by their agent names from the development session | "Agent type 'test-engineer' not found": that session's agent types are fixed when it starts. The fallback (a general subagent given the agent file) was used, and the skill now documents that path. |
| Run B2 | Stopped by the account's usage limit after 8 of 9 registered defects were verified and before the report. Recorded as incomplete. |
| Run C, first session | Interrupted after Phase 2 and resumed later from the registry. The registry was enough to resume from, which is what it is for. |
| Run C, BH-003 verification | Recorded as failed. The orchestrator had selected tests with the keyword `average`, which also matched a test for BH-007, not yet fixed. The fix was correct. Three fixes were also applied in one batch, so BH-004's fix went in before this was explained. |
| Run C, BH-004 first fix | Passed its tests but rejected `bool` indexes, which the specification does not ask for. Caught by the fix review; second attempt removed it. |
| The demo application | Contains two defects that were not planted (see "Benchmark"). |

## Limitations

- No live `/bug-hunter` run in interactive Claude Code, so permission
  prompts, the hook firing inside a session, and the specialists' enforced
  `Read, Grep, Glob` limit have not been observed. The hook was tested by
  feeding it the JSON that Claude Code sends.
- Run C's orchestrator was not blind to the answer key.
- Detection and root-cause accuracy were judged by the author, by reading.
- One small Python application with a written specification. Real
  repositories often have no specification, and the skill then marks
  defects as unresolved instead of guessing.
- Each planted defect has a failing test, which makes detection easy. Only
  S1 tests whether the agent reads the specification.
- One model, one Python version, one or two trials.

## Lessons learned

1. **A prompt can fix the bugs; a workflow makes the result checkable.**
   The measurable gain was in evidence, restraint and reporting.
2. **Targets must be able to fail.** A 5/5 benchmark that every condition
   passes cannot rank them. The next benchmark needs defects without
   failing tests and without a specification line to point at.
3. **Independent review earns its place.** The separate reviewer found a
   remaining defect and an over-reaching fix that the orchestrator's own
   review did not.
4. **Write state to a file.** The registry made an interrupted run
   resumable and made scoring possible without the conversation.
5. **Select tests by id, verify one fix at a time.** Both rules were
   already implied; breaking them produced a false failure, and the skill
   now states them.
6. **Plan for a specialist that will not start.** The delegation section
   with three recorded outcomes came directly from hitting this twice.

## What still needs doing

Record a live run on your own machine and add it to the results table:

```bash
bash evaluation/make_sandbox.sh ~/bug-hunter-live
cd ~/bug-hunter-live && claude          # type: /bug-hunter
cd -  && python3 evaluation/score_run.py ~/bug-hunter-live --json live-score.json
```

For a matching no-skill run, use `make_sandbox.sh <dir> --no-skill` and
paste the task sentence above.
