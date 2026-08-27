from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable, Mapping

from .artifacts import (
    ConflictError,
    NotFoundError,
    ValidationError,
    sha256_file,
    validate_safe_id,
)
from .composition_schema import (
    COMPILER_VERSION,
    assert_compiled_timeline,
    compile_edit_plan,
    content_hash,
    validate_edit_plan,
)
from .utils import atomic_write_json, read_json


COMPOSITION_PROJECT_SCHEMA_VERSION = 1
COMPOSITION_PROJECT_VERSION = 4
EDIT_REVISION_SCHEMA_VERSION = 1
COMPOSITION_RENDER_SCHEMA_VERSION = 1
RENDER_INPUT_SCHEMA_VERSION = 1
RENDER_PROFILE_VERSION = "c0-1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_link(path: Path) -> bool:
    is_junction = getattr(os.path, "isjunction", None)
    return path.is_symlink() or (callable(is_junction) and is_junction(path))


def _composition_root(value: Path, *, create: bool = False) -> Path:
    raw = value.expanduser()
    if create:
        raw.mkdir(parents=True, exist_ok=True)
    if not raw.is_dir():
        raise NotFoundError("composition projects root does not exist")
    if _is_link(raw):
        raise ValidationError("composition projects root must not be a link")
    return raw.resolve()


def composition_project_dir(
    projects_root: Path, project_id: str, *, create_root: bool = False
) -> Path:
    validate_safe_id(project_id, "composition project id")
    root = _composition_root(projects_root, create=create_root)
    raw = root / project_id
    if _is_link(raw):
        raise ValidationError("composition project directory must not be a link")
    resolved = raw.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValidationError("composition project escapes its root") from exc
    return resolved


def confined_composition_path(project_dir: Path, *parts: str) -> Path:
    root = project_dir.expanduser().resolve()
    candidate = root.joinpath(*parts).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValidationError("composition artifact escapes its project") from exc
    return candidate


def _write_json_file(path: Path, value: Mapping[str, Any]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as destination:
        json.dump(value, destination, ensure_ascii=False, indent=2, allow_nan=False)
        destination.write("\n")
        destination.flush()
        os.fsync(destination.fileno())


def _fraction(value: Any, label: str) -> Fraction:
    try:
        result = Fraction(str(value))
    except (ValueError, ZeroDivisionError) as exc:
        raise ValidationError(f"invalid {label}") from exc
    if result <= 0:
        raise ValidationError(f"invalid {label}")
    return result


def _signed_fraction(value: Any, label: str) -> Fraction:
    try:
        return Fraction(str(value))
    except (ValueError, ZeroDivisionError) as exc:
        raise ValidationError(f"invalid {label}") from exc


def _round_fraction(value: Fraction) -> int:
    if value < 0:
        raise ValidationError("negative source duration")
    return (value.numerator * 2 + value.denominator) // (2 * value.denominator)


def _round_signed_fraction(value: Fraction) -> int:
    return _round_fraction(value) if value >= 0 else -_round_fraction(-value)


def probe_composition_source(source_path: Path, ffprobe: Path) -> dict[str, Any]:
    command = [
        str(ffprobe),
        "-v",
        "error",
        "-show_entries",
        (
            "format=start_time,duration:"
            "stream=index,codec_type,time_base,start_pts,start_time,duration_ts,"
            "duration,width,height,avg_frame_rate,r_frame_rate,sample_rate,channels"
        ),
        "-of",
        "json",
        str(source_path),
    ]
    result = subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        raise ValidationError("ffprobe could not read the composition source")
    try:
        metadata = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValidationError("ffprobe returned invalid source metadata") from exc
    streams = metadata.get("streams")
    if not isinstance(streams, list):
        raise ValidationError("source stream metadata is missing")
    video = next(
        (stream for stream in streams if stream.get("codec_type") == "video"), None
    )
    audio = next(
        (stream for stream in streams if stream.get("codec_type") == "audio"), None
    )
    if not isinstance(video, Mapping) or not isinstance(audio, Mapping):
        raise ValidationError("composition source requires video and audio")
    format_value = metadata.get("format")
    if not isinstance(format_value, Mapping):
        format_value = {}

    video_time_base = _fraction(video.get("time_base"), "video time base")
    try:
        video_start_pts = int(video.get("start_pts"))
    except (TypeError, ValueError):
        video_start_time = _signed_fraction(
            video.get("start_time", 0), "video start time"
        )
        video_start_pts = _round_signed_fraction(video_start_time / video_time_base)
    try:
        video_duration_ts = int(video.get("duration_ts"))
    except (TypeError, ValueError):
        raw_duration = video.get("duration", format_value.get("duration"))
        duration = _fraction(raw_duration, "video duration")
        video_duration_ts = _round_fraction(duration / video_time_base)
    if video_duration_ts < 1:
        raise ValidationError("video duration is empty")

    try:
        sample_rate = int(audio.get("sample_rate"))
    except (TypeError, ValueError) as exc:
        raise ValidationError("invalid source audio sample rate") from exc
    if sample_rate < 1:
        raise ValidationError("invalid source audio sample rate")
    audio_time_base = _fraction(audio.get("time_base"), "audio time base")
    try:
        audio_start_pts = int(audio.get("start_pts"))
    except (TypeError, ValueError):
        audio_start_time = _signed_fraction(
            audio.get("start_time", 0), "audio start time"
        )
        audio_start_pts = _round_signed_fraction(audio_start_time / audio_time_base)
    try:
        audio_duration_ts = int(audio.get("duration_ts"))
        audio_duration = Fraction(audio_duration_ts) * audio_time_base
    except (TypeError, ValueError):
        raw_duration = audio.get("duration", format_value.get("duration"))
        audio_duration = _fraction(raw_duration, "audio duration")
    audio_duration_samples = _round_fraction(audio_duration * sample_rate)
    if audio_duration_samples < 1:
        raise ValidationError("audio duration is empty")

    try:
        width = int(video.get("width"))
        height = int(video.get("height"))
        channels = int(audio.get("channels"))
        video_index = int(video.get("index"))
        audio_index = int(audio.get("index"))
    except (TypeError, ValueError) as exc:
        raise ValidationError("invalid source stream metadata") from exc
    if width < 2 or height < 2 or channels < 1:
        raise ValidationError("invalid source stream dimensions")
    average_rate = str(video.get("avg_frame_rate", "0/0"))
    real_rate = str(video.get("r_frame_rate", "0/0"))
    raw_format_start = format_value.get("start_time")
    if raw_format_start is None:
        format_start = min(
            Fraction(video_start_pts) * video_time_base,
            Fraction(audio_start_pts) * audio_time_base,
        )
    else:
        format_start = _signed_fraction(raw_format_start, "format start time")
    return {
        "format": {
            "start_time_num": format_start.numerator,
            "start_time_den": format_start.denominator,
        },
        "video": {
            "stream_index": video_index,
            "time_base_num": video_time_base.numerator,
            "time_base_den": video_time_base.denominator,
            "start_pts": video_start_pts,
            "duration_ts": video_duration_ts,
            "width": width,
            "height": height,
            "avg_frame_rate": average_rate,
            "real_frame_rate": real_rate,
            "variable_frame_rate": average_rate != real_rate,
        },
        "audio": {
            "stream_index": audio_index,
            "time_base_num": audio_time_base.numerator,
            "time_base_den": audio_time_base.denominator,
            "start_pts": audio_start_pts,
            "sample_rate": sample_rate,
            "channels": channels,
            "duration_samples": audio_duration_samples,
        },
    }


def create_composition_project(
    projects_root: Path,
    project_id: str,
    *,
    source_path: Path,
    rights_confirmed: bool,
    authorization_note: str,
    config: Mapping[str, Any],
    ffmpeg: Path,
    ffprobe: Path,
    probe: Callable[[Path, Path], Mapping[str, Any]] = probe_composition_source,
) -> dict[str, Any]:
    if rights_confirmed is not True:
        raise ValidationError("rights confirmation is required")
    if not isinstance(authorization_note, str) or not authorization_note.strip():
        raise ValidationError("authorization note is required")
    source = source_path.expanduser().resolve()
    if not source.is_file() or _is_link(source):
        raise ValidationError("composition source must be a regular local file")
    ffmpeg = ffmpeg.expanduser().resolve()
    ffprobe = ffprobe.expanduser().resolve()
    if not ffmpeg.is_file() or not ffprobe.is_file():
        raise ValidationError("ffmpeg and ffprobe must exist")
    try:
        pinned_config = json.loads(
            json.dumps(config, ensure_ascii=False, allow_nan=False)
        )
    except (TypeError, ValueError) as exc:
        raise ValidationError("composition config must be JSON serializable") from exc
    if not isinstance(pinned_config, dict):
        raise ValidationError("composition config must be an object")
    canvas = pinned_config.get("canvas")
    audio = pinned_config.get("audio")
    render = pinned_config.get("render")
    subtitle = pinned_config.get("subtitle")
    if not all(isinstance(value, dict) for value in (canvas, audio, render, subtitle)):
        raise ValidationError("composition config is incomplete")
    if (
        canvas.get("width") != 1080
        or canvas.get("height") != 1920
        or canvas.get("fps") != 30
    ):
        raise ValidationError("C0 composition output must be 1080x1920 at 30 fps")
    audio["sample_rate"] = 48000

    analysis = dict(probe(source, ffprobe))
    project_dir = composition_project_dir(
        projects_root, project_id, create_root=True
    )
    if project_dir.exists():
        raise ConflictError(f"composition project already exists: {project_id}")
    stat = source.stat()
    project = {
        "schema_version": COMPOSITION_PROJECT_SCHEMA_VERSION,
        "version": COMPOSITION_PROJECT_VERSION,
        "project_id": project_id,
        "created_at": _now(),
        "source": {
            "source_id": "source-001",
            "path": str(source),
            "name": source.name,
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "sha256": sha256_file(source),
            "analysis": analysis,
        },
        "rights": {
            "confirmed": True,
            "authorization_note": authorization_note.strip(),
        },
        "config": pinned_config,
        "config_hash": content_hash(pinned_config),
        "tools": {"ffmpeg": str(ffmpeg), "ffprobe": str(ffprobe)},
    }
    root = project_dir.parent
    temporary = root / f".{project_id}.tmp-{uuid.uuid4().hex}"
    temporary.mkdir()
    published = False
    try:
        _write_json_file(temporary / "project.json", project)
        _write_json_file(
            temporary / "project-identity.json",
            {
                "schema_version": 1,
                "project_id": project_id,
                "project_hash": content_hash(project),
            },
        )
        os.replace(temporary, project_dir)
        published = True
        return load_composition_project(project_dir)
    finally:
        if not published and temporary.exists():
            shutil.rmtree(temporary)


def load_composition_project(project_dir: Path) -> dict[str, Any]:
    validate_safe_id(project_dir.name, "composition project id")
    path = confined_composition_path(project_dir, "project.json")
    identity_path = confined_composition_path(project_dir, "project-identity.json")
    if not path.is_file() or not identity_path.is_file():
        raise NotFoundError("composition project metadata is missing")
    value = read_json(path)
    if not isinstance(value, Mapping):
        raise ValidationError("composition project metadata must be an object")
    project = dict(value)
    identity = read_json(identity_path)
    if (
        not isinstance(identity, Mapping)
        or identity.get("schema_version") != 1
        or identity.get("project_id") != project_dir.name
        or identity.get("project_hash") != content_hash(project)
    ):
        raise ValidationError("composition project identity hash mismatch")
    if (
        project.get("schema_version") != COMPOSITION_PROJECT_SCHEMA_VERSION
        or project.get("version") != COMPOSITION_PROJECT_VERSION
        or project.get("project_id") != project_dir.name
    ):
        raise ValidationError("invalid composition project metadata")
    config = project.get("config")
    if not isinstance(config, Mapping) or project.get("config_hash") != content_hash(config):
        raise ValidationError("composition config hash mismatch")
    source = project.get("source")
    if not isinstance(source, Mapping) or source.get("source_id") != "source-001":
        raise ValidationError("composition source metadata is invalid")
    source_hash = source.get("sha256")
    if not isinstance(source_hash, str) or len(source_hash) != 64:
        raise ValidationError("composition source hash is invalid")
    rights = project.get("rights")
    if not isinstance(rights, Mapping) or rights.get("confirmed") is not True:
        raise ValidationError("composition rights record is invalid")
    tools = project.get("tools")
    if not isinstance(tools, Mapping):
        raise ValidationError("composition tool metadata is missing")
    return project


def safe_composition_project_dir(projects_root: Path, project_id: str) -> Path:
    project_dir = composition_project_dir(projects_root, project_id)
    if not project_dir.is_dir():
        raise NotFoundError(f"composition project not found: {project_id}")
    load_composition_project(project_dir)
    return project_dir


def verified_composition_source(project_dir: Path) -> Path:
    project = load_composition_project(project_dir)
    source = project["source"]
    path = Path(source["path"]).expanduser().resolve()
    if not path.is_file() or _is_link(path):
        raise ConflictError("composition source is missing or linked")
    stat = path.stat()
    if stat.st_size != source["size"] or stat.st_mtime_ns != source["mtime_ns"]:
        raise ConflictError("composition source file identity changed")
    if sha256_file(path) != source["sha256"]:
        raise ConflictError("composition source hash changed")
    return path


def _edit_revision_name(revision: int) -> str:
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise ValidationError("edit revision must be a positive integer")
    return f"{revision:06d}"


def _edits_root(project_dir: Path) -> Path:
    return confined_composition_path(project_dir, "edits")


def _edit_revision_dir(project_dir: Path, revision: int) -> Path:
    return confined_composition_path(
        project_dir, "edits", "revisions", _edit_revision_name(revision)
    )


def list_edit_revisions(project_dir: Path) -> list[int]:
    load_composition_project(project_dir)
    root = confined_composition_path(project_dir, "edits", "revisions")
    if not root.is_dir():
        return []
    revisions: list[int] = []
    for entry in root.iterdir():
        if not entry.is_dir() or not entry.name.isdigit() or len(entry.name) != 6:
            continue
        if (entry / "edit.json").is_file() and (entry / "compiled-timeline.json").is_file():
            revisions.append(int(entry.name))
    return sorted(revisions)


def _validate_edit_document(
    document: Mapping[str, Any], *, project: Mapping[str, Any], revision: int
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(document, Mapping):
        raise ValidationError("edit revision must be an object")
    if set(document) != {
        "schema_version",
        "project_id",
        "revision",
        "base_revision",
        "origin",
        "created_at",
        "plan",
        "plan_hash",
        "compiled_timeline_hash",
    }:
        raise ValidationError("edit revision has invalid fields")
    if (
        document.get("schema_version") != EDIT_REVISION_SCHEMA_VERSION
        or document.get("project_id") != project.get("project_id")
        or document.get("revision") != revision
    ):
        raise ValidationError("edit revision identity mismatch")
    base = document.get("base_revision")
    if revision == 1:
        if base is not None:
            raise ValidationError("first edit revision must not have a base")
    elif not isinstance(base, int) or isinstance(base, bool) or not 1 <= base < revision:
        raise ValidationError("invalid base edit revision")
    if document.get("origin") not in {"manual", "ai-accepted"}:
        raise ValidationError("invalid edit revision origin")
    plan = validate_edit_plan(document.get("plan"), project=project)
    compiled = compile_edit_plan(plan, project=project)
    if document.get("plan_hash") != content_hash(plan):
        raise ValidationError("edit plan hash mismatch")
    if document.get("compiled_timeline_hash") != content_hash(compiled):
        raise ValidationError("compiled timeline hash mismatch")
    return dict(document), compiled


def load_edit_revision(project_dir: Path, revision: int) -> dict[str, Any]:
    project = load_composition_project(project_dir)
    revision_dir = _edit_revision_dir(project_dir, revision)
    edit_path = revision_dir / "edit.json"
    compiled_path = revision_dir / "compiled-timeline.json"
    if not edit_path.is_file() or not compiled_path.is_file():
        raise NotFoundError(f"edit revision not found: {revision}")
    document, expected_compiled = _validate_edit_document(
        read_json(edit_path), project=project, revision=revision
    )
    stored_compiled = assert_compiled_timeline(read_json(compiled_path))
    if stored_compiled != expected_compiled:
        raise ValidationError("stored compiled timeline does not match edit plan")
    return document


def load_compiled_timeline(project_dir: Path, revision: int) -> dict[str, Any]:
    load_edit_revision(project_dir, revision)
    return assert_compiled_timeline(
        read_json(_edit_revision_dir(project_dir, revision) / "compiled-timeline.json")
    )


def _current_edit_pointer(project_dir: Path) -> dict[str, Any]:
    path = confined_composition_path(project_dir, "edits", "current.json")
    if not path.is_file():
        raise NotFoundError("current edit revision is not initialized")
    pointer = read_json(path)
    if not isinstance(pointer, Mapping):
        raise ValidationError("current edit pointer must be an object")
    revision = pointer.get("revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise ValidationError("invalid current edit pointer")
    document = load_edit_revision(project_dir, revision)
    if pointer.get("edit_hash") != content_hash(document):
        raise ValidationError("current edit pointer hash mismatch")
    return dict(pointer)


def load_current_edit(project_dir: Path) -> dict[str, Any]:
    pointer = _current_edit_pointer(project_dir)
    return load_edit_revision(project_dir, int(pointer["revision"]))


def publish_edit_revision(
    project_dir: Path,
    plan: Mapping[str, Any],
    *,
    base_revision: int | None,
    origin: str = "manual",
    failpoint: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    project = load_composition_project(project_dir)
    normalized = validate_edit_plan(plan, project=project)
    compiled = compile_edit_plan(normalized, project=project)
    revisions = list_edit_revisions(project_dir)
    current: dict[str, Any] | None
    try:
        current = load_current_edit(project_dir)
    except NotFoundError:
        current = None
    if current is None:
        if base_revision is not None:
            raise ConflictError("first edit revision must not specify a base")
    else:
        if base_revision != current["revision"]:
            raise ConflictError("base edit revision is stale")
        if current["plan_hash"] == content_hash(normalized):
            raise ValidationError("edit plan does not change the current revision")
    next_revision = (revisions[-1] if revisions else 0) + 1
    document = {
        "schema_version": EDIT_REVISION_SCHEMA_VERSION,
        "project_id": project["project_id"],
        "revision": next_revision,
        "base_revision": base_revision,
        "origin": origin,
        "created_at": _now(),
        "plan": normalized,
        "plan_hash": content_hash(normalized),
        "compiled_timeline_hash": content_hash(compiled),
    }
    _validate_edit_document(document, project=project, revision=next_revision)
    revisions_dir = confined_composition_path(project_dir, "edits", "revisions")
    revisions_dir.mkdir(parents=True, exist_ok=True)
    final_dir = _edit_revision_dir(project_dir, next_revision)
    if final_dir.exists():
        raise ConflictError(f"edit revision already exists: {next_revision}")
    temporary = revisions_dir / f".{final_dir.name}.tmp-{uuid.uuid4().hex}"
    temporary.mkdir()
    published = False
    try:
        _write_json_file(temporary / "edit.json", document)
        _write_json_file(temporary / "compiled-timeline.json", compiled)
        os.replace(temporary, final_dir)
        published = True
        pointer = {
            "schema_version": 1,
            "project_id": project["project_id"],
            "revision": next_revision,
            "edit_hash": content_hash(document),
            "updated_at": _now(),
        }
        edits_root = _edits_root(project_dir)
        atomic_write_json(
            edits_root / "recovery.json",
            {
                "schema_version": 1,
                "project_id": project["project_id"],
                "latest_published_revision": next_revision,
                "edit_hash": pointer["edit_hash"],
                "updated_at": pointer["updated_at"],
            },
        )
        if failpoint:
            failpoint("edit_after_revision_publish")
        atomic_write_json(edits_root / "current.json", pointer)
        return document
    finally:
        if not published and temporary.exists():
            shutil.rmtree(temporary)


def _validated_composition_qc(path: Path) -> dict[str, Any]:
    qc = read_json(path)
    if not isinstance(qc, Mapping):
        raise ValidationError("composition render QC must be an object")
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
        raise ValidationError("composition render QC is internally inconsistent")
    return dict(qc)


def _composition_renders_dir(project_dir: Path) -> Path:
    return confined_composition_path(project_dir, "renders")


def publish_composition_render(
    project_dir: Path,
    *,
    edit_revision: int,
    render_profile: str = "final",
    renderer: Callable[
        [Path, Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], Path],
        Mapping[str, Any],
    ],
    failpoint: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    if render_profile not in {"proxy", "final"}:
        raise ValidationError("composition render profile must be proxy or final")
    project = load_composition_project(project_dir)
    source_path = verified_composition_source(project_dir)
    edit = load_edit_revision(project_dir, edit_revision)
    compiled = load_compiled_timeline(project_dir, edit_revision)
    render_input = {
        "schema_version": RENDER_INPUT_SCHEMA_VERSION,
        "project_id": project["project_id"],
        "edit_revision": edit_revision,
        "edit_plan_hash": edit["plan_hash"],
        "compiled_timeline_hash": edit["compiled_timeline_hash"],
        "source_sha256": project["source"]["sha256"],
        "source_path": str(source_path),
        "style_preset": project["config"],
        "style_preset_hash": project["config_hash"],
        "compiler_version": COMPILER_VERSION,
        "render_profile_version": RENDER_PROFILE_VERSION,
        "render_profile": render_profile,
    }
    render_input_hash = content_hash(render_input)
    render_id = (
        "composition-"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        + "-"
        + uuid.uuid4().hex[:10]
    )
    renders_dir = _composition_renders_dir(project_dir)
    renders_dir.mkdir(parents=True, exist_ok=True)
    final_dir = renders_dir / render_id
    temporary = renders_dir / f".{render_id}.tmp"
    temporary.mkdir()
    published = False
    try:
        _write_json_file(temporary / "render-input.json", render_input)
        _write_json_file(temporary / "compiled-timeline.json", compiled)
        renderer_result = dict(
            renderer(project_dir, project, edit, compiled, temporary)
        )
        video_path = temporary / "short.mp4"
        qc_path = temporary / "qc.json"
        if not video_path.is_file() or video_path.stat().st_size == 0:
            raise ValidationError("composition renderer did not produce short.mp4")
        if not qc_path.is_file():
            raise ValidationError("composition renderer did not produce qc.json")
        _validated_composition_qc(qc_path)
        metadata = {
            "schema_version": COMPOSITION_RENDER_SCHEMA_VERSION,
            "render_id": render_id,
            "project_id": project["project_id"],
            "edit_revision": edit_revision,
            "edit_plan_hash": edit["plan_hash"],
            "compiled_timeline_hash": edit["compiled_timeline_hash"],
            "render_input_hash": render_input_hash,
            "source_sha256": project["source"]["sha256"],
            "style_preset_hash": project["config_hash"],
            "compiler_version": COMPILER_VERSION,
            "render_profile_version": RENDER_PROFILE_VERSION,
            "render_profile": render_profile,
            "output_hash": sha256_file(video_path),
            "technical_checks_passed": True,
            "content_review": "pending",
            "created_at": _now(),
            "renderer": renderer_result,
        }
        _write_json_file(temporary / "render.json", metadata)
        if failpoint:
            failpoint("composition_render_after_qc_before_publish")
        os.replace(temporary, final_dir)
        published = True
        return metadata
    finally:
        if not published and temporary.exists():
            shutil.rmtree(temporary)


def load_composition_render(project_dir: Path, render_id: str) -> dict[str, Any]:
    project = load_composition_project(project_dir)
    validate_safe_id(render_id, "composition render id")
    render_dir = confined_composition_path(project_dir, "renders", render_id)
    metadata_path = render_dir / "render.json"
    video_path = render_dir / "short.mp4"
    qc_path = render_dir / "qc.json"
    render_input_path = render_dir / "render-input.json"
    compiled_path = render_dir / "compiled-timeline.json"
    if not all(
        path.is_file()
        for path in (metadata_path, video_path, qc_path, render_input_path, compiled_path)
    ):
        raise NotFoundError(f"composition render not found: {render_id}")
    metadata = read_json(metadata_path)
    if not isinstance(metadata, Mapping):
        raise ValidationError("composition render metadata must be an object")
    if (
        metadata.get("schema_version") != COMPOSITION_RENDER_SCHEMA_VERSION
        or metadata.get("render_id") != render_id
        or metadata.get("project_id") != project["project_id"]
    ):
        raise ValidationError("composition render identity mismatch")
    revision = metadata.get("edit_revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise ValidationError("composition render edit revision is invalid")
    edit = load_edit_revision(project_dir, revision)
    compiled = load_compiled_timeline(project_dir, revision)
    if (
        metadata.get("edit_plan_hash") != edit["plan_hash"]
        or metadata.get("compiled_timeline_hash") != content_hash(compiled)
    ):
        raise ValidationError("composition render edit identity mismatch")
    render_input = read_json(render_input_path)
    if metadata.get("render_input_hash") != content_hash(render_input):
        raise ValidationError("composition render input hash mismatch")
    if metadata.get("render_profile") != render_input.get("render_profile"):
        raise ValidationError("composition render profile mismatch")
    if read_json(compiled_path) != compiled:
        raise ValidationError("composition render timeline snapshot mismatch")
    if metadata.get("output_hash") != sha256_file(video_path):
        raise ConflictError("composition render output hash mismatch")
    _validated_composition_qc(qc_path)
    current_revision = int(_current_edit_pointer(project_dir)["revision"])
    result = dict(metadata)
    result["is_current_edit"] = revision == current_revision
    return result


def list_composition_renders(project_dir: Path) -> list[dict[str, Any]]:
    load_composition_project(project_dir)
    root = _composition_renders_dir(project_dir)
    if not root.is_dir():
        return []
    values: list[dict[str, Any]] = []
    for entry in root.iterdir():
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        try:
            values.append(load_composition_render(project_dir, entry.name))
        except (ConflictError, NotFoundError, ValidationError, OSError, ValueError):
            continue
    return sorted(values, key=lambda item: str(item.get("created_at", "")))


def composition_source_for_review(project_dir: Path) -> tuple[dict[str, Any], Path]:
    """Return the pinned local source for localhost review without a full re-hash."""
    project = load_composition_project(project_dir)
    source = project["source"]
    path = Path(source["path"]).expanduser().resolve()
    if not path.is_file() or _is_link(path):
        raise ConflictError("composition source is missing or linked")
    stat = path.stat()
    if stat.st_size != source["size"] or stat.st_mtime_ns != source["mtime_ns"]:
        raise ConflictError("composition source file identity changed")
    return dict(source), path


def list_composition_projects(projects_root: Path) -> list[dict[str, Any]]:
    raw_root = projects_root.expanduser()
    if not raw_root.is_dir() or _is_link(raw_root):
        return []
    root = raw_root.resolve()
    values: list[dict[str, Any]] = []
    for entry in root.iterdir():
        if not entry.is_dir() or entry.name.startswith(".") or _is_link(entry):
            continue
        try:
            project_dir = safe_composition_project_dir(root, entry.name)
            project = load_composition_project(project_dir)
            try:
                current = load_current_edit(project_dir)
                revision = int(current["revision"])
            except NotFoundError:
                revision = None
            analysis = project["source"]["analysis"]["video"]
            duration = Fraction(int(analysis["duration_ts"])) * Fraction(
                int(analysis["time_base_num"]), int(analysis["time_base_den"])
            )
            renders_root = confined_composition_path(project_dir, "renders")
            render_count = (
                sum(
                    1
                    for child in renders_root.iterdir()
                    if child.is_dir() and not child.name.startswith(".")
                )
                if renders_root.is_dir()
                else 0
            )
            values.append(
                {
                    "project_id": project["project_id"],
                    "source_name": project["source"]["name"],
                    "duration_seconds": float(duration),
                    "current_revision": revision,
                    "render_count": render_count,
                }
            )
        except (ConflictError, NotFoundError, ValidationError, OSError, ValueError):
            continue
    return sorted(values, key=lambda item: str(item["project_id"]))


def project_composition_for_review(project_dir: Path) -> dict[str, Any]:
    project = load_composition_project(project_dir)
    current = load_current_edit(project_dir)
    compiled = load_compiled_timeline(project_dir, int(current["revision"]))
    source = project["source"]
    video = source["analysis"]["video"]
    audio = source["analysis"]["audio"]
    format_analysis = source["analysis"].get("format", {})
    format_start_num = int(format_analysis.get("start_time_num", 0))
    format_start_den = int(format_analysis.get("start_time_den", 1))
    duration = Fraction(int(video["duration_ts"])) * Fraction(
        int(video["time_base_num"]), int(video["time_base_den"])
    )
    return {
        "project_id": project["project_id"],
        "source": {
            "name": source["name"],
            "sha256": source["sha256"],
            "duration_seconds": float(duration),
            "width": int(video["width"]),
            "height": int(video["height"]),
            "video_time_base_num": int(video["time_base_num"]),
            "video_time_base_den": int(video["time_base_den"]),
            "video_start_pts": int(video["start_pts"]),
            "video_duration_ts": int(video["duration_ts"]),
            "format_start_time_num": format_start_num,
            "format_start_time_den": format_start_den,
            "audio_sample_rate": int(audio["sample_rate"]),
            "audio_duration_samples": int(audio["duration_samples"]),
        },
        "edit": current,
        "compiled": compiled,
        "renders": list_composition_renders(project_dir),
    }
