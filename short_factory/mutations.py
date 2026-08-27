from __future__ import annotations

import errno
import hashlib
import json
import math
import os
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any, BinaryIO, Mapping

from .artifacts import (
    ConflictError,
    NotFoundError,
    ValidationError,
    WorkflowError,
    ensure_workflow_job,
    safe_job_dir,
    save_caption_revision,
    sha256_file,
    list_renders,
    load_current_caption,
)
from .candidate_artifacts import candidate_preview, candidate_source
from .pipeline import Pipeline, RunOptions
from .rendering import render_caption_revision


BUSY_EXIT_CODE = 75


class LockBusyError(RuntimeError):
    pass


class GlobalMutationLock:
    """One non-blocking OS lock shared by every mutating command."""

    def __init__(self, jobs_root: Path):
        self.jobs_root = jobs_root.expanduser().resolve()
        self._file: BinaryIO | None = None

    @property
    def path(self) -> Path:
        raw = self.jobs_root / ".client-short-factory.lock"
        is_junction = getattr(os.path, "isjunction", None)
        if raw.is_symlink() or (callable(is_junction) and is_junction(raw)):
            raise OSError(errno.ELOOP, "mutation lock path must not be a link")
        resolved = raw.resolve()
        try:
            resolved.relative_to(self.jobs_root)
        except ValueError as exc:
            raise OSError(errno.EPERM, "mutation lock escapes jobs root") from exc
        if raw.exists() and raw.stat().st_nlink != 1:
            raise OSError(errno.EPERM, "mutation lock must not be hard-linked")
        return resolved

    def __enter__(self) -> "GlobalMutationLock":
        self.jobs_root.mkdir(parents=True, exist_ok=True)
        lock_file = self.path.open("a+b")
        lock_file.seek(0, os.SEEK_END)
        if lock_file.tell() == 0:
            lock_file.write(b"\0")
            lock_file.flush()
            os.fsync(lock_file.fileno())
        lock_file.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            lock_file.close()
            if exc.errno in {errno.EACCES, errno.EAGAIN} or getattr(
                exc, "winerror", None
            ) in {33, 36}:
                raise LockBusyError("another mutation is already running") from exc
            raise
        self._file = lock_file
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self._file is None:
            return
        try:
            self._file.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
        finally:
            self._file.close()
            self._file = None


def _read_payload(*, stdin_json: bool, captions_file: Path | None) -> dict[str, Any]:
    if stdin_json == (captions_file is not None):
        raise ValueError("choose exactly one of --stdin-json or --captions-file")
    if stdin_json:
        raw = sys.stdin.buffer.read().decode("utf-8")
    else:
        assert captions_file is not None
        raw = captions_file.expanduser().read_text(encoding="utf-8")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("caption payload must be a JSON object")
    return value


def save_captions(
    *,
    jobs_root: Path,
    job_id: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    if set(payload) != {"base_revision", "cues"}:
        raise ValidationError("caption payload must contain only base_revision and cues")
    job_dir = safe_job_dir(jobs_root, job_id)
    return save_caption_revision(
        job_dir,
        base_revision=payload["base_revision"],
        cues=payload["cues"],
    )


def render_job(
    *,
    jobs_root: Path,
    job_id: str,
    caption_revision: int,
) -> dict[str, Any]:
    job_dir = safe_job_dir(jobs_root, job_id)
    return render_caption_revision(job_dir, caption_revision)


def _candidate_job_id(
    run_id: str, candidate_id: str, start: float, end: float
) -> str:
    identity = f"{run_id}\0{candidate_id}\0{start:.3f}\0{end:.3f}"
    suffix = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:14]
    rank = candidate_id.rsplit("-", 1)[-1]
    return f"clip-{rank}-{suffix}"


def adopt_candidate_range(
    *,
    jobs_root: Path,
    candidate_root: Path,
    run_id: str,
    candidate_id: str,
    start: float,
    end: float,
) -> dict[str, Any]:
    if (
        isinstance(start, bool)
        or isinstance(end, bool)
        or not isinstance(start, (int, float))
        or not isinstance(end, (int, float))
        or not math.isfinite(float(start))
        or not math.isfinite(float(end))
    ):
        raise ValidationError("candidate range must use finite seconds")
    normalized_start = round(float(start), 3)
    normalized_end = round(float(end), 3)
    source, source_file = candidate_source(candidate_root, run_id)
    candidate_preview(candidate_root, run_id, candidate_id)
    duration = float(source["duration_seconds"])
    if (
        normalized_start < 0
        or normalized_end <= normalized_start
        or normalized_end > duration
        or normalized_end - normalized_start < 15
        or normalized_end - normalized_start > 60
    ):
        raise ValidationError("candidate range is outside the supported source window")
    if sha256_file(source_file) != source["sha256"]:
        raise ConflictError("candidate source hash changed")

    job_id = _candidate_job_id(
        run_id, candidate_id, normalized_start, normalized_end
    )
    pipeline = Pipeline(
        RunOptions(
            source=str(source_file),
            start=f"{normalized_start:.3f}",
            end=f"{normalized_end:.3f}",
            job_id=job_id,
            jobs_root=jobs_root,
            template="default",
            dictionary="default",
            rights_confirmed=True,
            authorization_note=(
                f"Authorized local candidate run {run_id}; range selected in "
                "localhost UI; no upload or delivery authorized."
            ),
        )
    )
    caption = pipeline.run_until_subtitles()
    revision = int(caption["revision"])
    existing = [
        render
        for render in list_renders(pipeline.job_dir)
        if render.get("caption_revision") == revision
    ]
    render = existing[-1] if existing else render_job(
        jobs_root=jobs_root,
        job_id=job_id,
        caption_revision=revision,
    )
    current = load_current_caption(pipeline.job_dir)
    return {
        "job_id": job_id,
        "caption_revision": int(current["revision"]),
        "render_id": render["render_id"],
        "candidate_run_id": run_id,
        "candidate_id": candidate_id,
        "start_seconds": normalized_start,
        "end_seconds": normalized_end,
    }


def _round_fraction(value: Fraction) -> int:
    if value < 0:
        return -_round_fraction(-value)
    return (value.numerator * 2 + value.denominator) // (2 * value.denominator)


def _candidate_composition_plan(
    project: Mapping[str, Any],
    caption: Mapping[str, Any],
    *,
    start: float,
    end: float,
) -> dict[str, Any]:
    analysis = project["source"]["analysis"]
    video = analysis["video"]
    audio = analysis["audio"]
    format_value = analysis.get("format", {})
    video_time_base = Fraction(
        int(video["time_base_num"]), int(video["time_base_den"])
    )
    audio_time_base = Fraction(
        int(audio.get("time_base_num", 1)),
        int(audio.get("time_base_den", audio["sample_rate"])),
    )
    format_start = Fraction(
        int(format_value.get("start_time_num", 0)),
        int(format_value.get("start_time_den", 1)),
    )
    video_start = int(video["start_pts"])
    video_end = video_start + int(video["duration_ts"])
    timeline_start = format_start + Fraction(str(start))
    timeline_end = format_start + Fraction(str(end))
    clip_in = max(video_start, _round_fraction(timeline_start / video_time_base))
    clip_out = min(video_end, _round_fraction(timeline_end / video_time_base))
    if clip_out <= clip_in:
        raise ValidationError("candidate range does not contain video frames")

    sample_rate = int(audio["sample_rate"])
    audio_stream_start = Fraction(int(audio.get("start_pts", 0))) * audio_time_base
    audio_in = _round_fraction((timeline_start - audio_stream_start) * sample_rate)
    clip_duration = Fraction(clip_out - clip_in) * video_time_base
    audio_out = audio_in + _round_fraction(clip_duration * sample_rate)
    if audio_in < 0 or audio_out > int(audio["duration_samples"]):
        raise ValidationError("candidate range is outside the source audio")

    speech_captions = []
    for index, cue in enumerate(caption.get("cues", []), start=1):
        cue_in = clip_in + _round_fraction(Fraction(str(cue["start"])) / video_time_base)
        cue_out = clip_in + _round_fraction(Fraction(str(cue["end"])) / video_time_base)
        cue_in = max(clip_in, cue_in)
        cue_out = min(clip_out, cue_out)
        if cue_out <= cue_in:
            continue
        speech_captions.append(
            {
                "id": f"caption-{index:03d}",
                "timeline_item_id": "clip-main",
                "source_in_pts": cue_in,
                "source_out_pts": cue_out,
                "text": str(cue["text"]),
                "role": "normal",
                "token_ids": [],
            }
        )

    return {
        "schema_version": 1,
        "project_id": project["project_id"],
        "source_id": project["source"]["source_id"],
        "story_beats": [
            {
                "id": "beat-main",
                "role": "hook",
                "source_order_lock": False,
                "timeline_item_ids": ["clip-main"],
            }
        ],
        "timeline_items": [
            {
                "id": "clip-main",
                "type": "source_clip",
                "story_beat_id": "beat-main",
                "video_in_pts": clip_in,
                "video_out_pts": clip_out,
                "audio_in_sample": audio_in,
                "audio_out_sample": audio_out,
            }
        ],
        "presentation_events": [
            {
                "id": "layout-main",
                "timeline_item_id": "clip-main",
                "source_in_pts": clip_in,
                "source_out_pts": clip_out,
                "layout": "standard",
            }
        ],
        "speech_captions": speech_captions,
        "editorial_overlays": [],
        "join_edges": [],
        "source_regions": {
            "person": [0, 0, 1000000, 1000000],
            "content": [0, 0, 1000000, 1000000],
            "comment": [0, 0, 1000000, 1000000],
        },
    }


def ensure_candidate_composition(
    *,
    jobs_root: Path,
    candidate_root: Path,
    composition_projects_root: Path,
    adoption: Mapping[str, Any],
) -> dict[str, Any]:
    from .composition_artifacts import (
        composition_project_dir,
        create_composition_project,
        load_composition_project,
        load_current_edit,
        publish_edit_revision,
    )

    project_id = str(adoption["job_id"])
    job_dir = safe_job_dir(jobs_root, project_id)
    job = ensure_workflow_job(job_dir)
    caption = load_current_caption(job_dir)
    source, source_file = candidate_source(candidate_root, str(adoption["candidate_run_id"]))
    if sha256_file(source_file) != source["sha256"]:
        raise ConflictError("candidate source hash changed")

    project_dir = composition_project_dir(
        composition_projects_root, project_id, create_root=True
    )
    try:
        project = load_composition_project(project_dir)
    except NotFoundError:
        tools = job.get("tools")
        config = job.get("config")
        if not isinstance(tools, Mapping) or not isinstance(config, Mapping):
            raise ValidationError("candidate job is missing composition settings")
        project = create_composition_project(
            composition_projects_root,
            project_id,
            source_path=source_file,
            rights_confirmed=True,
            authorization_note=(
                f"Authorized local candidate run {adoption['candidate_run_id']}; "
                "range selected in localhost UI; no upload or delivery authorized."
            ),
            config=config,
            ffmpeg=Path(str(tools["ffmpeg"])),
            ffprobe=Path(str(tools["ffprobe"])),
        )
    if project["source"]["sha256"] != source["sha256"]:
        raise ConflictError("composition project source does not match candidate source")
    try:
        edit = load_current_edit(project_dir)
    except NotFoundError:
        plan = _candidate_composition_plan(
            project,
            caption,
            start=float(adoption["start_seconds"]),
            end=float(adoption["end_seconds"]),
        )
        edit = publish_edit_revision(project_dir, plan, base_revision=None, origin="candidate")
    return {
        **dict(adoption),
        "project_id": project_id,
        "edit_revision": int(edit["revision"]),
    }


def run_save_worker(
    *,
    jobs_root: Path,
    job_id: str,
    stdin_json: bool,
    captions_file: Path | None,
) -> int:
    try:
        payload = _read_payload(stdin_json=stdin_json, captions_file=captions_file)
        safe_job_dir(jobs_root, job_id)
    except Exception as exc:
        print("ERROR " + json.dumps({"error": str(exc)}), flush=True)
        return 2
    try:
        with GlobalMutationLock(jobs_root):
            print("LOCK_ACQUIRED", flush=True)
            result = save_captions(
                jobs_root=jobs_root,
                job_id=job_id,
                payload=payload,
            )
    except LockBusyError:
        print("BUSY", flush=True)
        return BUSY_EXIT_CODE
    except Exception as exc:
        status = exc.status_code if isinstance(exc, WorkflowError) else 500
        print(
            json.dumps(
                {"ok": False, "status": status, "error": str(exc)},
                ensure_ascii=True,
            ),
            flush=True,
        )
        return 3 if isinstance(exc, ConflictError) else 1
    print(json.dumps({"ok": True, "result": result}), flush=True)
    return 0


def run_render_worker(
    *,
    jobs_root: Path,
    job_id: str,
    caption_revision: int,
) -> int:
    try:
        safe_job_dir(jobs_root, job_id)
        if caption_revision < 1:
            raise ValueError("caption revision must be positive")
    except Exception as exc:
        print("ERROR " + json.dumps({"error": str(exc)}), flush=True)
        return 2
    try:
        with GlobalMutationLock(jobs_root):
            print("LOCK_ACQUIRED", flush=True)
            result = render_job(
                jobs_root=jobs_root,
                job_id=job_id,
                caption_revision=caption_revision,
            )
    except LockBusyError:
        print("BUSY", flush=True)
        return BUSY_EXIT_CODE
    except Exception as exc:
        status = exc.status_code if isinstance(exc, WorkflowError) else 500
        print(
            json.dumps(
                {"ok": False, "status": status, "error": str(exc)},
                ensure_ascii=True,
            ),
            flush=True,
        )
        return 3 if isinstance(exc, ConflictError) else 1
    print(json.dumps({"ok": True, "result": result}), flush=True)
    return 0


def run_adopt_candidate_worker(
    *,
    jobs_root: Path,
    candidate_root: Path,
    composition_projects_root: Path,
    run_id: str,
    candidate_id: str,
    start: float,
    end: float,
) -> int:
    try:
        candidate_source(candidate_root, run_id)
        candidate_preview(candidate_root, run_id, candidate_id)
    except Exception as exc:
        print("ERROR " + json.dumps({"error": str(exc)}), flush=True)
        return 2
    try:
        with GlobalMutationLock(jobs_root):
            print("LOCK_ACQUIRED", flush=True)
            adoption = adopt_candidate_range(
                jobs_root=jobs_root,
                candidate_root=candidate_root,
                run_id=run_id,
                candidate_id=candidate_id,
                start=start,
                end=end,
            )
        with GlobalMutationLock(composition_projects_root):
            result = ensure_candidate_composition(
                jobs_root=jobs_root,
                candidate_root=candidate_root,
                composition_projects_root=composition_projects_root,
                adoption=adoption,
            )
    except LockBusyError:
        print("BUSY", flush=True)
        return BUSY_EXIT_CODE
    except Exception as exc:
        status = exc.status_code if isinstance(exc, WorkflowError) else 500
        print(
            json.dumps(
                {"ok": False, "status": status, "error": str(exc)},
                ensure_ascii=True,
            ),
            flush=True,
        )
        return 1
    print(json.dumps({"ok": True, "result": result}), flush=True)
    return 0


def _read_object_payload_from_stdin() -> dict[str, Any]:
    value = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("payload must be a JSON object")
    return value


def run_composition_save_worker(
    *,
    projects_root: Path,
    project_id: str,
) -> int:
    from .composition_artifacts import publish_edit_revision, safe_composition_project_dir

    try:
        payload = _read_object_payload_from_stdin()
        if set(payload) != {"base_revision", "plan"}:
            raise ValidationError("composition payload must contain base_revision and plan")
        base_revision = payload["base_revision"]
        if isinstance(base_revision, bool) or not isinstance(base_revision, int) or base_revision < 1:
            raise ValidationError("composition base revision must be positive")
        plan = payload["plan"]
        if not isinstance(plan, Mapping):
            raise ValidationError("composition plan must be an object")
        project_dir = safe_composition_project_dir(projects_root, project_id)
    except Exception as exc:
        print("ERROR " + json.dumps({"error": str(exc)}), flush=True)
        return 2
    try:
        with GlobalMutationLock(projects_root):
            print("LOCK_ACQUIRED", flush=True)
            result = publish_edit_revision(
                project_dir,
                plan,
                base_revision=base_revision,
                origin="manual",
            )
    except LockBusyError:
        print("BUSY", flush=True)
        return BUSY_EXIT_CODE
    except Exception as exc:
        status = exc.status_code if isinstance(exc, WorkflowError) else 500
        print(
            json.dumps(
                {"ok": False, "status": status, "error": str(exc)},
                ensure_ascii=True,
            ),
            flush=True,
        )
        return 3 if isinstance(exc, ConflictError) else 1
    print(
        json.dumps(
            {
                "ok": True,
                "result": {
                    "project_id": result["project_id"],
                    "revision": result["revision"],
                    "plan_hash": result["plan_hash"],
                    "compiled_timeline_hash": result["compiled_timeline_hash"],
                },
            }
        ),
        flush=True,
    )
    return 0


def run_composition_render_worker(
    *,
    projects_root: Path,
    project_id: str,
    edit_revision: int,
    render_profile: str,
) -> int:
    from .composition_artifacts import safe_composition_project_dir
    from .composition_rendering import render_composition_revision

    try:
        project_dir = safe_composition_project_dir(projects_root, project_id)
        if isinstance(edit_revision, bool) or edit_revision < 1:
            raise ValueError("edit revision must be positive")
        if render_profile not in {"proxy", "final"}:
            raise ValueError("render profile must be proxy or final")
    except Exception as exc:
        print("ERROR " + json.dumps({"error": str(exc)}), flush=True)
        return 2
    try:
        with GlobalMutationLock(projects_root):
            print("LOCK_ACQUIRED", flush=True)
            result = render_composition_revision(
                project_dir,
                edit_revision,
                render_profile=render_profile,
            )
    except LockBusyError:
        print("BUSY", flush=True)
        return BUSY_EXIT_CODE
    except Exception as exc:
        status = exc.status_code if isinstance(exc, WorkflowError) else 500
        print(
            json.dumps(
                {"ok": False, "status": status, "error": str(exc)},
                ensure_ascii=True,
            ),
            flush=True,
        )
        return 3 if isinstance(exc, ConflictError) else 1
    print(json.dumps({"ok": True, "result": result}), flush=True)
    return 0
