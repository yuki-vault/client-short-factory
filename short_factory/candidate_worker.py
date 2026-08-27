from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Mapping

from .candidate_selector import load_selector_config, select_candidates


WORKER_VERSION = 1


class CandidateWorkerError(RuntimeError):
    pass


class CandidateCancelled(CandidateWorkerError):
    pass


class CandidateNotQueued(CandidateWorkerError):
    pass


def run_candidate_worker(
    candidate_root: Path, run_id: str, config_path: Path
) -> dict[str, Any]:
    """Run one resumable, local-only candidate analysis."""

    from .candidate_artifacts import (
        cancel_requested,
        candidate_run_dir,
        candidate_run_lock,
        candidate_work_dir,
        load_external_ai_authorization,
        load_run,
        publish_candidate_set,
        update_status,
    )

    candidate_root = candidate_root.expanduser().resolve()
    config_path = config_path.expanduser().resolve()
    initial_run_dir = candidate_run_dir(candidate_root, run_id)
    with candidate_run_lock(initial_run_dir):
        run_dir = initial_run_dir
        try:
            run = load_run(candidate_root, run_id)
            run_dir = Path(run["run_dir"])
            if run_dir != initial_run_dir:
                raise CandidateWorkerError(
                    "candidate run path changed while acquiring lock"
                )
            source = Path(run["source_path"])
            status = run.get("status")
            if not isinstance(status, Mapping) or status.get("state") != "queued":
                raise CandidateNotQueued("candidate analysis is not queued")
        except CandidateNotQueued:
            raise
        except Exception as exc:
            update_status(
                run_dir,
                state="failed",
                stage="failed",
                progress=None,
                error={"code": type(exc).__name__, "message": str(exc)[:1000]},
            )
            raise
        try:
            config_document = _load_worker_config(config_path)
            selector_config = load_selector_config(config_path)
            authorization = load_external_ai_authorization(run_dir)
            update_status(
                run_dir,
                state="processing",
                stage="source_validation",
                progress={"completed": 0, "total": 1},
            )
            source_hash = _sha256(source)
            expected_hash = _manifest_value(
                run.get("manifest"), "source_sha256", "sha256"
            )
            if expected_hash and source_hash.lower() != str(expected_hash).lower():
                raise CandidateWorkerError("source hash does not match finalized intake")
            work_dir = candidate_work_dir(run_dir)
            work_dir.mkdir(parents=True, exist_ok=True)
            tools = _resolve_media_tools()
            duration = _probe_duration(tools["ffprobe"], source)
            expected_duration = _manifest_value(
                run.get("manifest"), "duration_seconds"
            )
            if expected_duration is not None and abs(duration - float(expected_duration)) > 1.0:
                raise CandidateWorkerError("source duration does not match finalized intake")
            fingerprint = _worker_fingerprint(
                source_hash, duration, config_document, config_path
            )
            _prepare_work_manifest(work_dir, fingerprint)
            _check_cancel(cancel_requested, run_dir)

            update_status(
                run_dir,
                state="processing",
                stage="audio",
                progress={"completed": 0, "total": 1},
            )
            audio = _ensure_audio(
                tools["ffmpeg"], tools["ffprobe"], source, work_dir, duration
            )
            transcript = _transcribe_resumable(
                audio,
                work_dir,
                duration,
                run_dir,
                config_document["transcription"],
                fingerprint["fingerprint_sha256"],
                cancel_requested,
                update_status,
            )
            _check_cancel(cancel_requested, run_dir)

            update_status(
                run_dir,
                state="processing",
                stage="selection",
                progress={"completed": 0, "total": 1},
            )
            if authorization is None:
                selected = select_candidates(transcript, selector_config)
            else:
                from .candidate_codex_selector import select_candidates_with_codex

                selected = select_candidates_with_codex(
                    transcript,
                    selector_config,
                    work_dir=work_dir,
                    authorization=authorization,
                )
            update_status(
                run_dir,
                state="processing",
                stage="preview",
                progress={"completed": 0, "total": len(selected["candidates"])},
            )
            previews: dict[str, Path] = {}
            for index, candidate in enumerate(selected["candidates"], 1):
                _check_cancel(cancel_requested, run_dir)
                preview = _render_preview(
                    tools["ffmpeg"],
                    tools["ffprobe"],
                    source,
                    work_dir,
                    candidate,
                    config_document["preview"],
                )
                previews[candidate["candidate_id"]] = preview
                update_status(
                    run_dir,
                    state="processing",
                    stage="preview",
                    progress={"completed": index, "total": len(selected["candidates"])},
                )
            _check_cancel(cancel_requested, run_dir)
            if _sha256(source) != source_hash:
                raise CandidateWorkerError("source changed during candidate analysis")
            document = {
                "schema_version": 1,
                "run_id": run_id,
                "source_sha256": source_hash,
                "assessment": selected["assessment"],
                "provider": selected["provider"],
                "model": selected["model"],
                "prompt_version": selected["prompt_version"],
                "candidates": selected["candidates"],
            }
            update_status(
                run_dir,
                state="processing",
                stage="publish",
                progress={"completed": 0, "total": 1},
            )
            published = publish_candidate_set(
                run_dir, document, preview_sources=previews
            )
            update_status(
                run_dir,
                state="complete",
                stage="complete",
                progress={"completed": 1, "total": 1},
                candidate_set_id=published.get("candidate_set_id"),
                candidate_count=len(published["candidates"]),
            )
            return published
        except CandidateCancelled:
            status = update_status(
                run_dir,
                state="cancelled",
                stage="cancelled",
                progress=None,
            )
            return {"cancelled": True, "status": status}
        except Exception as exc:
            update_status(
                run_dir,
                state="failed",
                stage="failed",
                progress=None,
                error={"code": type(exc).__name__, "message": str(exc)[:1000]},
            )
            raise


def _load_worker_config(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateWorkerError("cannot read candidate worker config") from exc
    if not isinstance(document, dict) or set(document) != {
        "schema_version",
        "transcription",
        "selection",
        "preview",
    }:
        raise CandidateWorkerError("candidate worker config has invalid top-level fields")
    if document["schema_version"] != 1:
        raise CandidateWorkerError("unsupported candidate worker config")
    transcription = _strict_mapping(
        document["transcription"],
        {
            "model",
            "device",
            "compute_type",
            "language",
            "beam_size",
            "vad_filter",
            "word_timestamps",
            "condition_on_previous_text",
            "chunk_seconds",
            "overlap_seconds",
        },
        "transcription",
    )
    if (
        transcription["model"] != "small"
        or transcription["device"] != "cpu"
        or transcription["compute_type"] != "int8"
        or transcription["beam_size"] != 1
        or transcription["vad_filter"] is not True
        or transcription["word_timestamps"] is not False
        or transcription["condition_on_previous_text"] is not True
        or transcription["chunk_seconds"] != 900.0
        or transcription["overlap_seconds"] != 5.0
    ):
        raise CandidateWorkerError("unsafe or unverified transcription settings")
    if not isinstance(transcription["language"], str) or not transcription["language"]:
        raise CandidateWorkerError("transcription language is invalid")
    preview = _strict_mapping(
        document["preview"],
        {"video_codec", "audio_codec", "preset", "crf", "movflags"},
        "preview",
    )
    if (
        preview["video_codec"] != "libx264"
        or preview["audio_codec"] != "aac"
        or preview["movflags"] != "+faststart"
        or preview["preset"] not in {"veryfast", "faster", "fast", "medium"}
        or isinstance(preview["crf"], bool)
        or not isinstance(preview["crf"], int)
        or not 0 <= preview["crf"] <= 51
    ):
        raise CandidateWorkerError("preview must use libx264/AAC with faststart")
    return document


def _transcribe_resumable(
    audio: Path,
    work_dir: Path,
    duration: float,
    run_dir: Path,
    settings: Mapping[str, Any],
    fingerprint: str,
    cancel_requested,
    update_status,
) -> dict[str, Any]:
    chunk_seconds = float(settings["chunk_seconds"])
    overlap = float(settings["overlap_seconds"])
    chunk_count = math.ceil(duration / chunk_seconds)
    chunks_dir = work_dir / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    model = None
    for index in range(chunk_count):
        _check_cancel(cancel_requested, run_dir)
        owned_start = index * chunk_seconds
        owned_end = min(duration, (index + 1) * chunk_seconds)
        input_start = max(0.0, owned_start - (overlap if index else 0.0))
        input_end = min(
            duration,
            owned_end + (overlap if index + 1 < chunk_count else 0.0),
        )
        window = {
            "index": index,
            "owned_start": owned_start,
            "owned_end": owned_end,
            "input_start": input_start,
            "input_end": input_end,
        }
        chunk_json = chunks_dir / f"{index:04d}.json"
        if chunk_json.exists():
            cached = _read_json_object(chunk_json)
            _validate_transcript_chunk(cached, fingerprint=fingerprint, window=window)
        else:
            if model is None:
                from faster_whisper import WhisperModel

                model = WhisperModel(
                    settings["model"],
                    device=settings["device"],
                    compute_type=settings["compute_type"],
                    local_files_only=True,
                )
            chunk_audio = work_dir / f"chunk-{index:04d}.wav"
            _extract_chunk(audio, chunk_audio, input_start, input_end)
            try:
                iterator, info = model.transcribe(
                    str(chunk_audio),
                    language=settings["language"],
                    beam_size=1,
                    vad_filter=True,
                    word_timestamps=False,
                    condition_on_previous_text=True,
                )
                segments = []
                for segment in iterator:
                    start = input_start + float(segment.start)
                    end = input_start + float(segment.end)
                    midpoint = (start + end) / 2.0
                    if midpoint < owned_start or (
                        midpoint >= owned_end and index + 1 < chunk_count
                    ):
                        continue
                    segments.append(
                        {
                            "start": start,
                            "end": end,
                            "text": str(segment.text).strip(),
                            "avg_logprob": float(segment.avg_logprob),
                            "no_speech_prob": float(segment.no_speech_prob),
                            "words": [],
                            "speaker": None,
                        }
                    )
                payload = {
                    "schema_version": 1,
                    "fingerprint_sha256": fingerprint,
                    "window": window,
                    "detected_language": str(info.language),
                    "language_probability": float(info.language_probability),
                    "segments": segments,
                }
                payload = _seal_transcript_chunk(payload)
                _validate_transcript_chunk(
                    payload,
                    fingerprint=fingerprint,
                    window=window,
                )
                _atomic_json(chunk_json, payload)
            finally:
                chunk_audio.unlink(missing_ok=True)
        update_status(
            run_dir,
            state="processing",
            stage="transcription",
            progress={"completed": index + 1, "total": chunk_count},
        )

    segments: list[dict[str, Any]] = []
    for index in range(chunk_count):
        payload = _read_json_object(chunks_dir / f"{index:04d}.json")
        owned_start = index * chunk_seconds
        owned_end = min(duration, (index + 1) * chunk_seconds)
        input_start = max(0.0, owned_start - (overlap if index else 0.0))
        input_end = min(
            duration,
            owned_end + (overlap if index + 1 < chunk_count else 0.0),
        )
        _validate_transcript_chunk(
            payload,
            fingerprint=fingerprint,
            window={
                "index": index,
                "owned_start": owned_start,
                "owned_end": owned_end,
                "input_start": input_start,
                "input_end": input_end,
            },
        )
        segments.extend(payload["segments"])
    segments.sort(key=lambda item: (item["start"], item["end"]))
    transcript = {
        "schema_version": 1,
        "source": {"duration_seconds": duration},
        "transcription": dict(settings),
        "segments": segments,
        "words": [],
    }
    _atomic_json(work_dir / "transcript.json", transcript)
    return transcript


def _chunk_content_sha256(value: Mapping[str, Any]) -> str:
    document = {key: item for key, item in value.items() if key != "content_sha256"}
    try:
        encoded = json.dumps(
            document,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CandidateWorkerError("transcript chunk cannot be hashed") from exc
    return hashlib.sha256(encoded).hexdigest()


def _seal_transcript_chunk(value: Mapping[str, Any]) -> dict[str, Any]:
    document = dict(value)
    document["content_sha256"] = _chunk_content_sha256(document)
    return document


def _validate_transcript_chunk(
    value: Mapping[str, Any], *, fingerprint: str, window: Mapping[str, Any]
) -> None:
    required = {
        "schema_version",
        "fingerprint_sha256",
        "window",
        "detected_language",
        "language_probability",
        "segments",
        "content_sha256",
    }
    if not isinstance(value, Mapping) or set(value) != required:
        raise CandidateWorkerError("cached transcript chunk has invalid fields")
    if value["schema_version"] != 1 or value["fingerprint_sha256"] != fingerprint:
        raise CandidateWorkerError("cached transcript chunk fingerprint mismatch")
    if value["window"] != dict(window):
        raise CandidateWorkerError("cached transcript chunk window mismatch")
    content_hash = value["content_sha256"]
    if (
        not isinstance(content_hash, str)
        or len(content_hash) != 64
        or content_hash != _chunk_content_sha256(value)
    ):
        raise CandidateWorkerError("cached transcript chunk integrity mismatch")
    language = value["detected_language"]
    probability = value["language_probability"]
    if (
        not isinstance(language, str)
        or not 1 <= len(language) <= 32
        or isinstance(probability, bool)
        or not isinstance(probability, (int, float))
        or not math.isfinite(float(probability))
        or not 0 <= float(probability) <= 1
    ):
        raise CandidateWorkerError("cached transcript language metadata is invalid")
    segments = value["segments"]
    if not isinstance(segments, list):
        raise CandidateWorkerError("cached transcript segments must be an array")
    previous_start = -1.0
    input_start = float(window["input_start"])
    input_end = float(window["input_end"])
    owned_start = float(window["owned_start"])
    owned_end = float(window["owned_end"])
    for segment in segments:
        if not isinstance(segment, Mapping) or set(segment) != {
            "start",
            "end",
            "text",
            "avg_logprob",
            "no_speech_prob",
            "words",
            "speaker",
        }:
            raise CandidateWorkerError("cached transcript segment has invalid fields")
        start = segment["start"]
        end = segment["end"]
        avg_logprob = segment["avg_logprob"]
        no_speech = segment["no_speech_prob"]
        if any(
            isinstance(number, bool)
            or not isinstance(number, (int, float))
            or not math.isfinite(float(number))
            for number in (start, end, avg_logprob, no_speech)
        ):
            raise CandidateWorkerError("cached transcript segment contains non-finite data")
        start_value = float(start)
        end_value = float(end)
        midpoint = (start_value + end_value) / 2.0
        if (
            start_value < input_start - 0.05
            or end_value > input_end + 0.05
            or end_value <= start_value
            or start_value < previous_start
            or midpoint < owned_start
            or midpoint > owned_end + 0.001
            or (input_end > owned_end and midpoint >= owned_end)
        ):
            raise CandidateWorkerError("cached transcript segment is outside its window")
        previous_start = start_value
        if (
            not isinstance(segment["text"], str)
            or len(segment["text"]) > 10_000
            or not 0 <= float(no_speech) <= 1
            or segment["words"] != []
            or segment["speaker"] is not None
        ):
            raise CandidateWorkerError("cached transcript segment is invalid")


def _ensure_audio(
    ffmpeg: Path, ffprobe: Path, source: Path, work_dir: Path, duration: float
) -> Path:
    output = work_dir / "source_16k.wav"
    if output.exists():
        if abs(_probe_duration(ffprobe, output) - duration) > 1.0:
            raise CandidateWorkerError("cached source audio duration mismatch")
        return output
    temporary = work_dir / "source_16k.tmp.wav"
    temporary.unlink(missing_ok=True)
    _run(
        [
            str(ffmpeg),
            "-y",
            "-i",
            str(source),
            "-map",
            "0:a:0",
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(temporary),
        ]
    )
    if abs(_probe_duration(ffprobe, temporary) - duration) > 1.0:
        temporary.unlink(missing_ok=True)
        raise CandidateWorkerError("extracted audio duration mismatch")
    os.replace(temporary, output)
    return output


def _extract_chunk(audio: Path, output: Path, start: float, end: float) -> None:
    ffmpeg = _resolve_media_tools()["ffmpeg"]
    output.unlink(missing_ok=True)
    _run(
        [
            str(ffmpeg),
            "-y",
            "-ss",
            f"{start:.3f}",
            "-t",
            f"{end - start:.3f}",
            "-i",
            str(audio),
            "-map",
            "0:a:0",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(output),
        ]
    )


def _render_preview(
    ffmpeg: Path,
    ffprobe: Path,
    source: Path,
    work_dir: Path,
    candidate: Mapping[str, Any],
    preview: Mapping[str, Any],
) -> Path:
    preview_dir = work_dir / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    output = preview_dir / f"{candidate['candidate_id']}.mp4"
    temporary = preview_dir / f".{candidate['candidate_id']}.tmp.mp4"
    temporary.unlink(missing_ok=True)
    expected = float(candidate["end"]) - float(candidate["start"])
    _run(
        [
            str(ffmpeg),
            "-y",
            "-ss",
            f"{float(candidate['start']):.3f}",
            "-t",
            f"{expected:.3f}",
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-c:v",
            "libx264",
            "-preset",
            str(preview["preset"]),
            "-crf",
            str(preview["crf"]),
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            "-avoid_negative_ts",
            "make_zero",
            str(temporary),
        ]
    )
    actual = _probe_duration(ffprobe, temporary)
    if abs(actual - expected) > 1.0:
        temporary.unlink(missing_ok=True)
        raise CandidateWorkerError("preview duration mismatch")
    os.replace(temporary, output)
    return output


def _worker_fingerprint(
    source_hash: str, duration: float, config: Mapping[str, Any], config_path: Path
) -> dict[str, Any]:
    config_hash = hashlib.sha256(config_path.read_bytes()).hexdigest()
    document = {
        "worker_version": WORKER_VERSION,
        "source_sha256": source_hash,
        "duration_seconds": duration,
        "config_sha256": config_hash,
        "transcription": config["transcription"],
    }
    encoded = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {**document, "fingerprint_sha256": hashlib.sha256(encoded).hexdigest()}


def _prepare_work_manifest(work_dir: Path, fingerprint: Mapping[str, Any]) -> None:
    path = work_dir / "worker-manifest.json"
    if path.exists():
        if _read_json_object(path) != fingerprint:
            raise CandidateWorkerError("existing candidate work fingerprint mismatch")
    else:
        _atomic_json(path, fingerprint)


def _manifest_value(manifest: Any, *names: str) -> Any:
    if not isinstance(manifest, Mapping):
        return None
    source = manifest.get("source")
    for name in names:
        if name in manifest:
            return manifest[name]
        if isinstance(source, Mapping) and name in source:
            return source[name]
    return None


def _resolve_media_tools() -> dict[str, Path]:
    result = {}
    for name in ("ffmpeg", "ffprobe"):
        found = shutil.which(name)
        if not found:
            raise CandidateWorkerError(f"{name} is not installed")
        result[name] = Path(found).resolve()
    return result


def _probe_duration(ffprobe: Path, path: Path) -> float:
    result = _run(
        [
            str(ffprobe),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            "--",
            str(path),
        ]
    )
    try:
        duration = float(result.stdout.strip())
    except ValueError as exc:
        raise CandidateWorkerError("ffprobe returned an invalid duration") from exc
    if not math.isfinite(duration) or duration <= 0:
        raise CandidateWorkerError("media duration must be positive and finite")
    return duration


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise CandidateWorkerError(
            f"media command failed ({result.returncode}): {result.stderr[-1000:]}"
        )
    return result


def _check_cancel(cancel_requested, run_dir: Path) -> None:
    if cancel_requested(run_dir):
        raise CandidateCancelled("candidate analysis was cancelled")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _read_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CandidateWorkerError(f"expected JSON object: {path.name}")
    return value


def _strict_mapping(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise CandidateWorkerError(f"{label} config has invalid fields")
    return value
