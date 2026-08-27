from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
from pathlib import Path
from typing import Any, Iterable


def parse_timecode(value: str | float | int) -> float:
    """Parse SS, MM:SS, or HH:MM:SS(.mmm) into seconds."""
    if isinstance(value, (int, float)):
        seconds = float(value)
    else:
        raw = str(value).strip()
        if not raw:
            raise ValueError("timecode is empty")
        parts = raw.split(":")
        if len(parts) > 3:
            raise ValueError(f"invalid timecode: {value}")
        try:
            numbers = [float(part) for part in parts]
        except ValueError as exc:
            raise ValueError(f"invalid timecode: {value}") from exc
        if len(numbers) == 3:
            hours, minutes, secs = numbers
        elif len(numbers) == 2:
            hours, minutes, secs = 0.0, numbers[0], numbers[1]
        else:
            hours, minutes, secs = 0.0, 0.0, numbers[0]
        if hours < 0 or minutes < 0 or secs < 0:
            raise ValueError(f"timecode must be non-negative: {value}")
        if len(numbers) >= 2 and secs >= 60:
            raise ValueError(f"seconds must be below 60: {value}")
        if len(numbers) == 3 and minutes >= 60:
            raise ValueError(f"minutes must be below 60: {value}")
        seconds = hours * 3600 + minutes * 60 + secs
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError(f"timecode must be non-negative: {value}")
    return seconds


def format_timecode(seconds: float, decimals: int = 3) -> str:
    seconds = max(0.0, float(seconds))
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    width = 2 + (1 + decimals if decimals else 0)
    return f"{hours:02d}:{minutes:02d}:{secs:0{width}.{decimals}f}"


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def short_hash(values: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(value.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()[:16]


def run_command(
    command: list[str],
    logger,
    *,
    cwd: Path | None = None,
    check: bool = True,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    printable = subprocess.list2cmdline(command)
    logger.info("COMMAND %s", printable)
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    process = subprocess.Popen(
        command,
        cwd=str(cwd) if cwd else None,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=creationflags,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        else:
            process.kill()
        final_stdout, final_stderr = process.communicate()
        stdout = (exc.stdout or "") + (final_stdout or "")
        stderr = (exc.stderr or "") + (final_stderr or "")
        if stdout:
            logger.info("STDOUT BEFORE TIMEOUT\n%s", str(stdout)[-4000:])
        if stderr:
            logger.info("STDERR BEFORE TIMEOUT\n%s", str(stderr)[-4000:])
        raise RuntimeError(
            f"command timed out after {timeout} seconds: {printable}"
        ) from exc
    result = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    if result.stdout.strip():
        logger.info("STDOUT\n%s", result.stdout.rstrip())
    if result.stderr.strip():
        logger.info("STDERR\n%s", result.stderr.rstrip())
    if check and result.returncode != 0:
        tail = (result.stderr or result.stdout)[-4000:]
        raise RuntimeError(
            f"command failed with exit code {result.returncode}: {printable}\n{tail}"
        )
    return result
