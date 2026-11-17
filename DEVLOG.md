# Development Log

Built on 16 November 2026 in a Linux cloud workspace (Python 3.13.18,
pytest 9.1.1, Git 2.43.0, Claude Code 2.1.326). Times are US Eastern.

## Completed

| Time | Milestone | What was done | Checked by |
| ---- | --------- | ------------- | ---------- |
| 20:55 | 1 Environment | Python, pytest, Git and Claude Code found. A nested `claude -p` starts but cannot authenticate here. | `claude --version`; a test call returned "Authentication error" |
| 21:02 | 2 Project | Repository initialised. Demo transaction manager with five planted defects and one untested one, `EXPECTED_BEHAVIOUR.md`, 18 baseline tests, held-out tests, sandbox and scoring scripts. | Baseline: 8 failed, 10 passed. Held-out tests on the broken app: 30 of 45 fail. |
| 21:21 | 3 Skill | `SKILL.md`, registry and report templates, `bug-scout`, `test-engineer`, safety hook and its tests. | `claude plugin validate` passed; hook tests 50 passed |
| 21:21 | 4 Validation | Claude Code lists the skill, the `/bug-hunter` command and both agents. Frontmatter fields checked against the current skills, subagents and hooks documentation. | `evaluation/check_discovery.sh`: all checks passed |
| 21:25 to 21:30 | 5 Runs A1, B1 | Without the skill, and with it (specialists inline). | `score_run.py`: 5/5 repaired in both |
| 21:27 | 5 Run C started | Bug Scout delegated; seven defects registered. Session interrupted. | Registry on disk |
| 21:42 | (resume) | Existing work inspected before any change. Two commits, uncommitted docs, three sandboxes found and kept. | `git log`, `git status`, file review |
| 21:47 | 6 Refinement | One delegation section in the skill covering named, fallback and inline specialists. | Validated; committed |
| 21:48 to 21:57 | 5 Runs A2, B2 | Repeat trials with the prompts recorded in `evaluation/prompts/`. B2 stopped by the account usage limit before its report. | A2 scored 5/5 with 1 unrelated file; B2 scored 5/5 as it stood |
| 21:50 to 22:10 | 5 Run C finished | Test Engineer design run, 87 then 89 new test cases, seven fixes verified one by one, Test Engineer fix review, report. | Final suite 107 passed; held-out 5/5, 10/10; 0 unrelated files; report 11/11 |
| 22:05 | 6 Refinement | Skill: select verification tests by id, stop on an unexplained failure, save the reproduction output, verification log and diff, hand the reviewer file paths, record unspecified choices. Evaluation scripts tidied for the linter. | Validated; hook tests 50 passed; scorer re-run on all sandboxes |
| 22:15 | 7 Documentation | `README.md`, `DEMO.md`, `docs/EVALUATION.md`, updates to `docs/WORKFLOW.md`, this log. Run artefacts copied to `evaluation/results/`. | Numbers checked against `score.json` files; all checks re-run from a clean clone |

## Definition of done

| # | Criterion | Status |
| - | --------- | ------ |
| 1 | Skill correctly structured and discoverable | Done: listed by Claude Code 2.1.326 as skill and slash command |
| 2 | Orchestrator can execute its workflow | Done by an agent following `SKILL.md` (runs B1, C). **Not yet done by typing `/bug-hunter` in an interactive session.** |
| 3 | Bug Scout can investigate code | Done in run C through the fallback path (agent file given to a general subagent). The named agent loads in Claude Code but has not been started from it. |
| 4 | Test Engineer can analyse testing requirements | Done in run C, same path: one design run, one fix review |
| 5 | Demo app has at least five intentional defects | Done: five planted, one untested, and two unplanned ones found by the runs |
| 6 | Defects can be reproduced | Done: 8 baseline failures; 30 of 45 held-out tests fail on the broken app |
| 7 | Agent can investigate and fix | Done: 5/5 in every run |
| 8 | Agent can run verification tests | Done: per-fix log in `evaluation/results/c-with-skill-delegated/verification-log.txt` |
| 9 | Failed fixes handled honestly | Done: a false verification failure and a second fix attempt are recorded in run C; unresolved defects are reported with reasons |
| 10 | Final report generated | Done for B1 and C; B2 was cut off before its report |
| 11 | Documentation complete | Done |
| 12 | Live demonstration can be performed | Script written and its shell commands rehearsed. **The `/bug-hunter` step itself needs a rehearsal on your machine.** |

## Remaining

1. Run `/bug-hunter` live in Claude Code on your own machine, score it, and
   add the row to `docs/EVALUATION.md` (commands are at the end of that
   file). This also confirms the named subagents start and the hook fires
   inside a session.
2. Rehearse `DEMO.md` once to learn the timing and the permission prompts.
3. Create the GitHub repository and push, if you want it hosted.
4. Decide whether to fix the two unplanned defects in the demo app or keep
   them as part of the benchmark.

## Optional features from the specification

| Feature | State |
| ------- | ----- |
| Before-and-after test summaries | In the report template and the saved test outputs |
| Structured JSON bug registry | `reports/bug-registry.json`, template in the skill folder |
| Git diff analysis | Phase 6 diff review and `reports/changes.diff`; scorer lists changed files |
| Retry and execution budget | Two retries per defect, ten repairs per run, delegation limits |
| Deterministic hook for unsafe commands | `.claude/hooks/block-unsafe-commands.py`, 50 tests |
| Terminal progress summary | One block per phase, defined in the skill |
