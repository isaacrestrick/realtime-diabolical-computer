from __future__ import annotations

import asyncio
import base64
import json
import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ComputerUseDemoContainer:
    id: str
    image: str
    name: str
    ports: str


async def _run_process(
    args: list[str],
    *,
    timeout_seconds: int,
    stdin_text: str | None = None,
) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdin=asyncio.subprocess.PIPE if stdin_text is not None else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(
                stdin_text.encode("utf-8") if stdin_text is not None else None
            ),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise

    stdout = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
    stderr = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""
    return proc.returncode or 0, stdout, stderr


async def find_computer_use_demo_container() -> Optional[ComputerUseDemoContainer]:
    """
    Best-effort detection of the running computer-use-demo container.

    Prefers containers that expose port 8080 and look like the anthropic computer-use-demo image.
    """
    code, stdout, _stderr = await _run_process(
        ["docker", "ps", "--format", "{{.ID}}|{{.Image}}|{{.Names}}|{{.Ports}}"],
        timeout_seconds=5,
    )
    if code != 0:
        return None

    candidates: list[ComputerUseDemoContainer] = []
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split("|", maxsplit=3)
        if len(parts) != 4:
            continue
        container_id, image, name, ports = parts
        candidates.append(
            ComputerUseDemoContainer(id=container_id, image=image, name=name, ports=ports)
        )

    if not candidates:
        return None

    def score(c: ComputerUseDemoContainer) -> int:
        s = 0
        if "8080->8080" in c.ports or ":8080->8080" in c.ports:
            s += 100
        if "computer-use-demo" in c.image:
            s += 50
        if "anthropic-quickstarts" in c.image:
            s += 10
        return s

    candidates.sort(key=score, reverse=True)
    best = candidates[0]
    if score(best) <= 0:
        return None
    return best


_OPUS_RUNNER_SCRIPT = r"""
import asyncio
import base64
import json
import os
import sys

from computer_use_demo.loop import APIProvider, sampling_loop


def _read_task() -> str:
    task_b64 = os.environ.get("OPUS_TASK_B64", "")
    if not task_b64:
        raise RuntimeError("Missing OPUS_TASK_B64")
    raw = base64.urlsafe_b64decode(task_b64.encode("utf-8"))
    data = json.loads(raw.decode("utf-8"))
    task = data.get("task")
    if not isinstance(task, str) or not task.strip():
        raise RuntimeError("Invalid task")
    return task.strip()


def _extract_final_text(messages):
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "assistant":
            content = msg.get("content") or []
            if not isinstance(content, list):
                continue
            texts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text")
                    if isinstance(text, str) and text.strip():
                        texts.append(text)
            return "\n".join(texts).strip()
    return ""


async def main() -> int:
    task = _read_task()

    model = os.environ.get("OPUS_MODEL") or os.environ.get("MODEL") or "claude-opus-4-5-20251101"
    tool_version = os.environ.get("OPUS_TOOL_VERSION") or "computer_use_20251124"
    max_tokens = int(os.environ.get("OPUS_MAX_TOKENS") or "2048")
    only_n = os.environ.get("OPUS_ONLY_N_MOST_RECENT_IMAGES")
    only_n_images = int(only_n) if only_n else None

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("Missing ANTHROPIC_API_KEY inside container")

    messages = [
        {
            "role": "user",
            "content": [{"type": "text", "text": task}],
        }
    ]

    def output_callback(_block):
        return None

    def tool_output_callback(_result, _tool_use_id):
        return None

    def api_response_callback(_request, _response, _err):
        return None

    out_messages = await sampling_loop(
        model=model,
        provider=APIProvider.ANTHROPIC,
        system_prompt_suffix="",
        messages=messages,
        output_callback=output_callback,
        tool_output_callback=tool_output_callback,
        api_response_callback=api_response_callback,
        api_key=api_key,
        only_n_most_recent_images=only_n_images,
        max_tokens=max_tokens,
        tool_version=tool_version,
    )

    final_text = _extract_final_text(out_messages)
    sys.stdout.write(final_text)
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
""".lstrip()


async def run_opus_task_in_container(
    task: str,
    *,
    timeout_seconds: int,
    container: str | None = None,
    model: str | None = None,
    tool_version: str | None = None,
) -> str:
    resolved_container = container or os.getenv("COMPUTER_USE_DEMO_CONTAINER")
    if not resolved_container:
        detected = await find_computer_use_demo_container()
        if not detected:
            raise RuntimeError(
                "Could not find a running computer-use-demo container. "
                "Start it and ensure it exposes port 8080."
            )
        resolved_container = detected.id

    task_payload = {"task": task}
    task_b64 = base64.urlsafe_b64encode(
        json.dumps(task_payload).encode("utf-8")
    ).decode("utf-8")

    docker_args = [
        "docker",
        "exec",
        "-i",
        "-e",
        f"OPUS_TASK_B64={task_b64}",
    ]

    if model:
        docker_args.extend(["-e", f"OPUS_MODEL={model}"])
    if tool_version:
        docker_args.extend(["-e", f"OPUS_TOOL_VERSION={tool_version}"])

    docker_args.extend([resolved_container, "python", "-"])

    code, stdout, stderr = await _run_process(
        docker_args,
        timeout_seconds=timeout_seconds,
        stdin_text=_OPUS_RUNNER_SCRIPT,
    )

    if code != 0:
        raise RuntimeError(f"Opus task failed (exit {code}). stderr:\n{stderr.strip()}")

    return stdout.strip() if stdout else ""
