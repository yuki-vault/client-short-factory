from __future__ import annotations

import errno
import hashlib
import json
import math
import os
import re
import secrets
import shutil
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Iterator, Mapping

from .candidate_selector import CandidateSelectionError, validate_candidate_set


RUN_SCHEMA_VERSION = 1
CANDIDATE_SET_SCHEMA_VERSION = 1
UPLOAD_CHUNK_BYTES = 8 * 1024 * 1024
MAX_SOURCE_BYTES = 64 * 1024 * 1024 * 1024
MAX_CANDIDATES = 5
CODEX_PROVIDER = "openai-codex"
CODEX_MODEL = "gpt-5.6-sol"
CODEX_PAYLOAD_SCOPE = (
    "timestamped transcript text only; no source video, audio, or frames"
)

_SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}
_STATES = {
    "created",
    "uploading",
    "finalized",
    "queued",
    "processing",
    "complete",
    "cancelled",
    "failed",
}
_STAGES = {
    "created",
    "upload",
    "finalized",
    "queued",
    "source_validation",
    "audio",
    "transcription",
    "selection",
    "preview",
    "publish",
    "complete",
    "cancelled",
    "failed",
}


class CandidateArtifactError(RuntimeError):
    status_code = 400


class CandidateNotFoundError(CandidateArtifactError):
    status_code = 404


class CandidateConflictError(CandidateArtifactError):
    status_code = 409


class CandidateBusyError(CandidateConflictError):
    pass


class CandidateValidationError(CandidateArtifactError):
    status_code = 422


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_link(path: Path) -> bool:
    is_junction = getattr(os.path, "isjunction", None)
    return path.is_symlink() or bool(callable(is_junction) and is_junction(path))


def _validate_id(value: Any, kind: str) -> str:
    base = value.split(".", 1)[0].upper() if isinstance(value, str) else ""
    if (
        not isinstance(value, str)
        or not _SAFE_ID.fullmatch(value)
        or value.endswith(".")
        or base in _WINDOWS_RESERVED
    ):
        raise CandidateValidationError(f"invalid {kind}")
    return value


def _candidate_root(value: Path, *, create: bool = False) -> Path:
    raw = value.expanduser().absolute()
    if raw.exists() and _is_link(raw):
        raise CandidateValidationError("candidate root must not be a link")
    if create:
        raw.mkdir(parents=True, exist_ok=True)
    root = raw.resolve()
    if not root.is_dir():
        raise CandidateNotFoundError("candidate root does not exist")
    return root


def _confined(root: Path, *parts: str) -> Path:
    resolved_root = root.expanduser().resolve()
    candidate = resolved_root.joinpath(*parts).resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise CandidateValidationError("candidate artifact escapes its run") from exc
    return candidate


def _read_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CandidateNotFoundError(f"{label} is missing") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CandidateValidationError(f"{label} is invalid") from exc
    if not isinstance(value, dict):
        raise CandidateValidationError(f"{label} must be an object")
    return value


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    encoded = (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        _replace_with_windows_retry(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _replace_with_windows_retry(source: Path, destination: Path) -> None:
    """Retry only transient Windows sharing/access races for an atomic replace."""

    delays = (0.0, 0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 0.5)
    for attempt, delay in enumerate(delays):
        if delay:
            time.sleep(delay)
        try:
            os.replace(source, destination)
            return
        except OSError as exc:
            transient = os.name == "nt" and getattr(exc, "winerror", None) in {
                5,
                32,
                33,
            }
            if not transient or attempt == len(delays) - 1:
                raise


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def candidate_run_dir(candidate_root: Path, run_id: str) -> Path:
    root = _candidate_root(candidate_root)
    _validate_id(run_id, "candidate run id")
    candidate = (root / run_id).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise CandidateValidationError("candidate run escapes its root") from exc
    if not candidate.is_dir():
        raise CandidateNotFoundError("candidate run not found")
    return candidate


def candidate_work_dir(run_dir: Path) -> Path:
    return _confined(run_dir, "work")


def _authorization_content_sha256(value: Mapping[str, Any]) -> str:
    document = {key: item for key, item in value.items() if key != "content_sha256"}
    encoded = json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_external_ai_authorization(
    value: Mapping[str, Any], *, run_id: str, source_sha256: str
) -> dict[str, Any]:
    required = {
        "schema_version",
        "run_id",
        "source_sha256",
        "provider",
        "model",
        "payload_scope",
        "local_session_persistence",
        "provider_retention",
        "approved_at",
        "approval_note",
        "rights_record",
        "content_sha256",
    }
    if not isinstance(value, Mapping) or set(value) != required:
        raise CandidateValidationError("external AI authorization is invalid")
    if (
        value.get("schema_version") != 1
        or value.get("run_id") != run_id
        or value.get("source_sha256") != source_sha256
        or value.get("provider") != CODEX_PROVIDER
        or value.get("model") != CODEX_MODEL
        or value.get("payload_scope") != CODEX_PAYLOAD_SCOPE
        or value.get("local_session_persistence") != "ephemeral"
        or value.get("provider_retention") != "not_inferred"
        or not isinstance(value.get("approved_at"), str)
        or not isinstance(value.get("approval_note"), str)
        or not 1 <= len(value["approval_note"]) <= 1000
        or not isinstance(value.get("rights_record"), str)
        or not 1 <= len(value["rights_record"]) <= 300
        or not isinstance(value.get("content_sha256"), str)
        or not _SHA256.fullmatch(value["content_sha256"])
        or _authorization_content_sha256(value) != value["content_sha256"]
    ):
        raise CandidateValidationError("external AI authorization is invalid")
    return dict(value)


def load_external_ai_authorization(run_dir: Path) -> dict[str, Any] | None:
    path = _confined(run_dir, "external-ai-authorization.json")
    if not path.is_file():
        return None
    manifest = _read_object(_confined(run_dir, "manifest.json"), "candidate manifest")
    source = manifest.get("source")
    if not isinstance(source, Mapping) or not isinstance(source.get("sha256"), str):
        raise CandidateValidationError("candidate source manifest is invalid")
    return _validate_external_ai_authorization(
        _read_object(path, "external AI authorization"),
        run_id=run_dir.name,
        source_sha256=source["sha256"],
    )


def record_codex_selection_authorization(
    candidate_root: Path,
    run_id: str,
    *,
    approval_note: str,
    rights_record: str,
) -> dict[str, Any]:
    run = load_run(candidate_root, run_id)
    run_dir = Path(run["run_dir"])
    with candidate_run_lock(run_dir):
        run = load_run(candidate_root, run_id)
        manifest = run.get("manifest")
        source = manifest.get("source") if isinstance(manifest, Mapping) else None
        if not isinstance(source, Mapping) or not isinstance(source.get("sha256"), str):
            raise CandidateConflictError("source must be finalized before authorization")
        path = _confined(run_dir, "external-ai-authorization.json")
        if path.is_file():
            return load_external_ai_authorization(run_dir)  # type: ignore[return-value]
        value: dict[str, Any] = {
            "schema_version": 1,
            "run_id": run_id,
            "source_sha256": source["sha256"],
            "provider": CODEX_PROVIDER,
            "model": CODEX_MODEL,
            "payload_scope": CODEX_PAYLOAD_SCOPE,
            "local_session_persistence": "ephemeral",
            "provider_retention": "not_inferred",
            "approved_at": _now(),
            "approval_note": approval_note,
            "rights_record": rights_record,
        }
        value["content_sha256"] = _authorization_content_sha256(value)
        validated = _validate_external_ai_authorization(
            value, run_id=run_id, source_sha256=source["sha256"]
        )
        _atomic_json(path, validated)
        return validated


def source_path(run_dir: Path) -> Path:
    path = _confined(run_dir, "source", "source.media")
    if not path.is_file():
        raise CandidateNotFoundError("finalized source is missing")
    return path


def candidate_source(
    candidate_root: Path, run_id: str
) -> tuple[dict[str, Any], Path]:
    """Return the immutable finalized source metadata and its confined path.

    This is intentionally a cheap identity check for interactive Range playback.
    The adoption worker performs the full SHA-256 verification before creating a
    normal workflow job.
    """
    run = load_run(candidate_root, run_id)
    manifest = run.get("manifest")
    source = manifest.get("source") if isinstance(manifest, Mapping) else None
    if not isinstance(source, Mapping):
        raise CandidateNotFoundError("candidate source is not finalized")
    path = source_path(Path(run["run_dir"]))
    size = source.get("size_bytes")
    digest = source.get("sha256")
    duration = source.get("duration_seconds")
    if (
        isinstance(size, bool)
        or not isinstance(size, int)
        or size <= 0
        or path.stat().st_size != size
        or not isinstance(digest, str)
        or not _SHA256.fullmatch(digest)
        or isinstance(duration, bool)
        or not isinstance(duration, (int, float))
        or not math.isfinite(float(duration))
        or float(duration) <= 0
    ):
        raise CandidateConflictError("candidate source identity changed")
    content_type = run["intake"]["file"].get("content_type")
    if content_type not in {
        "video/mp4",
        "video/webm",
        "video/quicktime",
        "video/x-matroska",
    }:
        content_type = "application/octet-stream"
    return (
        {
            "sha256": digest,
            "size_bytes": size,
            "duration_seconds": float(duration),
            "content_type": content_type,
        },
        path,
    )


def _validated_file(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {
        "name",
        "size_bytes",
        "content_type",
        "last_modified_ms",
    }:
        raise CandidateValidationError("invalid source file metadata")
    name = value["name"]
    content_type = value["content_type"]
    size = value["size_bytes"]
    modified = value["last_modified_ms"]
    if (
        not isinstance(name, str)
        or not name.strip()
        or len(name) > 255
        or "\0" in name
        or any(ord(character) < 32 for character in name)
    ):
        raise CandidateValidationError("invalid source display name")
    if not isinstance(content_type, str) or len(content_type) > 200 or "\0" in content_type:
        raise CandidateValidationError("invalid source content type")
    if isinstance(size, bool) or not isinstance(size, int) or not 1 <= size <= MAX_SOURCE_BYTES:
        raise CandidateValidationError("source size is outside the supported range")
    if (
        isinstance(modified, bool)
        or not isinstance(modified, (int, float))
        or not math.isfinite(float(modified))
        or modified < 0
    ):
        raise CandidateValidationError("invalid source modification time")
    return {
        "name": name.strip(),
        "size_bytes": size,
        "content_type": content_type,
        "last_modified_ms": float(modified),
    }


def _validated_rights(value: Any) -> dict[str, bool]:
    required = {"edit_analysis_confirmed", "local_processing_confirmed"}
    if not isinstance(value, Mapping) or set(value) != required:
        raise CandidateValidationError("rights confirmation is required")
    if any(value[key] is not True for key in required):
        raise CandidateValidationError("both rights confirmations must be true")
    return {key: True for key in sorted(required)}


def create_candidate_run(
    candidate_root: Path, *, file: Mapping[str, Any], rights: Mapping[str, Any]
) -> dict[str, Any]:
    root = _candidate_root(candidate_root, create=True)
    normalized_file = _validated_file(file)
    normalized_rights = _validated_rights(rights)
    required_free = normalized_file["size_bytes"] + _required_work_free(
        normalized_file["size_bytes"]
    )
    if shutil.disk_usage(root).free < required_free:
        raise CandidateConflictError("insufficient disk space for local analysis")
    for _ in range(20):
        run_id = f"candidate-{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{secrets.token_hex(5)}"
        destination = root / run_id
        temporary = root / f".{run_id}.tmp"
        if destination.exists() or temporary.exists():
            continue
        temporary.mkdir()
        try:
            intake = {
                "schema_version": RUN_SCHEMA_VERSION,
                "run_id": run_id,
                "created_at": _now(),
                "file": normalized_file,
                "rights": normalized_rights,
            }
            upload = {
                "schema_version": RUN_SCHEMA_VERSION,
                "received_bytes": 0,
                "total_bytes": normalized_file["size_bytes"],
                "next_chunk_index": 0,
                "chunk_bytes": UPLOAD_CHUNK_BYTES,
                "complete": False,
            }
            status = {
                "schema_version": RUN_SCHEMA_VERSION,
                "state": "created",
                "stage": "created",
                "updated_at": _now(),
                "progress": {"completed": 0, "total": normalized_file["size_bytes"]},
            }
            _atomic_json(temporary / "intake.json", intake)
            _atomic_json(temporary / "upload" / "progress.json", upload)
            _atomic_json(temporary / "status.json", status)
            os.replace(temporary, destination)
            return load_run(root, run_id)
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise
    raise CandidateConflictError("could not allocate a candidate run")


def _required_work_free(source_size: int) -> int:
    return max(512 * 1024 * 1024, min(source_size, 4 * 1024 * 1024 * 1024))


def _validate_upload(value: Mapping[str, Any], total: int) -> dict[str, Any]:
    required = {
        "schema_version",
        "received_bytes",
        "total_bytes",
        "next_chunk_index",
        "chunk_bytes",
        "complete",
    }
    if set(value) != required or value.get("schema_version") != RUN_SCHEMA_VERSION:
        raise CandidateValidationError("upload progress is invalid")
    for key in ("received_bytes", "total_bytes", "next_chunk_index", "chunk_bytes"):
        if isinstance(value[key], bool) or not isinstance(value[key], int) or value[key] < 0:
            raise CandidateValidationError("upload progress is invalid")
    if (
        value["total_bytes"] != total
        or value["chunk_bytes"] != UPLOAD_CHUNK_BYTES
        or value["received_bytes"] > total
        or value["next_chunk_index"] != math.ceil(value["received_bytes"] / UPLOAD_CHUNK_BYTES)
        or not isinstance(value["complete"], bool)
    ):
        raise CandidateValidationError("upload progress is inconsistent")
    return dict(value)


def _validate_status(value: Mapping[str, Any]) -> dict[str, Any]:
    if value.get("schema_version") != RUN_SCHEMA_VERSION:
        raise CandidateValidationError("candidate status is invalid")
    if value.get("state") not in _STATES or value.get("stage") not in _STAGES:
        raise CandidateValidationError("candidate status is invalid")
    if not isinstance(value.get("updated_at"), str):
        raise CandidateValidationError("candidate status is invalid")
    progress = value.get("progress")
    if progress is not None:
        if not isinstance(progress, Mapping) or not set(progress).issubset(
            {"completed", "total", "message"}
        ):
            raise CandidateValidationError("candidate progress is invalid")
        for key in ("completed", "total"):
            number = progress.get(key)
            if (
                isinstance(number, bool)
                or not isinstance(number, (int, float))
                or not math.isfinite(float(number))
                or number < 0
            ):
                raise CandidateValidationError("candidate progress is invalid")
        if "message" in progress and (
            not isinstance(progress["message"], str) or len(progress["message"]) > 300
        ):
            raise CandidateValidationError("candidate progress is invalid")
    return dict(value)


def load_run(candidate_root: Path, run_id: str) -> dict[str, Any]:
    run_dir = candidate_run_dir(candidate_root, run_id)
    intake = _read_object(_confined(run_dir, "intake.json"), "candidate intake")
    if (
        intake.get("schema_version") != RUN_SCHEMA_VERSION
        or intake.get("run_id") != run_id
        or not isinstance(intake.get("created_at"), str)
    ):
        raise CandidateValidationError("candidate intake is invalid")
    file = _validated_file(intake.get("file"))
    rights = _validated_rights(intake.get("rights"))
    upload = _validate_upload(
        _read_object(_confined(run_dir, "upload", "progress.json"), "upload progress"),
        file["size_bytes"],
    )
    status = _validate_status(
        _read_object(_confined(run_dir, "status.json"), "candidate status")
    )
    manifest_path = _confined(run_dir, "manifest.json")
    manifest = _read_object(manifest_path, "candidate manifest") if manifest_path.is_file() else None
    finalized_source = _confined(run_dir, "source", "source.media")
    if manifest is not None:
        _validate_manifest(manifest, run_id, file["size_bytes"])
        if (
            not finalized_source.is_file()
            or finalized_source.stat().st_size != file["size_bytes"]
        ):
            raise CandidateConflictError("finalized source is missing or changed")
    return {
        "run_id": run_id,
        "run_dir": run_dir,
        "source_path": finalized_source,
        "intake": {**intake, "file": file, "rights": rights},
        "upload": upload,
        "status": status,
        "manifest": manifest,
    }


def list_candidate_runs(candidate_root: Path) -> Iterator[dict[str, Any]]:
    try:
        root = _candidate_root(candidate_root)
    except CandidateNotFoundError:
        return
    for entry in sorted(root.iterdir(), key=lambda item: item.name, reverse=True):
        if not entry.is_dir() or _is_link(entry) or not _SAFE_ID.fullmatch(entry.name):
            continue
        try:
            yield load_run(root, entry.name)
        except CandidateArtifactError:
            continue


class _CandidateRunLock:
    def __init__(self, run_dir: Path):
        self.run_dir = run_dir.expanduser().resolve()
        self._handle: BinaryIO | None = None

    def __enter__(self) -> "_CandidateRunLock":
        lock = _confined(self.run_dir, "worker.lock")
        if _is_link(lock) or (lock.exists() and lock.stat().st_nlink != 1):
            raise CandidateValidationError("candidate lock must not be linked")
        handle = lock.open("a+b")
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
            os.fsync(handle.fileno())
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            handle.close()
            if exc.errno in {errno.EACCES, errno.EAGAIN} or getattr(
                exc, "winerror", None
            ) in {33, 36}:
                raise CandidateBusyError("candidate analysis is already running") from exc
            raise
        self._handle = handle
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self._handle is None:
            return
        try:
            self._handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        finally:
            self._handle.close()
            self._handle = None


def candidate_run_lock(run_dir: Path) -> _CandidateRunLock:
    return _CandidateRunLock(run_dir)


def candidate_worker_active(run_dir: Path) -> bool:
    try:
        with candidate_run_lock(run_dir):
            return False
    except CandidateBusyError:
        return True


def append_upload_chunk(
    candidate_root: Path,
    run_id: str,
    *,
    index: int,
    start: int,
    end: int,
    total: int,
    data: bytes,
    chunk_sha256: str,
) -> dict[str, Any]:
    run = load_run(candidate_root, run_id)
    run_dir = Path(run["run_dir"])
    with candidate_run_lock(run_dir):
        run = load_run(candidate_root, run_id)
        upload = dict(run["upload"])
        expected_total = int(run["intake"]["file"]["size_bytes"])
        if run["manifest"] is not None:
            raise CandidateConflictError("source is already finalized")
        if (
            isinstance(index, bool)
            or not isinstance(index, int)
            or index < 0
            or isinstance(start, bool)
            or isinstance(end, bool)
            or not isinstance(start, int)
            or not isinstance(end, int)
            or total != expected_total
            or start != index * UPLOAD_CHUNK_BYTES
            or end <= start
            or end > total
            or end - start != len(data)
            or len(data) > UPLOAD_CHUNK_BYTES
            or (end < total and len(data) != UPLOAD_CHUNK_BYTES)
            or not isinstance(chunk_sha256, str)
            or not _SHA256.fullmatch(chunk_sha256.lower())
            or _sha256_bytes(data) != chunk_sha256.lower()
        ):
            raise CandidateValidationError("invalid upload chunk")
        part = _confined(run_dir, "upload", "source.part")
        part.parent.mkdir(parents=True, exist_ok=True)
        received = int(upload["received_bytes"])
        actual_size = part.stat().st_size if part.exists() else 0
        if actual_size > received:
            with part.open("r+b") as handle:
                handle.truncate(received)
                handle.flush()
                os.fsync(handle.fileno())
            actual_size = received
        if actual_size != received:
            raise CandidateConflictError("upload bytes do not match committed progress")
        if index < upload["next_chunk_index"]:
            if end > received:
                raise CandidateConflictError("upload retry does not match committed progress")
            with part.open("rb") as handle:
                handle.seek(start)
                existing = handle.read(end - start)
            if _sha256_bytes(existing) != chunk_sha256.lower():
                raise CandidateConflictError("upload retry has different bytes")
            return load_run(candidate_root, run_id)
        if index != upload["next_chunk_index"] or start != received:
            raise CandidateConflictError("upload offset does not match server progress")
        with part.open("ab") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        upload.update(
            {
                "received_bytes": end,
                "next_chunk_index": index + 1,
                "complete": end == total,
            }
        )
        _atomic_json(_confined(run_dir, "upload", "progress.json"), upload)
        update_status(
            run_dir,
            state="uploading",
            stage="upload",
            progress={"completed": end, "total": total},
        )
        return load_run(candidate_root, run_id)


def _resolve_ffprobe(explicit: Path | None = None) -> Path:
    requested = explicit or (
        Path(os.environ["SHORT_FACTORY_FFPROBE"])
        if os.environ.get("SHORT_FACTORY_FFPROBE")
        else None
    )
    found = str(requested) if requested else shutil.which("ffprobe")
    if not found or not Path(found).expanduser().is_file():
        raise CandidateConflictError("ffprobe is not available")
    return Path(found).expanduser().resolve()


def _probe_media(path: Path, *, ffprobe: Path | None = None) -> dict[str, Any]:
    command = [
        str(_resolve_ffprobe(ffprobe)),
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=codec_type",
        "-of",
        "json",
        str(path),
    ]
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CandidateValidationError("media validation failed") from exc
    if result.returncode != 0:
        raise CandidateValidationError("dropped file is not readable media")
    try:
        value = json.loads(result.stdout)
        duration = float(value["format"]["duration"])
        stream_types = {item.get("codec_type") for item in value.get("streams", [])}
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise CandidateValidationError("media metadata is invalid") from exc
    if not math.isfinite(duration) or duration <= 0:
        raise CandidateValidationError("media duration is invalid")
    if not {"video", "audio"}.issubset(stream_types):
        raise CandidateValidationError("candidate source requires video and audio")
    return {"duration_seconds": duration, "streams": ["audio", "video"]}


def _validate_manifest(value: Mapping[str, Any], run_id: str, expected_size: int) -> None:
    if value.get("schema_version") != RUN_SCHEMA_VERSION or value.get("run_id") != run_id:
        raise CandidateValidationError("candidate manifest is invalid")
    source = value.get("source")
    if not isinstance(source, Mapping) or set(source) != {
        "path",
        "sha256",
        "size_bytes",
        "duration_seconds",
        "streams",
    }:
        raise CandidateValidationError("candidate source manifest is invalid")
    duration = source["duration_seconds"]
    if (
        source["path"] != "source/source.media"
        or source["size_bytes"] != expected_size
        or not isinstance(source["sha256"], str)
        or not _SHA256.fullmatch(source["sha256"])
        or isinstance(duration, bool)
        or not isinstance(duration, (int, float))
        or not math.isfinite(float(duration))
        or duration <= 0
        or source["streams"] != ["audio", "video"]
    ):
        raise CandidateValidationError("candidate source manifest is invalid")


def finalize_upload(
    candidate_root: Path,
    run_id: str,
    *,
    size_bytes: int,
    chunk_count: int,
    ffprobe: Path | None = None,
) -> dict[str, Any]:
    run = load_run(candidate_root, run_id)
    run_dir = Path(run["run_dir"])
    with candidate_run_lock(run_dir):
        run = load_run(candidate_root, run_id)
        expected_size = int(run["intake"]["file"]["size_bytes"])
        expected_chunks = math.ceil(expected_size / UPLOAD_CHUNK_BYTES)
        if size_bytes != expected_size or chunk_count != expected_chunks:
            raise CandidateValidationError("upload finalization does not match intake")
        if run["manifest"] is not None:
            final = source_path(run_dir)
            if final.stat().st_size != expected_size or _sha256(final) != run["manifest"]["source"]["sha256"]:
                raise CandidateConflictError("finalized source identity changed")
            if run["status"]["state"] in {"created", "uploading"}:
                update_status(
                    run_dir,
                    state="finalized",
                    stage="finalized",
                    progress={"completed": 1, "total": 1},
                )
                return load_run(candidate_root, run_id)
            return run
        upload = run["upload"]
        if not upload["complete"] or upload["received_bytes"] != expected_size:
            raise CandidateConflictError("upload is incomplete")
        if shutil.disk_usage(run_dir).free < _required_work_free(expected_size):
            raise CandidateConflictError(
                "insufficient disk space for transcription and previews"
            )
        part = _confined(run_dir, "upload", "source.part")
        destination = _confined(run_dir, "source", "source.media")
        uploaded = part if part.is_file() else destination
        if not uploaded.is_file() or uploaded.stat().st_size != expected_size:
            raise CandidateConflictError("uploaded bytes are incomplete")
        media = _probe_media(uploaded, ffprobe=ffprobe)
        digest = _sha256(uploaded)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if uploaded == part:
            os.replace(part, destination)
        manifest = {
            "schema_version": RUN_SCHEMA_VERSION,
            "run_id": run_id,
            "finalized_at": _now(),
            "source": {
                "path": "source/source.media",
                "sha256": digest,
                "size_bytes": expected_size,
                "duration_seconds": media["duration_seconds"],
                "streams": media["streams"],
            },
        }
        _atomic_json(_confined(run_dir, "manifest.json"), manifest)
        update_status(
            run_dir,
            state="finalized",
            stage="finalized",
            progress={"completed": 1, "total": 1},
        )
        return load_run(candidate_root, run_id)


def update_status(
    run_dir: Path,
    *,
    state: str,
    stage: str,
    progress: Mapping[str, Any] | None,
    candidate_set_id: str | None = None,
    candidate_count: int | None = None,
    error: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if state not in _STATES or stage not in _STAGES:
        raise CandidateValidationError("candidate status transition is invalid")
    value: dict[str, Any] = {
        "schema_version": RUN_SCHEMA_VERSION,
        "state": state,
        "stage": stage,
        "updated_at": _now(),
        "progress": dict(progress) if progress is not None else None,
    }
    if candidate_set_id is not None:
        value["candidate_set_id"] = _validate_id(candidate_set_id, "candidate set id")
    if candidate_count is not None:
        if isinstance(candidate_count, bool) or not isinstance(candidate_count, int) or not 0 <= candidate_count <= MAX_CANDIDATES:
            raise CandidateValidationError("candidate count is invalid")
        value["candidate_count"] = candidate_count
    if error is not None:
        if (
            not isinstance(error, Mapping)
            or not isinstance(error.get("code"), str)
            or not isinstance(error.get("message"), str)
            or len(error["code"]) > 100
            or len(error["message"]) > 1000
        ):
            raise CandidateValidationError("candidate error is invalid")
        value["error"] = {"code": error["code"], "message": error["message"]}
    _validate_status(value)
    _atomic_json(_confined(run_dir, "status.json"), value)
    return value


def request_cancel(run_dir: Path) -> None:
    _atomic_json(_confined(run_dir, "cancel.json"), {"requested": True, "at": _now()})


def clear_cancel(run_dir: Path) -> None:
    _confined(run_dir, "cancel.json").unlink(missing_ok=True)


def cancel_requested(run_dir: Path) -> bool:
    path = _confined(run_dir, "cancel.json")
    if not path.is_file():
        return False
    value = _read_object(path, "cancel request")
    return value.get("requested") is True


def prepare_analysis(candidate_root: Path, run_id: str) -> dict[str, Any]:
    run = load_run(candidate_root, run_id)
    run_dir = Path(run["run_dir"])
    with candidate_run_lock(run_dir):
        run = load_run(candidate_root, run_id)
        if run["manifest"] is None:
            raise CandidateConflictError("source upload is not finalized")
        if run["status"]["state"] == "complete":
            raise CandidateConflictError("candidate analysis is already complete")
        clear_cancel(run_dir)
        update_status(
            run_dir,
            state="queued",
            stage="queued",
            progress={"completed": 0, "total": 1},
        )
        return load_run(candidate_root, run_id)


def publish_candidate_set(
    run_dir: Path,
    document: Mapping[str, Any],
    *,
    preview_sources: Mapping[str, Path],
    ffprobe: Path | None = None,
) -> dict[str, Any]:
    run_id = _validate_id(document.get("run_id"), "candidate run id")
    if run_dir.name != run_id:
        raise CandidateValidationError("candidate set run id mismatch")
    manifest = _read_object(_confined(run_dir, "manifest.json"), "candidate manifest")
    source = manifest.get("source")
    if not isinstance(source, Mapping):
        raise CandidateValidationError("candidate source manifest is invalid")
    selected = {
        key: document.get(key)
        for key in (
            "schema_version",
            "assessment",
            "provider",
            "model",
            "prompt_version",
            "candidates",
        )
    }
    try:
        validate_candidate_set(
            selected,
            source_duration=float(source["duration_seconds"]),
            maximum=MAX_CANDIDATES,
        )
    except (CandidateSelectionError, KeyError, TypeError, ValueError) as exc:
        raise CandidateValidationError("candidate set is invalid") from exc
    if document.get("source_sha256") != source.get("sha256"):
        raise CandidateConflictError("candidate set source identity mismatch")
    candidates = [dict(item) for item in selected["candidates"]]
    identifiers = {item["candidate_id"] for item in candidates}
    if set(preview_sources) != identifiers:
        raise CandidateValidationError("candidate previews do not match candidates")
    set_id = f"set-{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{secrets.token_hex(5)}"
    sets = _confined(run_dir, "candidate-set")
    sets.mkdir(parents=True, exist_ok=True)
    temporary = sets / f".{set_id}.{secrets.token_hex(4)}.tmp"
    destination = sets / set_id
    temporary.mkdir()
    try:
        for candidate in candidates:
            identifier = _validate_id(candidate["candidate_id"], "candidate id")
            raw_preview = Path(preview_sources[identifier]).expanduser().resolve()
            try:
                raw_preview.relative_to(run_dir.resolve())
            except ValueError as exc:
                raise CandidateValidationError("preview source escapes candidate run") from exc
            if not raw_preview.is_file() or raw_preview.stat().st_size <= 0:
                raise CandidateValidationError("candidate preview is missing")
            media = _probe_media(raw_preview, ffprobe=ffprobe)
            if abs(float(media["duration_seconds"]) - float(candidate["duration"])) > 1.0:
                raise CandidateValidationError("candidate preview duration mismatch")
            filename = f"{identifier}.mp4"
            copied = temporary / filename
            shutil.copyfile(raw_preview, copied)
            candidate["preview"] = {
                "path": filename,
                "sha256": _sha256(copied),
                "size_bytes": copied.stat().st_size,
                "duration_seconds": media["duration_seconds"],
            }
        published = {
            **selected,
            "candidate_set_id": set_id,
            "run_id": run_id,
            "source_sha256": source["sha256"],
            "created_at": _now(),
            "candidates": candidates,
        }
        _atomic_json(temporary / "candidates.json", published)
        os.replace(temporary, destination)
        return load_candidate_set(run_dir, set_id)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def load_candidate_set(run_dir: Path, set_id: str | None = None) -> dict[str, Any]:
    if set_id is None:
        status = _validate_status(_read_object(_confined(run_dir, "status.json"), "candidate status"))
        set_id = status.get("candidate_set_id")
    if not isinstance(set_id, str):
        raise CandidateNotFoundError("candidate set is not published")
    _validate_id(set_id, "candidate set id")
    set_dir = _confined(run_dir, "candidate-set", set_id)
    document = _read_object(_confined(set_dir, "candidates.json"), "candidate set")
    manifest = _read_object(_confined(run_dir, "manifest.json"), "candidate manifest")
    source = manifest.get("source")
    if (
        document.get("candidate_set_id") != set_id
        or document.get("run_id") != run_dir.name
        or not isinstance(source, Mapping)
        or document.get("source_sha256") != source.get("sha256")
    ):
        raise CandidateValidationError("candidate set identity is invalid")
    selected = {
        key: document.get(key)
        for key in (
            "schema_version",
            "assessment",
            "provider",
            "model",
            "prompt_version",
            "candidates",
        )
    }
    clean_candidates: list[dict[str, Any]] = []
    raw_candidates = document.get("candidates")
    if not isinstance(raw_candidates, list):
        raise CandidateValidationError("candidate set is invalid")
    for raw in raw_candidates:
        if not isinstance(raw, Mapping) or not isinstance(raw.get("preview"), Mapping):
            raise CandidateValidationError("candidate preview metadata is invalid")
        clean = {key: value for key, value in raw.items() if key != "preview"}
        clean_candidates.append(clean)
    selected["candidates"] = clean_candidates
    try:
        validate_candidate_set(
            selected,
            source_duration=float(source["duration_seconds"]),
            maximum=MAX_CANDIDATES,
        )
    except (CandidateSelectionError, TypeError, ValueError) as exc:
        raise CandidateValidationError("candidate set is invalid") from exc
    for raw in raw_candidates:
        preview = raw["preview"]
        if set(preview) != {"path", "sha256", "size_bytes", "duration_seconds"}:
            raise CandidateValidationError("candidate preview metadata is invalid")
        candidate_id = raw["candidate_id"]
        if preview["path"] != f"{candidate_id}.mp4" or not _SHA256.fullmatch(str(preview["sha256"])):
            raise CandidateValidationError("candidate preview metadata is invalid")
        path = _confined(set_dir, preview["path"])
        if (
            not path.is_file()
            or path.stat().st_size != preview["size_bytes"]
            or _sha256(path) != preview["sha256"]
        ):
            raise CandidateConflictError("candidate preview identity changed")
    return document


def candidate_preview(
    candidate_root: Path, run_id: str, candidate_id: str
) -> tuple[dict[str, Any], Path]:
    run = load_run(candidate_root, run_id)
    run_dir = Path(run["run_dir"])
    document = load_candidate_set(run_dir)
    _validate_id(candidate_id, "candidate id")
    for candidate in document["candidates"]:
        if candidate.get("candidate_id") == candidate_id:
            set_dir = _confined(run_dir, "candidate-set", document["candidate_set_id"])
            return candidate, _confined(set_dir, candidate["preview"]["path"])
    raise CandidateNotFoundError("candidate preview not found")


def project_candidate_run(candidate_root: Path, run_id: str) -> dict[str, Any]:
    run = load_run(candidate_root, run_id)
    status = run["status"]
    public_status = status["state"]
    if status["state"] in {"queued", "processing"}:
        try:
            updated = datetime.fromisoformat(status["updated_at"])
            age_seconds = (datetime.now(timezone.utc) - updated).total_seconds()
        except (TypeError, ValueError):
            age_seconds = 0.0
        if age_seconds > 15.0 and not candidate_worker_active(Path(run["run_dir"])):
            public_status = "interrupted"
    if status["state"] == "processing":
        if public_status != "interrupted":
            public_status = {
                "source_validation": "validating",
                "audio": "extracting_audio",
                "transcription": "transcribing",
                "selection": "analyzing",
                "preview": "building_previews",
                "publish": "building_previews",
            }.get(status["stage"], "processing")
    result: dict[str, Any] = {
        "run_id": run_id,
        "state": status["state"],
        "status": public_status,
        "stage": status["stage"],
        "file": run["intake"]["file"],
        "upload": run["upload"],
        "progress": status.get("progress"),
        "source_ready": run["manifest"] is not None,
    }
    if run["manifest"] is not None:
        source = run["manifest"].get("source")
        if isinstance(source, Mapping):
            result["source_duration_seconds"] = source.get("duration_seconds")
            result["source_video_url"] = (
                f"/api/candidate-runs/{run_id}/source/video"
            )
    authorization = load_external_ai_authorization(Path(run["run_dir"]))
    if authorization is not None:
        result["selection"] = {
            "provider": authorization["provider"],
            "model": authorization["model"],
            "payload_scope": authorization["payload_scope"],
        }
    if status["state"] == "failed":
        result["error"] = {
            "code": "analysis_failed",
            "message": "ローカル分析を完了できませんでした。状態を確認して再開できます。",
        }
    if status["state"] == "complete":
        document = load_candidate_set(Path(run["run_dir"]))
        result.update(
            {
                "assessment": document["assessment"],
                "provider": {"name": document["provider"], "model": document["model"]},
                "prompt_version": document["prompt_version"],
                "candidates": [
                    {key: value for key, value in candidate.items() if key != "preview"}
                    for candidate in document["candidates"]
                ],
            }
        )
    return result
