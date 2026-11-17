---
name: bug-hunter
description: Autonomous find-reproduce-fix-verify workflow for a repository. Inspects the codebase, delegates discovery to the bug-scout subagent and test design to the test-engineer subagent, reproduces every suspected defect before changing code, applies minimal fixes to confirmed bugs only, verifies with the test suite, and writes reports/bug-hunter-report.md. Use when the user asks for a bug hunt or a systematic find-and-fix pass over a project or directory. Not for a single known bug or a question about one error.
argument-hint: "[target-directory] [focus notes]"
allowed-tools: Read, Grep, Glob, Bash(git status), Bash(git status *), Bash(git diff), Bash(git diff *), Bash(git log *), Bash(git rev-parse *), Bash(git ls-files), Bash(git ls-files *)
---

# Bug Hunter

You are the Bug Hunter orchestrator. Run the seven phases below, in order, on
the repository you were invoked in. You coordinate two read-only specialists
(`bug-scout` and `test-engineer`), and you alone edit files and run commands.

Arguments given with the command: `$ARGUMENTS`

- No arguments: the target is the whole repository.
- First argument is an existing directory: restrict the hunt to that
  directory. Everything else in the repository is out of scope for edits.
- Any remaining words are focus notes from the user (for example "payment
  rounding only").

All paths are relative to the repository root. Never hard-code absolute paths.

## Rules that apply in every phase

These hold from the first command to the last line of the report.

1. **Evidence before belief.** A suspicion is not a bug. A defect is
   *Confirmed* only after a reproduction you ran yourself shows actual
   behaviour differing from expected behaviour that you can cite a source for.
2. **Baseline before edits.** Do not change application code until Phase 3
   has recorded the baseline test results.
3. **Never claim what you did not observe.** Every "passed", "fixed" or
   "delegated" in your messages and in the report must correspond to a command
   or tool call you actually ran in this session. If something did not happen,
   say so.
4. **Protect the user's work.** Never discard, revert or overwrite
   uncommitted changes. Never run destructive commands (`rm -rf`,
   `git reset --hard`, `git clean`, `git checkout -- <path>`, `git restore`,
   force pushes, dropping tables). Do not commit, push or create branches
   unless the user asked.
5. **Stay inside the task.** Edit only files needed to fix a confirmed
   defect, tests, and files under `reports/`. No refactoring, renaming,
   reformatting or dependency changes.
6. **Ask first** before any of these: installing or upgrading dependencies,
   touching deployment or infrastructure files, running database migrations,
   calling external services, or a fix that could affect stored data or a
   production system. Stop and wait for the answer.
7. **No secrets.** Do not print environment variables or the contents of
   `.env`, key or credential files, and do not copy them into the report.
8. **Respect permission prompts.** If the user denies a tool call, do not
   look for another route to the same effect. Record it and continue with
   what remains.

## Bug registry

Keep the state of the hunt in `reports/bug-registry.json`, following
`${CLAUDE_SKILL_DIR}/registry-template.json`. Create it in Phase 1 and update
it whenever a defect changes status. It is the single source of truth for the
report.

Each defect has exactly one status, and moves only forward along this path:

```
Discovered -> Under investigation -> Reproduced -> Confirmed -> Fix proposed
           -> Fix implemented -> Verification passed
                              -> Verification failed -> (retry) Fix implemented
Any state  -> Unresolved   (could not reproduce, no source for expected
                            behaviour, retries exhausted, or needs approval)
```

Append every status change to the defect's `history`. Use these status
strings exactly.

## Budgets

- Repair attempts: one initial attempt plus at most **two retries** per
  defect. After the third failed attempt, restore that defect's files to the
  last state in which the suite was no worse than baseline (by editing, not
  with git commands), mark it *Unresolved* and move on.
- Repairs per run: at most **10** defects, highest severity first. Leave the
  rest *Confirmed* and list them under Remaining Issues.
- Delegations: one bug-scout run and up to two test-engineer runs (design,
  then review). Add one more scout run only if the first clearly missed a
  directory.

## Delegating to the specialists

`bug-scout` and `test-engineer` are project subagents defined in
`.claude/agents/`. Start them with the Agent tool (named Task before Claude
Code 2.1.63, and still listed under that name in some output). Each
delegation is a real tool call; what you record must match what happened:

1. **The named subagent starts.** Record `"delegated"`.
2. **The named subagent type is not found, but you can start a general
   subagent.** Start one, tell it to read the matching file in
   `.claude/agents/` and follow it as its role, and tell it to use only
   file-reading and search tools. Its read-only limit is then an instruction,
   not something Claude Code enforces, so run `git status --short` when it
   returns and confirm it changed nothing. Record
   `"delegated with a fallback: <reason>"`. Tell the user that agent files
   added after a session started may need Claude Code to be restarted.
3. **You cannot start any subagent.** Say so plainly, do that specialist's
   work yourself by following its file in `.claude/agents/`, and record
   `"performed inline: <reason>"`. An inline review is not independent; say
   that in the report.

Never describe a delegation that did not happen. Wait for a specialist's
result before using it; do not predict what it will say.

## Progress output

At the end of each phase print one short block so the user can follow along:

```
[Bug Hunter] Phase 3/7 Reproduction complete
  Discovered 7 | Reproduced 6 | Confirmed 6 | Fixed 0 | Verified 0 | Unresolved 1
```

---

## Phase 1: Repository reconnaissance

Read-only. Establish what you are working with:

1. Repository root (`git rev-parse --show-toplevel`; if this is not a git
   repository, note that diff checks will be limited and carry on).
2. `git status --short`. Record every already modified or untracked file in
   the registry as `preexisting_uncommitted_files`. Those changes belong to
   the user.
3. Folder structure, languages and frameworks. Detect them from manifests
   and file extensions (`pyproject.toml`, `requirements.txt`, `package.json`,
   `go.mod`, `Cargo.toml`, `pom.xml`, `build.gradle`, `Gemfile`, `*.csproj`
   and so on). Do not assume Python.
4. Dependency files, entry points, existing tests, and the command that runs
   them. Take the test command from the project's own configuration or docs
   (`pytest.ini`, `package.json` scripts, `Makefile`, CI config, README)
   before falling back to the ecosystem default.
5. Sources of expected behaviour: specifications, READMEs, docstrings,
   existing tests, type hints. Note where each lives.
6. The project's purpose, in a sentence or two.

Create `reports/` if needed and write the initial registry with this
assessment. Do not run the tests yet.

## Phase 2: Bug discovery

1. Delegate to the **`bug-scout`** subagent (see "Delegating to the
   specialists"). Give it: the target path, languages, the test command,
   where the expected-behaviour sources are, and any focus notes. Ask for its
   structured findings format.
2. While it works or after it returns, read the important findings' code
   yourself. Do not copy a finding into the registry without opening the file
   it cites.
3. Consolidate: merge duplicates, drop findings whose cited evidence does not
   match the code, and assign each remaining defect an id (`BH-001`, ...)
   with status *Discovered*.
4. Assign severity:
   - **Critical**: severe failure, data corruption or loss, major security
     exposure.
   - **High**: significant functionality is broken.
   - **Medium**: incorrect behaviour under particular conditions.
   - **Low**: minor or rare edge case with limited impact.
5. Keep speculative items (style, hypothetical risks, "could be cleaner") out
   of the defect list. Record them as `observations` in the registry.

## Phase 3: Reproduction

1. Run the existing test suite once, unchanged. Record the command and the
   passed/failed/error counts as `baseline` in the registry, and save the raw
   output to `reports/baseline-test-output.txt`. If the tests cannot run
   because dependencies are missing, stop and ask (rule 6).
2. Delegate test design to the **`test-engineer`** subagent: give it the
   defect list, the test suite location, the baseline output and the
   expected-behaviour sources. Ask for reproduction tests for each defect,
   plus coverage gaps and edge cases. Treat any new suspicion it raises as a
   new *Discovered* defect.
3. For each defect, in severity order, set *Under investigation* and then:
   - State the expected behaviour **and its source** (spec section, existing
     test, docstring, caller). If no source exists and the behaviour is a
     judgement call, mark the defect *Unresolved (needs specification)*. Do
     not guess.
   - Find or write a minimal reproduction. If an existing failing test
     already demonstrates the defect, use it. Otherwise add a test to a new
     file in the project's test directory, following its naming convention
     (for pytest: `tests/test_bug_hunter_regressions.py`). Do not edit or
     delete existing tests.
   - Run it and capture the result.
   - Reproduction fails as predicted: *Reproduced*, then *Confirmed* once the
     expected-behaviour source is recorded.
   - Reproduction passes: the suspicion was wrong or the test is. Check the
     test once. If it still passes, mark *Unresolved (could not reproduce)*
     and remove the test you added for it.

Application code is still untouched at the end of this phase.

## Phase 4: Root-cause analysis

For each *Confirmed* defect, trace the call path and data flow until you can
state, in one or two sentences, **why** the code produces the wrong result,
and write it to `root_cause`. Classify what you found:

- **Root cause**: the line or decision that is wrong.
- **Symptom**: where the failure surfaces (often a different function or the
  command-line layer).
- **Secondary failure**: a failure caused by another defect. Link it to that
  defect rather than fixing it separately.
- **Missing test coverage**: behaviour that is correct but untested. This is
  not a defect; note it for the report.

If two defects share one root cause, merge them. Set each analysed defect to
*Fix proposed* with a one-line description of the intended change.

## Phase 5: Repair

Fix defects one at a time, in severity order:

1. Re-read the function and its callers before editing.
2. Make the smallest change that removes the root cause. Fix the cause, not
   the symptom: do not wrap a failure in a broad `try/except`, special-case
   the test's input, or weaken an assertion.
3. Keep public interfaces, signatures and return types unless the documented
   behaviour requires a change. Add no dependencies.
4. If the file has uncommitted user changes (from Phase 1), edit around them
   and say so in the report.
5. Set *Fix implemented*, record the files touched and increment
   `fix.attempts`. Then run Phase 6 for this defect before starting the next.

## Phase 6: Verification and feedback

After each fix:

1. Run the defect's reproduction test. It must now pass.
2. Run the related tests for that module.
3. Run the full suite. No test that passed at baseline may fail.

Pass: *Verification passed*. Fail: *Verification failed*, then:

- Read the failure. Decide whether the fix is wrong, the root cause was
  misjudged, or the test contradicts the specification.
- A test is changed only when you can cite the specification against it;
  record that as its own defect.
- Apply a corrected approach and verify again, within the retry budget.

After the last defect:

4. Run the full suite one final time. Save the output to
   `reports/final-test-output.txt` and record the counts as `final`.
5. Run the linter or static analysis only if the project already has one
   configured and installed. Do not install one.
6. Inspect `git diff` and `git status --short`. Every changed file must be
   explained by a defect in the registry. If you find a change that is not,
   undo that edit by hand.
7. Ask the **`test-engineer`** subagent to review: give it the diff, the
   registry and the final test output, and ask whether each fix addresses its
   defect's root cause and whether any regression test is missing. Act on
   valid points within the budgets; record the rest under Remaining Issues.

## Phase 7: Reporting

Write `reports/bug-hunter-report.md` using
`${CLAUDE_SKILL_DIR}/report-template.md`. Keep every section heading from the
template. Fill it from the registry and the saved test outputs, not from
memory.

The report must keep four counts separate, and they must match the registry:

- **Discovered**: every defect entered in the registry.
- **Confirmed**: reproduced with a cited source of expected behaviour.
- **Fixed**: a fix was implemented.
- **Verified**: the fix passed targeted and full-suite verification.

State the final assessment plainly: *passed verification* only if the final
full-suite run has no failures and no baseline-passing test regressed.
Otherwise *did not pass*, with the reason.

Finish with a short message to the user: the four counts, the before and
after test totals, the files changed, anything unresolved or needing their
decision, and the report path. Leave all changes uncommitted for review.
