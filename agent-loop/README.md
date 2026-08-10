# Havi Agent Loop

Dev-only loop that reads `roadmap.json`, calls a provider one task at a time, and
writes checkpoints to `memory.json`. This loop is not part of the FastAPI/Celery
production runtime.

## Safe Dry Run

```bash
npm run loop
```

If `agent-loop/roadmap.json` does not exist, the script creates it from
`roadmap.example.json`. Dry-run mode does not call a real provider and does not
spend tokens.

## Run With AI

Add at least one key to `apps/backend/.env`:

- `HAVI_GEMINI_API_KEY`
- `HAVI_ANTHROPIC_API_KEY`
- `HAVI_OPENAI_API_KEY`

Then run:

```bash
npm run loop:ai
```

By default this runs **1 task** and stops. Use this for daily work and token
control. This mode only plans/checkpoints; it does not edit files.

Run a bounded batch:

```bash
npm run loop:ai -- --task-limit 2
npm run loop:ai:3
npm run loop:ai:5
```

The default provider is `auto`: Gemini, then Anthropic, then OpenAI, depending on
which key is configured.

Force a provider:

```bash
npm run loop:ai -- --provider anthropic
npm run loop:ai -- --provider openai
npm run loop:ai -- --provider gemini
```

Limit both task count and total tokens:

```bash
python3 agent-loop/run_loop.py --execute --provider auto --task-limit 3 --max-total-tokens 50000
```

Do not make “run until token exhaustion” the default. If needed later, create a
separate mode with stricter guards: token budget, error budget, command allowlist,
and explicit confirmation before file edits or shell commands.

## Code Mode

Ask the agent to read `files_to_read`, create a patch, apply it with `git apply`,
and run the task’s `verify_commands`:

```bash
npm run loop:code -- --provider gemini --task-limit 1
```

Commit and push stay manual.

Before applying, the loop normalizes hunk counts and runs
`git apply --check --recount --whitespace=fix`. If a provider returns a patch
that is valid diff syntax but does not match the current files, the task is put
back to `pending` and the roadmap/memory record the patch path plus the git
diagnostic so the next run can retry instead of marking feature work completed
or failed incorrectly.

Create a patch without applying it:

```bash
npm run loop:patch -- --provider gemini --task-limit 1
```

Apply but skip verification:

```bash
npm run loop:code:no-verify -- --provider gemini --task-limit 1
```

Patches are saved to `agent-loop/patches/<task-id>.patch`. After a code run,
inspect `git diff`. Only sync/tick the Markdown roadmap when the patch has been
applied and genuinely verified.

## Roadmap Schema

The default roadmap is derived from `docs/product/ROADMAP.md` and split into
small founder-beta tasks. Edit `agent-loop/roadmap.json` to change local priority.

Required fields:

- `id`: stable task id.
- `title`: task title.
- `status`: `pending`, `in_progress`, `completed`, or `failed`.

Recommended fields:

- `priority`: `P0`, `P1`, or `P2`.
- `area`: backend/frontend/ops/product/security...
- `why`: why this task exists in the roadmap.
- `files_to_read`: files the agent should read before working.
- `acceptance_criteria`: completion criteria.
- `verify_commands`: commands to run after changes.
- `prompt`: task-specific instruction for the agent.

The script prioritizes an `in_progress` task first, then the first `pending` task.
Run one task and stop:

```bash
npm run loop:ai
```

`loop:ai` reads the roadmap, calls a provider, and writes results/checkpoints.
`loop:patch` asks the provider for a unified diff only. `loop:code` applies that
diff and runs verification. Commit and push remain manual.
