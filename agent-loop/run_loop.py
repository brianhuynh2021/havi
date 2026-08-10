#!/usr/bin/env python3
"""Bounded dev agent loop for Havi.

This script is intentionally bounded: it calls an LLM for one roadmap task at a
time, records checkpoints, and only applies patches/runs verify commands when
explicitly requested.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROADMAP = ROOT / "agent-loop" / "roadmap.json"
DEFAULT_ROADMAP_EXAMPLE = ROOT / "agent-loop" / "roadmap.example.json"
DEFAULT_MEMORY = ROOT / "agent-loop" / "memory.json"
DEFAULT_ENV_FILE = ROOT / "apps" / "backend" / ".env"

TASK_STATUSES = {"pending", "in_progress", "completed", "failed"}
PROVIDERS = ("gemini", "anthropic", "openai")
DEFAULT_PROVIDER_ORDER = PROVIDERS
DEFAULT_CONTEXT_CHARS_PER_FILE = 40_000
DEFAULT_CONTEXT_TOTAL_CHARS = 160_000


class PatchApplyFailed(Exception):
    pass


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def load_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        if default is None:
            raise FileNotFoundError(f"File not found: {path}")
        return default
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def ensure_default_roadmap(path: Path) -> None:
    if path.exists() or path != DEFAULT_ROADMAP:
        return
    roadmap = load_json(DEFAULT_ROADMAP_EXAMPLE)
    save_json(path, roadmap)
    print(f"Created default roadmap: {path}")


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def validate_roadmap(roadmap: dict[str, Any]) -> None:
    if not isinstance(roadmap.get("project"), str) or not roadmap["project"].strip():
        raise ValueError("roadmap.json must include a non-empty string field `project`.")

    tasks = roadmap.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("roadmap.json must include a non-empty `tasks` list.")

    seen_ids: set[str] = set()
    for index, task in enumerate(tasks, start=1):
        if not isinstance(task, dict):
            raise ValueError(f"Task #{index} must be an object.")
        task_id = str(task.get("id", "")).strip()
        title = str(task.get("title", "")).strip()
        status = str(task.get("status", "")).strip()
        if not task_id:
            raise ValueError(f"Task #{index} is missing `id`.")
        if task_id in seen_ids:
            raise ValueError(f"Duplicate task id: {task_id}")
        if not title:
            raise ValueError(f"Task {task_id} is missing `title`.")
        if status not in TASK_STATUSES:
            raise ValueError(
                f"Task {task_id} has status `{status}`; expected one of {sorted(TASK_STATUSES)}."
            )
        seen_ids.add(task_id)


def select_task(tasks: list[dict[str, Any]]) -> dict[str, Any] | None:
    for task in tasks:
        if task["status"] == "in_progress":
            return task
    for task in tasks:
        if task["status"] == "pending":
            return task
    return None


def read_task_context(task: dict[str, Any]) -> list[dict[str, str]]:
    context: list[dict[str, str]] = []
    remaining = DEFAULT_CONTEXT_TOTAL_CHARS

    for raw_path in task.get("files_to_read", []):
        if remaining <= 0:
            break

        path = (ROOT / raw_path).resolve()
        try:
            path.relative_to(ROOT)
        except ValueError:
            context.append({"path": str(raw_path), "error": "path is outside the repo"})
            continue

        if not path.exists():
            context.append({"path": str(raw_path), "error": "file does not exist"})
            continue
        if path.is_dir():
            context.append({"path": str(raw_path), "error": "path is a directory; use a file path"})
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            context.append({"path": str(raw_path), "error": "not UTF-8 text"})
            continue

        clipped = text[: min(DEFAULT_CONTEXT_CHARS_PER_FILE, remaining)]
        remaining -= len(clipped)
        context.append(
            {
                "path": str(raw_path),
                "content": clipped,
                "truncated": str(len(text) > len(clipped)).lower(),
            }
        )

    return context


def build_prompt(
    roadmap: dict[str, Any],
    task: dict[str, Any],
    memory: dict[str, Any],
    *,
    code_mode: bool,
) -> str:
    completed = [
        {"id": item["id"], "title": item["title"], "result": item.get("result")}
        for item in roadmap["tasks"]
        if item["status"] == "completed"
    ]
    recent_runs = memory.get("runs", [])[-5:]
    context_files = read_task_context(task) if code_mode else []
    mode_rules = (
        "Code mode: read the file context below and return a unified diff that applies "
        "with `git apply`. Only modify files directly related to the task. If context "
        "is insufficient, return failed and list the additional files needed. Put patch "
        "content in `unified_diff_lines` as one array item per physical patch line. Base "
        "patch hunks only on the exact File context provided; do not invent nearby comments, "
        "line numbers, or file contents."
        if code_mode
        else "Plan mode: analyze the task and propose an approach; do not claim code was changed."
    )

    return f"""
You are a development agent helping build Havi, an AI marketing app for small businesses.

Rules:
- Work only on the current task; do not expand scope.
- Do not request dangerous commands.
- If changing code, return a valid unified diff.
- Return valid JSON only, without Markdown fences.
- {mode_rules}

Project: {roadmap["project"]}

Source of truth:
{json.dumps(roadmap.get("source_of_truth", []), ensure_ascii=False, indent=2)}

Guardrails:
{json.dumps(roadmap.get("guardrails", []), ensure_ascii=False, indent=2)}

Definition of Done:
{json.dumps(roadmap.get("definition_of_done", []), ensure_ascii=False, indent=2)}

Current task:
{json.dumps(task, ensure_ascii=False, indent=2)}

File context:
{json.dumps(context_files, ensure_ascii=False, indent=2)}

Completed tasks:
{json.dumps(completed, ensure_ascii=False, indent=2)}

Recent checkpoints:
{json.dumps(recent_runs, ensure_ascii=False, indent=2)}

Return JSON matching this schema. Prefer `unified_diff_lines` over `unified_diff`
in code mode so JSON escaping stays valid:
{{
  "status": "completed" | "failed",
  "summary": "short summary",
  "suggested_changes": ["..."],
  "commands_to_run": ["..."],
  "unified_diff": "diff --git ... or an empty string if no code changes are proposed",
  "unified_diff_lines": ["diff --git a/file b/file", "--- a/file", "+++ b/file", "..."],
  "next_notes": "notes for the next run"
}}
""".strip()


def parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        stripped = "\n".join(lines[1:-1]).strip()

    try:
        value = json.loads(stripped)
    except json.JSONDecodeError as first_error:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return parse_loose_provider_response(stripped, first_error)
        candidate = stripped[start : end + 1]
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            return parse_loose_provider_response(stripped, first_error)

    if not isinstance(value, dict):
        raise ValueError("Model must return a JSON object.")
    return value


def parse_loose_provider_response(text: str, error: json.JSONDecodeError) -> dict[str, Any]:
    """Best-effort parser for provider JSON that contains raw newlines in diff strings."""

    diff = extract_diff(text)
    status = extract_json_string_field(text, "status") or ("completed" if diff else "failed")
    summary = extract_json_string_field(text, "summary") or (
        "Provider returned malformed JSON, but a unified diff was recovered."
        if diff
        else f"Provider returned malformed JSON: {error}"
    )
    next_notes = extract_json_string_field(text, "next_notes") or ""
    return {
        "status": status if status in TASK_STATUSES else "failed",
        "summary": summary,
        "suggested_changes": [],
        "commands_to_run": [],
        "unified_diff": diff,
        "next_notes": next_notes,
        "parse_warning": str(error),
    }


def extract_json_string_field(text: str, field: str) -> str | None:
    match = re.search(rf'"{re.escape(field)}"\\s*:\\s*"((?:\\\\.|[^"\\\\])*)"', text, re.S)
    if not match:
        return None
    try:
        return json.loads(f'"{match.group(1)}"')
    except json.JSONDecodeError:
        return match.group(1)


def extract_diff(text: str) -> str:
    fence_match = re.search(r"```(?:diff|patch)?\\s*(diff --git .*?)```", text, re.S)
    if fence_match:
        return fence_match.group(1).strip()

    start = text.find("diff --git ")
    if start == -1:
        return ""

    diff = text[start:]
    marker_positions = [
        pos
        for marker in ('\\n  "next_notes"', '\\n  "commands_to_run"', '\\n  "suggested_changes"')
        if (pos := diff.find(marker)) != -1
    ]
    if marker_positions:
        diff = diff[: min(marker_positions)]
    diff = diff.strip()
    if diff.endswith('"'):
        diff = diff[:-1].rstrip()
    if diff.endswith(","):
        diff = diff[:-1].rstrip()
    return diff.replace("\\\\n", "\n").replace("\\\\t", "\t")


def post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout_seconds: int,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc


def call_gemini(prompt: str, model: str, api_key: str, timeout_seconds: int) -> tuple[str, int]:
    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        + urllib.parse.quote(model, safe="")
        + ":generateContent?key="
        + urllib.parse.quote(api_key, safe="")
    )
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }
    body = post_json(endpoint, payload, {}, timeout_seconds)

    candidates = body.get("candidates") or []
    parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
    text = "".join(part.get("text", "") for part in parts)
    usage = body.get("usageMetadata") or {}
    total_tokens = int(usage.get("totalTokenCount") or 0)
    if not text.strip():
        raise RuntimeError("Gemini returned no text.")
    return text, total_tokens


def call_anthropic(prompt: str, model: str, api_key: str, timeout_seconds: int) -> tuple[str, int]:
    payload = {
        "model": model,
        "max_tokens": 4096,
        "system": "Return exactly one valid JSON object, without Markdown fences.",
        "messages": [{"role": "user", "content": prompt}],
    }
    body = post_json(
        "https://api.anthropic.com/v1/messages",
        payload,
        {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        timeout_seconds,
    )

    text = "".join(
        block.get("text", "")
        for block in body.get("content", [])
        if block.get("type") == "text"
    )
    usage = body.get("usage", {})
    total_tokens = int(usage.get("input_tokens") or 0) + int(usage.get("output_tokens") or 0)
    if not text.strip():
        raise RuntimeError("Anthropic returned no text.")
    return text, total_tokens


def call_openai(prompt: str, model: str, api_key: str, timeout_seconds: int) -> tuple[str, int]:
    payload = {
        "model": model,
        "max_completion_tokens": 4096,
        "messages": [
            {"role": "system", "content": "Return exactly one valid JSON object."},
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
    }
    body = post_json(
        "https://api.openai.com/v1/chat/completions",
        payload,
        {"Authorization": f"Bearer {api_key}"},
        timeout_seconds,
    )

    choices = body.get("choices") or []
    text = choices[0].get("message", {}).get("content", "") if choices else ""
    usage = body.get("usage", {})
    total_tokens = int(usage.get("total_tokens") or 0)
    if not text.strip():
        raise RuntimeError("OpenAI returned no text.")
    return text, total_tokens


def provider_config(provider: str) -> tuple[str, str]:
    if provider == "gemini":
        return (
            os.environ.get("HAVI_GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY", ""),
            os.environ.get("HAVI_GEMINI_MODEL", "gemini-3.6-flash"),
        )
    if provider == "anthropic":
        return (
            os.environ.get("HAVI_ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", ""),
            os.environ.get("HAVI_ANTHROPIC_MODEL", "claude-sonnet-5"),
        )
    if provider == "openai":
        return (
            os.environ.get("HAVI_OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY", ""),
            os.environ.get("HAVI_OPENAI_MODEL", "gpt-5"),
        )
    raise ValueError(f"Unsupported provider: {provider}")


def resolve_provider(requested_provider: str) -> tuple[str, str, str]:
    if requested_provider != "auto":
        api_key, model = provider_config(requested_provider)
        if not api_key:
            raise RuntimeError(f"Missing API key for provider `{requested_provider}`.")
        return requested_provider, api_key, model

    for provider in DEFAULT_PROVIDER_ORDER:
        api_key, model = provider_config(provider)
        if api_key:
            return provider, api_key, model

    raise RuntimeError(
        "Missing API key. Set one of: HAVI_GEMINI_API_KEY, "
        "HAVI_ANTHROPIC_API_KEY, HAVI_OPENAI_API_KEY."
    )


def call_provider(
    provider: str,
    prompt: str,
    model: str,
    api_key: str,
    timeout_seconds: int,
) -> tuple[str, int]:
    if provider == "gemini":
        return call_gemini(prompt, model, api_key, timeout_seconds)
    if provider == "anthropic":
        return call_anthropic(prompt, model, api_key, timeout_seconds)
    if provider == "openai":
        return call_openai(prompt, model, api_key, timeout_seconds)
    raise ValueError(f"Unsupported provider: {provider}")


def dry_run_response(task: dict[str, Any]) -> tuple[dict[str, Any], int]:
    return (
        {
            "status": "completed",
            "summary": f"Dry-run processed task `{task['id']}` and wrote a checkpoint.",
            "suggested_changes": [],
            "commands_to_run": [],
            "unified_diff": "",
            "unified_diff_lines": [],
            "next_notes": "Run with --execute to call a real provider.",
        },
        0,
    )


def write_patch_file(task_id: str, unified_diff: str) -> Path:
    patch_dir = ROOT / "agent-loop" / "patches"
    patch_dir.mkdir(parents=True, exist_ok=True)
    patch_path = patch_dir / f"{task_id}.patch"
    patch_path.write_text(normalize_unified_diff(unified_diff).rstrip() + "\n", encoding="utf-8")
    return patch_path


def result_unified_diff(result: dict[str, Any]) -> str:
    lines = result.get("unified_diff_lines")
    if isinstance(lines, list) and all(isinstance(line, str) for line in lines):
        return "\n".join(lines).strip()
    return str(result.get("unified_diff") or "").strip()


def normalize_unified_diff(unified_diff: str) -> str:
    """Recalculate hunk line counts; LLMs often get @@ counts slightly wrong."""

    lines = unified_diff.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    normalized: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.startswith("@@ "):
            normalized.append(line)
            index += 1
            continue

        header = line
        body: list[str] = []
        index += 1
        while index < len(lines) and not lines[index].startswith(("@@ ", "diff --git ")):
            body.append(lines[index])
            index += 1

        normalized.append(rewrite_hunk_header(header, body))
        normalized.extend(body)
    return "\n".join(normalized)


def rewrite_hunk_header(header: str, body: list[str]) -> str:
    match = re.match(
        r"^@@ -(?P<old_start>\d+)(?:,\d+)? \+(?P<new_start>\d+)(?:,\d+)? @@(?P<tail>.*)$",
        header,
    )
    if not match:
        return header

    old_count = 0
    new_count = 0
    for line in body:
        if line.startswith("\\"):
            continue
        if line.startswith((" ", "-")):
            old_count += 1
        if line.startswith((" ", "+")):
            new_count += 1

    return (
        f"@@ -{format_hunk_range(match.group('old_start'), old_count)} "
        f"+{format_hunk_range(match.group('new_start'), new_count)} @@{match.group('tail')}"
    )


def format_hunk_range(start: str, count: int) -> str:
    if count == 1:
        return start
    return f"{start},{count}"


def apply_patch_file(patch_path: Path) -> None:
    check = run_git_apply(["--check", "--recount", "--whitespace=fix"], patch_path)
    if check.returncode != 0:
        raise PatchApplyFailed(
            "git apply preflight failed for "
            f"{patch_path.relative_to(ROOT)}:\n{command_output(check)}"
        )

    completed = run_git_apply(["--recount", "--whitespace=fix"], patch_path)
    if completed.returncode != 0:
        raise PatchApplyFailed(
            "git apply failed for "
            f"{patch_path.relative_to(ROOT)}:\n{command_output(completed)}"
        )


def run_git_apply(args: list[str], patch_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "apply", *args, str(patch_path)],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )


def command_output(completed: subprocess.CompletedProcess[str]) -> str:
    output = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip())
    return output or f"command exited with status {completed.returncode}"


def run_verify_commands(task: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for command in task.get("verify_commands", []):
        print(f"  -> running verify: {command}")
        completed = subprocess.run(
            command,
            cwd=ROOT,
            shell=True,
            check=False,
            text=True,
            capture_output=True,
        )
        output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
        if len(output) > 6000:
            output = output[-6000:]
        results.append(
            {
                "command": command,
                "returncode": completed.returncode,
                "output_tail": output,
            }
        )
        if completed.returncode != 0:
            raise RuntimeError(f"verify command failed ({completed.returncode}): {command}")
    return results


def run_loop(args: argparse.Namespace) -> int:
    load_env_file(args.env_file)
    ensure_default_roadmap(args.roadmap)

    roadmap = load_json(args.roadmap)
    memory = load_json(
        args.memory,
        default={"created_at": utc_now(), "total_tokens": 0, "runs": []},
    )
    validate_roadmap(roadmap)

    if args.execute:
        provider, api_key, configured_model = resolve_provider(args.provider)
        model = args.model or configured_model
        print(f"Using provider `{provider}` with model `{model}`.")
    else:
        provider = args.provider
        api_key = ""
        model = args.model or "dry-run"

    task_limit = args.task_limit if args.task_limit is not None else args.max_steps

    for step in range(1, task_limit + 1):
        task = select_task(roadmap["tasks"])
        if task is None:
            print("All tasks are completed.")
            save_json(args.roadmap, roadmap)
            save_json(args.memory, memory)
            return 0

        if int(memory.get("total_tokens", 0)) >= args.max_total_tokens:
            print("Stopped because the token limit was reached.")
            break

        print(f"[{step}/{task_limit}] Processing task {task['id']}: {task['title']}")
        task["status"] = "in_progress"
        task["started_at"] = task.get("started_at") or utc_now()
        save_json(args.roadmap, roadmap)
        result: dict[str, Any] | None = None
        used_tokens = 0

        try:
            if args.execute:
                prompt = build_prompt(roadmap, task, memory, code_mode=args.code)
                text, used_tokens = call_provider(
                    provider=provider,
                    prompt=prompt,
                    model=model,
                    api_key=api_key,
                    timeout_seconds=args.timeout_seconds,
                )
                result = parse_json_object(text)
            else:
                result, used_tokens = dry_run_response(task)

            status = result.get("status")
            if status not in {"completed", "failed"}:
                raise ValueError("Model result must have status `completed` or `failed`.")

            unified_diff = result_unified_diff(result)
            if args.code and unified_diff:
                patch_path = write_patch_file(str(task["id"]), unified_diff)
                result["patch_file"] = str(patch_path.relative_to(ROOT))
                print(f"  -> created patch: {result['patch_file']}")
                if args.apply_patch:
                    apply_patch_file(patch_path)
                    result["patch_applied"] = True
                    print("  -> applied patch")
                    if args.verify:
                        result["verify_results"] = run_verify_commands(task)
                        print("  -> verify commands passed")

            task["status"] = status
            task["finished_at"] = utc_now()
            task["result"] = result
            if status == "failed":
                task["error"] = result.get("summary", "Task failed.")

            memory["total_tokens"] = int(memory.get("total_tokens", 0)) + used_tokens
            memory.setdefault("runs", []).append(
                {
                    "task_id": task["id"],
                    "status": status,
                    "tokens": used_tokens,
                    "at": utc_now(),
                    "summary": result.get("summary", ""),
                }
            )
            save_json(args.roadmap, roadmap)
            save_json(args.memory, memory)
            print(f"  -> {status}; tokens={used_tokens}; total={memory['total_tokens']}")

            if status == "failed":
                break
            if args.sleep_seconds > 0:
                time.sleep(args.sleep_seconds)
        except Exception as exc:
            patch_apply_failed = isinstance(exc, PatchApplyFailed)
            task["status"] = "pending" if patch_apply_failed else "failed"
            task["finished_at"] = utc_now()
            error_key = "last_error" if patch_apply_failed else "error"
            task[error_key] = str(exc)
            if patch_apply_failed and result:
                last_result = {
                    "status": result.get("status"),
                    "summary": result.get("summary", ""),
                }
                if result.get("patch_file"):
                    last_result["patch_file"] = result["patch_file"]
                    task["last_patch_file"] = result["patch_file"]
                if result.get("parse_warning"):
                    last_result["parse_warning"] = result["parse_warning"]
                task["last_result"] = last_result
            memory.setdefault("runs", []).append(
                {
                    "task_id": task["id"],
                    "status": "pending" if patch_apply_failed else "failed",
                    "tokens": used_tokens,
                    "at": utc_now(),
                    "summary": str(exc),
                }
            )
            memory["total_tokens"] = int(memory.get("total_tokens", 0)) + used_tokens
            save_json(args.roadmap, roadmap)
            save_json(args.memory, memory)
            raise

    print("Loop stopped at the current limit.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Havi bounded dev agent loop.")
    parser.add_argument("--roadmap", type=Path, default=DEFAULT_ROADMAP)
    parser.add_argument("--memory", type=Path, default=DEFAULT_MEMORY)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--model")
    parser.add_argument("--provider", choices=("auto", *PROVIDERS), default="auto")
    parser.add_argument(
        "--code",
        action="store_true",
        help="Read files_to_read and ask the provider to return a unified diff.",
    )
    parser.add_argument(
        "--apply-patch",
        action="store_true",
        help="Apply the returned diff with git apply.",
    )
    parser.add_argument(
        "--verify",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run the task verify_commands after applying a patch.",
    )
    parser.add_argument(
        "--task-limit",
        type=int,
        help="Maximum number of tasks to run in one batch. Defaults to 1 task.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=1,
        help="Old alias for --task-limit; kept so existing commands do not break.",
    )
    parser.add_argument("--max-total-tokens", type=int, default=100_000)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Call a real provider. Defaults to dry-run with no token cost.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        return run_loop(parse_args())
    except Exception as exc:
        print(f"Agent loop error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
