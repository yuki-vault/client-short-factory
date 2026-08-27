from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from .utils import atomic_write_json, read_json


WORKFLOW_MANIFEST_VERSION = 3
CAPTION_SCHEMA_VERSION = 1
RENDER_SCHEMA_VERSION = 1

_SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


class WorkflowError(RuntimeError):
    status_code = 400


class NotFoundError(WorkflowError):
    status_code = 404


class ConflictError(WorkflowError):
    status_code = 409


class LegacyJobError(ConflictError):
    pass


class ValidationError(WorkflowError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_safe_id(value: str, kind: str) -> str:
    base_name = value.split(".", 1)[0].upper() if isinstance(value, str) else ""
    if (
        not isinstance(value, str)
        or not _SAFE_ID.fullmatch(value)
        or value.endswith(".")
        or base_name in _WINDOWS_RESERVED
    ):
        raise ValidationError(f"invalid {kind}")
    return value


def confined_job_path(job_dir: Path, *parts: str) -> Path:
    """Resolve an artifact path without following a nested link outside the job."""
    root = job_dir.expanduser().resolve()
    candidate = root.joinpath(*parts).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValidationError("artifact path escapes its job") from exc
    return candidate


def safe_job_dir(jobs_root: Path, job_id: str) -> Path:
    validate_safe_id(job_id, "job id")
    root = jobs_root.expanduser().resolve()
    candidate = (root / job_id).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValidationError("job path escapes jobs root") from exc
    if not candidate.is_dir():
        raise NotFoundError(f"job not found: {job_id}")
    return candidate


def load_job(job_dir: Path) -> dict[str, Any]:
    validate_safe_id(job_dir.name, "job id")
    path = confined_job_path(job_dir, "job.json")
    if not path.is_file():
        raise NotFoundError("job.json is missing")
    value = read_json(path)
    if not isinstance(value, Mapping):
        raise ValidationError("job metadata must be an object")
    if value.get("job_id") != job_dir.name:
        raise ValidationError("job id does not match its directory")
    return dict(value)


def ensure_workflow_job(job_dir: Path) -> dict[str, Any]:
    job = load_job(job_dir)
    if job.get("version") != WORKFLOW_MANIFEST_VERSION:
        raise LegacyJobError("legacy jobs are read-only and are not migrated")
    duration = job.get("duration_seconds")
    if (
        not isinstance(duration, (int, float))
        or isinstance(duration, bool)
        or not math.isfinite(float(duration))
        or duration <= 0
    ):
        raise ValidationError("job duration must be positive")
    return job


def _caption_revisions_dir(job_dir: Path) -> Path:
    return confined_job_path(job_dir, "subtitles", "revisions")


def _caption_revision_name(revision: int) -> str:
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise ValidationError("caption revision must be a positive integer")
    return f"{revision:06d}"


def _caption_revision_path(job_dir: Path, revision: int) -> Path:
    return confined_job_path(
        job_dir,
        "subtitles",
        "revisions",
        _caption_revision_name(revision),
        "captions.json",
    )


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def caption_hash(document: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(document)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _caption_subtitle_config(job: Mapping[str, Any]) -> Mapping[str, Any]:
    if "config" not in job:
        return {}
    config = job.get("config")
    if not isinstance(config, Mapping):
        raise ValidationError("job config must be an object")
    if "subtitle" not in config:
        return {}
    subtitle = config.get("subtitle")
    if not isinstance(subtitle, Mapping):
        raise ValidationError("job subtitle config must be an object")
    return subtitle


def caption_duration_floor(job: Mapping[str, Any]) -> float:
    minimum = 0.7
    subtitle = _caption_subtitle_config(job)
    raw = subtitle.get("min_cue_seconds", minimum)
    if (
        not isinstance(raw, (int, float))
        or isinstance(raw, bool)
        or not math.isfinite(float(raw))
        or float(raw) <= 0.05
    ):
        raise ValidationError("invalid minimum caption duration")
    minimum = float(raw)
    return minimum - 0.05


def caption_layout_limits(job: Mapping[str, Any]) -> tuple[int, int]:
    subtitle = _caption_subtitle_config(job)
    max_chars = subtitle.get("max_chars_per_line", 15)
    max_lines = subtitle.get("max_lines", 2)
    if (
        not isinstance(max_chars, int)
        or isinstance(max_chars, bool)
        or not 1 <= max_chars <= 500
    ):
        raise ValidationError("invalid maximum caption line length")
    if (
        not isinstance(max_lines, int)
        or isinstance(max_lines, bool)
        or not 1 <= max_lines <= 500
    ):
        raise ValidationError("invalid maximum caption line count")
    return max_chars, max_lines


def _normalized_cues(
    cues: Iterable[Mapping[str, Any]],
    *,
    duration: float,
    minimum_duration: float,
    max_chars_per_line: int,
    max_lines: int,
) -> list[dict[str, Any]]:
    if isinstance(cues, (str, bytes, Mapping)):
        raise ValidationError("cues must be a list")
    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    previous_end = 0.0
    for index, raw in enumerate(cues):
        if not isinstance(raw, Mapping):
            raise ValidationError(f"cue {index + 1} must be an object")
        if set(raw) != {"id", "start", "end", "text"}:
            raise ValidationError(f"cue {index + 1} has invalid fields")
        cue_id = validate_safe_id(raw.get("id"), "cue id")
        if cue_id in seen_ids:
            raise ValidationError(f"duplicate cue id: {cue_id}")
        seen_ids.add(cue_id)
        start = raw.get("start")
        end = raw.get("end")
        text = raw.get("text")
        if (
            not isinstance(start, (int, float))
            or isinstance(start, bool)
            or not isinstance(end, (int, float))
            or isinstance(end, bool)
        ):
            raise ValidationError(f"cue {cue_id} has invalid timing")
        raw_start = float(start)
        raw_end = float(end)
        if not math.isfinite(raw_start) or not math.isfinite(raw_end):
            raise ValidationError(f"cue {cue_id} has invalid timing")
        if raw_start < 0 or raw_end > duration:
            raise ValidationError(f"cue {cue_id} is outside the job duration")
        start_value = round(raw_start, 3)
        end_value = round(raw_end, 3)
        if start_value < 0 or end_value <= start_value or end_value > duration + 0.001:
            raise ValidationError(f"cue {cue_id} is outside the job duration")
        if end_value - start_value < minimum_duration:
            raise ValidationError(f"cue {cue_id} duration is too short")
        if index and start_value < previous_end:
            raise ValidationError(f"cue {cue_id} overlaps the previous cue")
        if not isinstance(text, str) or not text.strip() or "\x00" in text:
            raise ValidationError(f"cue {cue_id} text must not be empty")
        if len(text) > 500:
            raise ValidationError(f"cue {cue_id} text is too long")
        lines = text.splitlines()
        if len(lines) > max_lines:
            raise ValidationError(f"cue {cue_id} has too many lines")
        if any(len(line) > max_chars_per_line for line in lines):
            raise ValidationError(f"cue {cue_id} has a line that is too long")
        normalized.append(
            {
                "id": cue_id,
                "start": start_value,
                "end": end_value,
                "text": text,
            }
        )
        previous_end = end_value
    if not normalized:
        raise ValidationError("at least one caption cue is required")
    return normalized


def _normalized_edit_cues(
    current: Mapping[str, Any],
    cues: Iterable[Mapping[str, Any]],
    *,
    duration: float,
    minimum_duration: float,
    max_chars_per_line: int,
    max_lines: int,
    revision: int,
) -> list[dict[str, Any]]:
    if isinstance(cues, (str, bytes, Mapping)):
        raise ValidationError("cues must be a list")
    raw_cues = list(cues)
    if not 1 <= len(raw_cues) <= 1000:
        raise ValidationError("caption cues must contain between 1 and 1000 items")

    current_cues = current.get("cues")
    if not isinstance(current_cues, list):
        raise ValidationError("current caption cues are invalid")
    current_ids = [cue.get("id") for cue in current_cues]
    if any(not isinstance(cue_id, str) for cue_id in current_ids):
        raise ValidationError("current caption cue IDs are invalid")
    current_id_set = set(current_ids)
    supplied_existing_ids: list[str] = []
    seen_existing_ids: set[str] = set()
    assigned_ids = set(current_id_set)
    next_new_ordinal = 1
    assigned_cues: list[dict[str, Any]] = []

    for index, raw in enumerate(raw_cues, start=1):
        if not isinstance(raw, Mapping):
            raise ValidationError(f"cue {index} must be an object")
        if set(raw) != {"id", "start", "end", "text"}:
            raise ValidationError(f"cue {index} has invalid fields")
        cue_id = raw.get("id")
        if cue_id is None:
            while True:
                candidate = (
                    f"cue-human-r{revision:09d}-{next_new_ordinal:04d}"
                )
                next_new_ordinal += 1
                if candidate not in assigned_ids:
                    cue_id = candidate
                    assigned_ids.add(candidate)
                    break
        else:
            cue_id = validate_safe_id(cue_id, "cue id")
            if cue_id not in current_id_set:
                raise ValidationError(f"unknown cue id: {cue_id}")
            if cue_id in seen_existing_ids:
                raise ValidationError(f"duplicate cue id: {cue_id}")
            seen_existing_ids.add(cue_id)
            supplied_existing_ids.append(cue_id)
        assigned_cues.append(
            {
                "id": cue_id,
                "start": raw.get("start"),
                "end": raw.get("end"),
                "text": raw.get("text"),
            }
        )

    if supplied_existing_ids != current_ids:
        if set(supplied_existing_ids) != current_id_set:
            raise ValidationError("all existing cue IDs must be preserved")
        raise ValidationError("existing cue order must be preserved")
    return _normalized_cues(
        assigned_cues,
        duration=duration,
        minimum_duration=minimum_duration,
        max_chars_per_line=max_chars_per_line,
        max_lines=max_lines,
    )


def validate_caption_document(
    document: Mapping[str, Any],
    *,
    job: Mapping[str, Any],
    expected_revision: int | None = None,
) -> dict[str, Any]:
    if not isinstance(document, Mapping):
        raise ValidationError("caption document must be an object")
    if document.get("schema_version") != CAPTION_SCHEMA_VERSION:
        raise ValidationError("unsupported caption schema version")
    if document.get("job_id") != job.get("job_id"):
        raise ValidationError("caption job id mismatch")
    revision = document.get("revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise ValidationError("caption revision must be a positive integer")
    if expected_revision is not None and revision != expected_revision:
        raise ValidationError("caption revision mismatch")
    base_revision = document.get("base_revision")
    if base_revision is not None and (
        not isinstance(base_revision, int)
        or isinstance(base_revision, bool)
        or base_revision < 1
        or base_revision >= revision
    ):
        raise ValidationError("invalid base caption revision")
    max_chars_per_line, max_lines = caption_layout_limits(job)
    normalized = dict(document)
    normalized["cues"] = _normalized_cues(
        document.get("cues", []),
        duration=float(job["duration_seconds"]),
        minimum_duration=caption_duration_floor(job),
        max_chars_per_line=max_chars_per_line,
        max_lines=max_lines,
    )
    return normalized


def load_caption_revision(job_dir: Path, revision: int) -> dict[str, Any]:
    job = ensure_workflow_job(job_dir)
    path = _caption_revision_path(job_dir, revision)
    if not path.is_file():
        raise NotFoundError(f"caption revision not found: {revision}")
    return validate_caption_document(
        read_json(path),
        job=job,
        expected_revision=revision,
    )


def _current_caption_pointer(job_dir: Path) -> dict[str, Any]:
    path = confined_job_path(job_dir, "subtitles", "current.json")
    if not path.is_file():
        raise NotFoundError("current caption revision is not initialized")
    pointer = read_json(path)
    if not isinstance(pointer, Mapping):
        raise ValidationError("current caption pointer must be an object")
    revision = pointer.get("revision")
    if not isinstance(revision, int) or isinstance(revision, bool):
        raise ValidationError("invalid current caption pointer")
    document = load_caption_revision(job_dir, revision)
    actual_hash = caption_hash(document)
    if pointer.get("caption_hash") != actual_hash:
        raise ValidationError("current caption pointer hash mismatch")
    return pointer


def load_current_caption(job_dir: Path) -> dict[str, Any]:
    pointer = _current_caption_pointer(job_dir)
    return load_caption_revision(job_dir, int(pointer["revision"]))


def list_caption_revisions(job_dir: Path) -> list[int]:
    ensure_workflow_job(job_dir)
    root = _caption_revisions_dir(job_dir)
    if not root.is_dir():
        return []
    revisions: list[int] = []
    for entry in root.iterdir():
        if not re.fullmatch(r"\d{6}", entry.name):
            continue
        try:
            revision_dir = confined_job_path(
                job_dir, "subtitles", "revisions", entry.name
            )
            revision_file = confined_job_path(
                job_dir,
                "subtitles",
                "revisions",
                entry.name,
                "captions.json",
            )
        except ValidationError:
            continue
        if revision_dir.is_dir() and revision_file.is_file():
            revisions.append(int(entry.name))
    return sorted(revisions)


def _write_json_file(path: Path, value: Mapping[str, Any]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as destination:
        json.dump(value, destination, ensure_ascii=False, indent=2, allow_nan=False)
        destination.write("\n")
        destination.flush()
        os.fsync(destination.fileno())


def _publish_caption_document(
    job_dir: Path,
    document: Mapping[str, Any],
    *,
    failpoint: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    job = ensure_workflow_job(job_dir)
    normalized = validate_caption_document(document, job=job)
    revision = int(normalized["revision"])
    revisions_dir = _caption_revisions_dir(job_dir)
    revisions_dir.mkdir(parents=True, exist_ok=True)
    final_dir = revisions_dir / _caption_revision_name(revision)
    if final_dir.exists():
        raise ConflictError(f"caption revision already exists: {revision}")
    temporary = revisions_dir / f".{final_dir.name}.tmp-{uuid.uuid4().hex}"
    temporary.mkdir()
    published = False
    try:
        _write_json_file(temporary / "captions.json", normalized)
        validate_caption_document(
            read_json(temporary / "captions.json"),
            job=job,
            expected_revision=revision,
        )
        os.replace(temporary, final_dir)
        published = True
        pointer = {
            "schema_version": 1,
            "job_id": job["job_id"],
            "revision": revision,
            "caption_hash": caption_hash(normalized),
            "updated_at": _now(),
        }
        atomic_write_json(
            confined_job_path(job_dir, "subtitles", "recovery.json"),
            {
                "schema_version": 1,
                "job_id": job["job_id"],
                "latest_published_revision": revision,
                "caption_hash": pointer["caption_hash"],
                "updated_at": pointer["updated_at"],
            },
        )
        if failpoint:
            failpoint("caption_after_revision_publish")
        atomic_write_json(confined_job_path(job_dir, "subtitles", "current.json"), pointer)
        return normalized
    except BaseException:
        if not published and temporary.exists():
            shutil.rmtree(temporary)
        raise


def initialize_machine_revision(
    job_dir: Path,
    cues: Iterable[Mapping[str, Any]],
    *,
    failpoint: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    job = ensure_workflow_job(job_dir)
    current_path = confined_job_path(job_dir, "subtitles", "current.json")
    if current_path.is_file():
        return load_current_caption(job_dir)
    revision_one = _caption_revision_path(job_dir, 1)
    if revision_one.is_file():
        document = load_caption_revision(job_dir, 1)
        pointer = {
            "schema_version": 1,
            "job_id": job["job_id"],
            "revision": 1,
            "caption_hash": caption_hash(document),
            "updated_at": _now(),
        }
        atomic_write_json(confined_job_path(job_dir, "subtitles", "recovery.json"), {
            "schema_version": 1,
            "job_id": job["job_id"],
            "latest_published_revision": 1,
            "caption_hash": pointer["caption_hash"],
            "updated_at": pointer["updated_at"],
        })
        atomic_write_json(current_path, pointer)
        return document
    if list_caption_revisions(job_dir):
        raise ConflictError("caption revisions exist without a recoverable revision 1")
    normalized_cues = []
    for index, cue in enumerate(cues, start=1):
        normalized_cues.append(
            {
                "id": f"cue-{index:06d}",
                "start": cue["start"],
                "end": cue["end"],
                "text": cue["text"],
            }
        )
    document = {
        "schema_version": CAPTION_SCHEMA_VERSION,
        "job_id": job["job_id"],
        "revision": 1,
        "base_revision": None,
        "origin": "machine",
        "created_at": _now(),
        "cues": normalized_cues,
    }
    return _publish_caption_document(job_dir, document, failpoint=failpoint)


def save_caption_revision(
    job_dir: Path,
    *,
    base_revision: int,
    cues: Iterable[Mapping[str, Any]],
    failpoint: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    job = ensure_workflow_job(job_dir)
    current = load_current_caption(job_dir)
    if (
        not isinstance(base_revision, int)
        or isinstance(base_revision, bool)
        or base_revision < 1
    ):
        raise ValidationError("base_revision must be a positive integer")
    if int(current["revision"]) != base_revision:
        raise ConflictError("base_revision is stale")
    revisions = list_caption_revisions(job_dir)
    next_revision = (revisions[-1] if revisions else base_revision) + 1
    max_chars_per_line, max_lines = caption_layout_limits(job)
    normalized_cues = _normalized_edit_cues(
        current,
        cues,
        duration=float(job["duration_seconds"]),
        minimum_duration=caption_duration_floor(job),
        max_chars_per_line=max_chars_per_line,
        max_lines=max_lines,
        revision=next_revision,
    )
    if normalized_cues == current["cues"]:
        raise ValidationError("caption edit does not change any cue")
    document = {
        "schema_version": CAPTION_SCHEMA_VERSION,
        "job_id": job["job_id"],
        "revision": next_revision,
        "base_revision": base_revision,
        "origin": "human",
        "created_at": _now(),
        "cues": normalized_cues,
    }
    return _publish_caption_document(job_dir, document, failpoint=failpoint)


def _renders_dir(job_dir: Path) -> Path:
    return confined_job_path(job_dir, "renders")


def _validated_qc(path: Path) -> dict[str, Any]:
    qc = read_json(path)
    if not isinstance(qc, Mapping):
        raise ValidationError("render QC must be an object")
    checks = qc.get("checks")
    if (
        qc.get("schema_version") != 1
        or qc.get("passed") is not True
        or qc.get("technical_checks_passed") is not True
        or qc.get("content_review") != "pending"
        or not isinstance(checks, Mapping)
        or not checks
        or any(value is not True for value in checks.values())
    ):
        raise ValidationError("render QC is internally inconsistent")
    return dict(qc)


def load_render(job_dir: Path, render_id: str) -> dict[str, Any]:
    ensure_workflow_job(job_dir)
    validate_safe_id(render_id, "render id")
    render_dir = (_renders_dir(job_dir) / render_id).resolve()
    try:
        render_dir.relative_to(_renders_dir(job_dir).resolve())
    except ValueError as exc:
        raise ValidationError("render path escapes its job") from exc
    metadata_path = confined_job_path(
        job_dir, "renders", render_id, "render.json"
    )
    video_path = confined_job_path(job_dir, "renders", render_id, "short.mp4")
    qc_path = confined_job_path(job_dir, "renders", render_id, "qc.json")
    if not metadata_path.is_file() or not video_path.is_file() or not qc_path.is_file():
        raise NotFoundError(f"render not found: {render_id}")
    metadata = read_json(metadata_path)
    if not isinstance(metadata, Mapping):
        raise ValidationError("render metadata must be an object")
    if (
        metadata.get("schema_version") != RENDER_SCHEMA_VERSION
        or metadata.get("render_id") != render_id
        or metadata.get("job_id") != job_dir.name
    ):
        raise ValidationError("invalid render metadata")
    caption_revision = metadata.get("caption_revision")
    if (
        not isinstance(caption_revision, int)
        or isinstance(caption_revision, bool)
        or caption_revision < 1
    ):
        raise ValidationError("invalid render caption revision")
    caption = load_caption_revision(job_dir, caption_revision)
    if metadata.get("caption_hash") != caption_hash(caption):
        raise ValidationError("render caption hash mismatch")
    output_hash = metadata.get("output_hash")
    if not isinstance(output_hash, str) or not _SHA256.fullmatch(output_hash):
        raise ValidationError("invalid render output hash")
    if sha256_file(video_path) != output_hash:
        raise ConflictError("render output hash mismatch")
    _validated_qc(qc_path)
    if (
        metadata.get("technical_checks_passed") is not True
        or metadata.get("content_review") != "pending"
    ):
        raise ValidationError("render QC metadata mismatch")
    return metadata


def list_renders(job_dir: Path) -> list[dict[str, Any]]:
    ensure_workflow_job(job_dir)
    root = _renders_dir(job_dir)
    if not root.is_dir():
        return []
    values: list[dict[str, Any]] = []
    for entry in root.iterdir():
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        try:
            values.append(load_render(job_dir, entry.name))
        except (WorkflowError, OSError, TypeError, ValueError):
            continue
    return sorted(values, key=lambda value: str(value.get("created_at", "")))


def publish_render(
    job_dir: Path,
    *,
    caption_revision: int,
    renderer: Callable[[Path, Mapping[str, Any], Path], Mapping[str, Any]],
    failpoint: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    job = ensure_workflow_job(job_dir)
    caption = load_caption_revision(job_dir, caption_revision)
    render_id = (
        "render-"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        + "-"
        + uuid.uuid4().hex[:10]
    )
    renders_dir = _renders_dir(job_dir)
    renders_dir.mkdir(parents=True, exist_ok=True)
    final_dir = renders_dir / render_id
    temporary = renders_dir / f".{render_id}.tmp"
    temporary.mkdir()
    published = False
    try:
        renderer_result = dict(renderer(job_dir, caption, temporary))
        video_path = temporary / "short.mp4"
        qc_path = temporary / "qc.json"
        if not video_path.is_file() or video_path.stat().st_size == 0:
            raise ValidationError("renderer did not produce short.mp4")
        if not qc_path.is_file():
            raise ValidationError("renderer did not produce qc.json")
        _validated_qc(qc_path)
        output_hash = sha256_file(video_path)
        metadata = {
            "schema_version": RENDER_SCHEMA_VERSION,
            "render_id": render_id,
            "job_id": job["job_id"],
            "caption_revision": caption_revision,
            "caption_hash": caption_hash(caption),
            "output_hash": output_hash,
            "technical_checks_passed": True,
            "content_review": "pending",
            "created_at": _now(),
            "renderer": renderer_result,
        }
        _write_json_file(temporary / "render.json", metadata)
        if failpoint:
            failpoint("render_after_qc_before_publish")
        os.replace(temporary, final_dir)
        published = True
        return metadata
    except BaseException:
        if not published and temporary.exists():
            shutil.rmtree(temporary)
        raise


def project_job(job_dir: Path) -> dict[str, Any]:
    job = ensure_workflow_job(job_dir)
    caption = load_current_caption(job_dir)
    max_chars_per_line, max_lines = caption_layout_limits(job)
    current_revision = int(caption["revision"])
    renders: list[dict[str, Any]] = []
    for metadata in list_renders(job_dir):
        item = dict(metadata)
        item["is_current_caption"] = item.get("caption_revision") == current_revision
        item["video_url"] = (
            f"/api/jobs/{job['job_id']}/renders/{item['render_id']}/video"
        )
        renders.append(item)
    current_renders = [item for item in renders if item["is_current_caption"]]
    technical_state = "pending"
    if len(current_renders) == 1:
        technical_state = (
            "passed"
            if current_renders[0].get("technical_checks_passed") is True
            else "failed"
        )
    return {
        "job_id": job["job_id"],
        "duration_seconds": job["duration_seconds"],
        "caption_minimum_seconds": caption_duration_floor(job),
        "caption_max_chars_per_line": max_chars_per_line,
        "caption_max_lines": max_lines,
        "current_caption": {
            "revision": current_revision,
            "caption_hash": caption_hash(caption),
            "cues": caption["cues"],
        },
        "renders": renders,
        "current_caption_render_ids": [
            item["render_id"] for item in current_renders
        ],
        "technical_state": technical_state,
        "content_state": "pending",
        "can_approve": False,
    }


def list_workflow_jobs(jobs_root: Path) -> list[dict[str, Any]]:
    root = jobs_root.expanduser().resolve()
    if not root.is_dir():
        return []
    jobs: list[dict[str, Any]] = []
    for entry in sorted(root.iterdir(), key=lambda path: path.name.lower()):
        if not entry.is_dir():
            continue
        try:
            validate_safe_id(entry.name, "job id")
            jobs.append(project_job(safe_job_dir(root, entry.name)))
        except (WorkflowError, OSError, TypeError, ValueError):
            continue
    return jobs
