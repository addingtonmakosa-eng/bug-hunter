# Bug Hunter: Live Demonstration Script

A 10 to 12 minute walkthrough. Commands are in code blocks; what to say is in
plain text. Everything here was rehearsed against the committed state of this
repository, where the demo app is still broken.

## Before the audience arrives (5 minutes)

1. Open two terminals in the repository root, and the folder in VS Code.
2. Check the tools:

   ```bash
   python3 --version && python3 -m pytest --version && git --version && claude --version
   ```

3. Check that Claude Code can see the skill and both subagents:

   ```bash
   bash evaluation/check_discovery.sh
   ```

   Expected: six `ok` lines and `All discovery checks passed.`

4. Make a fresh, broken copy to run the demo in. This keeps the repository
   itself untouched and leaves out `docs/` and `evaluation/`, which describe
   the planted bugs:

   ```bash
   bash evaluation/make_sandbox.sh ~/bug-hunter-demo
   ```

   If `~/bug-hunter-demo` already exists from a rehearsal, use a new name
   such as `~/bug-hunter-demo-2`.

5. In terminal 2, start Claude Code in the sandbox so it is ready:

   ```bash
   cd ~/bug-hunter-demo && claude --permission-mode acceptEdits
   ```

   `acceptEdits` lets Claude Code edit files without a prompt for each edit; it
   still asks before running commands. The first time it asks to run the
   tests, choose **Yes, and don't ask again for: python3 -m pytest**. A full
   run took 11 minutes 14 seconds in rehearsal. To fit the slot, type
   `/bug-hunter` straight after Stage 1, then present Stages 2 and 5 while
   it works.

## Stage 1: The problem (1 minute)

Say:

> Debugging by hand is a loop: read the code, guess what is wrong, reproduce
> the failure, change something, run the tests, and repeat. Each step is
> manual, and it is easy to skip the ones that protect you, such as
> reproducing the bug before fixing it, or checking that the fix did not
> break something else.
>
> Bug Hunter turns that loop into a workflow that Claude Code runs on its
> own. You type one command. It inspects the repository, sends two specialist
> agents to investigate, reproduces each suspected bug before touching the
> code, fixes only what it has confirmed, re-runs the tests, and writes a
> report that separates what it found from what it proved.

## Stage 2: The broken application (2 minutes)

In terminal 1:

```bash
cd ~/bug-hunter-demo/demo-app
python3 app.py summary
```

Say: "A small transaction manager. The specification says the net total
should be 501.25 and there is one duplicate record. It prints 541.25 and 4."

```bash
python3 app.py --empty summary     # crashes: ZeroDivisionError
python3 app.py show 99             # crashes: IndexError
python3 app.py discount 200 150    # prints -100.00: a 150% discount is accepted
python3 -m pytest -q               # 8 failed, 10 passed
```

Open `demo-app/EXPECTED_BEHAVIOUR.md` in VS Code and say:

> The expected behaviour is written down separately from the code, so
> "correct" is objective. Five defects were planted: the average crashes on
> an empty collection, duplicate detection deletes records instead of
> reporting them, discounts accept invalid percentages, an invalid index
> crashes, and refunds are added to the total instead of subtracted. There
> is also a sixth that no test exposes, to see whether the agent reads the
> specification or only chases failing tests.

Do not open `transaction_service.py` yet. Let the agent find the lines.

## Stage 3: Run Bug Hunter (about 11 minutes)

In terminal 2, type:

```
/bug-hunter
```

Narrate each phase as its progress line appears
(`[Bug Hunter] Phase 2/7 ...`):

| Phase | Point out |
| ----- | --------- |
| 1 Reconnaissance | It runs `git status` and reads the manifests before anything else. Nothing is edited. It works out the language and test command instead of assuming Python. |
| 2 Discovery | The delegation to **bug-scout**. It runs in its own context with read-only tools and returns structured findings: file, lines, evidence, expected against actual, confidence. |
| 3 Reproduction | The baseline test run is saved first. **test-engineer** designs the reproduction tests. A suspicion only becomes *Confirmed* when a test fails as predicted and the expected result has a cited source. |
| 4 Root cause | It states why each line is wrong, and separates root causes from symptoms. |
| 5 Repair | One defect at a time, smallest change, no refactoring. |
| 6 Verification | After every fix: the reproduction test, then the full suite. This is the feedback loop. A failed fix gets two retries and is then reported as unresolved. At the end, **test-engineer** reviews the diff. |
| 7 Report | Written from the registry, not from memory. |

While it runs, open `reports/bug-registry.json` in VS Code and show a defect's
`status` and `history` changing.

If someone asks about safety, in terminal 1 run:

```bash
cd ~/bug-hunter-demo
echo '{"tool_name":"Bash","tool_input":{"command":"git reset --hard"}}' | python3 .claude/hooks/block-unsafe-commands.py; echo "exit code: $?"
```

It prints the block message and `exit code: 2`. Say: "Rules in a prompt are
followed with judgement. This hook runs before every shell command and
blocks a fixed list of destructive ones, whatever the model decides."

## Stage 4: The outcome (2 minutes)

Open `~/bug-hunter-demo/reports/bug-hunter-report.md` and show, in order:

1. The count row at the top: discovered, confirmed, fixed, verified,
   unresolved. Say: "These are four different claims, and the report keeps
   them apart."
2. **Root-Cause Analysis** for the duplicate bug.
3. **Before-and-After Comparison** and **Verification Results**.
4. **Remaining Issues**. Say: "It lists what it did not fix and why. An
   agent that reports only successes cannot be trusted."

Then confirm the result independently, in terminal 1:

```bash
cd ~/bug-hunter-demo/demo-app
python3 -m pytest -q                 # all tests pass
python3 app.py summary               # net total 501.25, 1 duplicate
python3 app.py --empty summary       # no crash
cd .. && git status --short && git diff --stat baseline
```

Say: "Two source files changed, one test file was added, and the reports.
Nothing else."

Finally, score the run with tests the agent never saw. Run this from the
Bug Hunter repository:

```bash
python3 evaluation/score_run.py ~/bug-hunter-demo
```

## Stage 5: The architecture (2 minutes)

Open the diagram in `README.md` or `docs/ARCHITECTURE.md`, and explain the
five ideas:

| Idea | One-sentence explanation | Where to point |
| ---- | ------------------------ | -------------- |
| Conventional prompt | A one-off instruction: it lives in one conversation, and the process it describes is retyped, and varies, every time. | The single sentence in `evaluation/prompts/task.txt` |
| Reusable skill | The same process saved as a file in the repository, so anyone on the project gets it by typing `/bug-hunter`, and it can be versioned and reviewed like code. | `.claude/skills/bug-hunter/SKILL.md` |
| Specialist subagent | A separate Claude with its own context window, its own instructions and a restricted tool list, so the investigator cannot edit code and its reading does not fill the orchestrator's context. | `.claude/agents/bug-scout.md`, the `tools: Read, Grep, Glob` line |
| Autonomous multi-step workflow | Seven phases the agent moves through by itself, deciding what to do next from what it found, with state kept in a registry file. | `reports/bug-registry.json` |
| Verification feedback loop | Every fix is tested, and a failure sends the agent back to re-examine the cause, at most twice, before it must report the defect as unresolved. | Phase 6 in `SKILL.md` |

Close with the honest result from `docs/EVALUATION.md`: on this small
application Claude Code repaired all the planted defects with and without
the skill. What the skill changed was the process and the evidence: a saved
baseline, a reproduction for every claim, smaller diffs, a registry, and a
complete report.

## If something goes wrong

| Problem | What to do |
| ------- | ---------- |
| `/bug-hunter` is not recognised | You are not in a directory that contains `.claude/skills/bug-hunter/`. `cd` into the sandbox and restart `claude`. |
| Claude says `bug-scout` or `test-engineer` does not exist | Restart Claude Code in the sandbox. The skill also has a fallback: it gives the agent file to a general subagent, or does the work itself, and says which in the report. |
| The run is too slow for the slot | Narrow it: `/bug-hunter demo-app find_duplicates only`. Or show a recorded run in `evaluation/results/`. |
| Too many permission prompts | Start with `claude --permission-mode acceptEdits`, and choose "don't ask again" for the pytest command. |
| You need to start over | Make a new sandbox with a new name. The repository's own `demo-app/` is never modified by the demo. |

## Likely questions

- **Is it only for Python?** The workflow detects the language and test
  command from the repository. Only the Python demo has been evaluated.
- **Does it always succeed?** No. The targets in `docs/EVALUATION.md` are
  targets. Defects it cannot reproduce or cannot fix within two retries are
  reported as unresolved.
- **What stops it doing damage?** Read-only specialists, Claude Code's own
  permission prompts, the skill's rules, and the hook. The hook is a
  deny-list, so it is a backstop and not a guarantee.
- **Why not one big prompt?** Compare `evaluation/prompts/task.txt` with the
  report sections and the registry: the one-line prompt fixed the bugs but
  left no baseline, no registry and a report with its own structure.
