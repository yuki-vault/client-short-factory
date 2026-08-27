from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

from .artifacts import (
    NotFoundError,
    WORKFLOW_MANIFEST_VERSION,
    confined_job_path,
    initialize_machine_revision,
    load_current_caption,
    validate_safe_id,
)
from .settings import PROJECT_ROOT, load_config, resolve_tools
from .subtitles import Cue, build_cues, cue_report, write_ass, write_srt
from .utils import (
    atomic_write_json,
    format_timecode,
    parse_timecode,
    read_json,
    run_command,
    short_hash,
)


STAGES = ("acquire", "audio", "transcribe", "subtitles", "render", "qc")


@dataclass
class RunOptions:
    source: str
    start: str
    end: str
    job_id: str | None = None
    jobs_root: Path = PROJECT_ROOT / "jobs"
    template: str = "default"
    dictionary: str = "default"
    bgm: Path | None = None
    rights_confirmed: bool = False
    authorization_note: str = ""
    model: str | None = None
    device: str | None = None
    compute_type: str | None = None
    encoder: str | None = None
    vad_filter: bool | None = None
    keep_fillers: bool = False
    yt_dlp: str | None = None
    ffmpeg: str | None = None
    ffprobe: str | None = None
    acquire_mode: str = "auto"
    fallback_height: int | None = None
    rerun_from: str | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _file_identity(path: Path) -> dict[str, Any]:
    """Cheaply detect replacement of a local input without hashing huge media."""
    resolved = path.expanduser().resolve()
    stat = resolved.stat()
    return {
        "path": str(resolved),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def _is_url(value: str) -> bool:
    return urlparse(value).scheme.lower() in {"http", "https"}


def canonicalize_source(value: str) -> str:
    if not _is_url(value):
        return str(Path(value).expanduser().resolve())
    parsed = urlparse(value)
    host = parsed.netloc.lower().removeprefix("www.")
    video_id = ""
    if host in {"youtube.com", "m.youtube.com"}:
        if parsed.path.startswith("/live/") or parsed.path.startswith("/shorts/"):
            video_id = parsed.path.strip("/").split("/")[-1]
        elif parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
    elif host == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0]
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return value


def _safe_job_id(value: str) -> str:
    try:
        return validate_safe_id(value, "job id")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(
            "job-id must be a Windows-safe 1-80 character identifier using "
            "letters, numbers, dot, underscore, or hyphen"
        ) from exc


class Pipeline:
    def __init__(self, options: RunOptions):
        self.options = options
        self.source = canonicalize_source(options.source)
        self.start = parse_timecode(options.start)
        self.end = parse_timecode(options.end)
        if self.end <= self.start:
            raise ValueError("end time must be later than start time")
        self.duration = self.end - self.start
        if self.duration > 10 * 60:
            raise ValueError("MVP safety limit: one job must be 10 minutes or shorter")
        if _is_url(self.source) and not options.rights_confirmed:
            raise ValueError("URL input requires --rights-confirmed")
        if not _is_url(self.source) and not Path(self.source).is_file():
            raise FileNotFoundError(f"local source does not exist: {self.source}")
        if options.bgm and not options.bgm.is_file():
            raise FileNotFoundError(f"BGM file does not exist: {options.bgm}")

        self.config, self.dictionary = load_config(options.template, options.dictionary)
        transcription = self.config["transcription"]
        render = self.config["render"]
        if options.model:
            transcription["model"] = options.model
        if options.device:
            transcription["device"] = options.device
        if options.compute_type:
            transcription["compute_type"] = options.compute_type
        if options.encoder:
            render["encoder"] = options.encoder
        if options.vad_filter is not None:
            transcription["vad_filter"] = options.vad_filter
        if options.keep_fillers:
            self.config["subtitle"]["remove_fillers"] = False
        if options.fallback_height:
            self.config["download"]["fallback_height"] = options.fallback_height
        if options.acquire_mode not in {"auto", "partial", "full"}:
            raise ValueError("acquire_mode must be auto, partial, or full")
        if options.rerun_from:
            raise ValueError(
                "workflow jobs do not support mutable --rerun-from; "
                "use a new job or render-job --caption-revision"
            )

        self.tools = resolve_tools(options.yt_dlp, options.ffmpeg, options.ffprobe)
        generated_id = "job_" + short_hash(
            [self.source, str(self.start), str(self.end), options.template]
        )
        self.job_id = _safe_job_id(options.job_id or generated_id)
        jobs_root = options.jobs_root.expanduser().resolve()
        candidate = (jobs_root / self.job_id).resolve()
        try:
            candidate.relative_to(jobs_root)
        except ValueError as exc:
            raise ValueError("job path escapes jobs root") from exc
        self.job_dir = candidate
        existing_manifest = confined_job_path(self.job_dir, "job.json")
        if existing_manifest.is_file():
            existing_version = read_json(existing_manifest).get("version")
            if existing_version != WORKFLOW_MANIFEST_VERSION:
                raise RuntimeError(
                    f"job {self.job_id} is legacy/read-only; use a new --job-id"
                )
        self.source_dir = confined_job_path(self.job_dir, "source")
        self.audio_dir = confined_job_path(self.job_dir, "audio")
        self.transcript_dir = confined_job_path(self.job_dir, "transcript")
        self.subtitles_dir = confined_job_path(self.job_dir, "subtitles")
        self.output_dir = confined_job_path(self.job_dir, "output")
        self.logs_dir = confined_job_path(self.job_dir, "logs")
        for directory in (
            self.source_dir,
            self.audio_dir,
            self.transcript_dir,
            self.subtitles_dir,
            self.output_dir,
            self.logs_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

        self.logger = self._build_logger()
        self.state_path = confined_job_path(self.job_dir, "state.json")
        self.manifest_path = confined_job_path(self.job_dir, "job.json")
        self.state = (
            read_json(self.state_path)
            if self.state_path.is_file()
            else {"version": 1, "job_id": self.job_id, "stages": {}}
        )

        margin = float(self.config["download"]["margin_seconds"])
        self.source_start = max(0.0, self.start - margin)
        self.source_end = self.end + margin
        self.local_offset = self.start - self.source_start
        self.acquired_path = self.source_dir / "acquired.mp4"
        self.audio_path = self.audio_dir / "speech_16k.wav"
        self.raw_transcript_path = self.transcript_dir / "raw.json"
        self.transcript_text_path = self.transcript_dir / "transcript.txt"
        self.srt_path = self.subtitles_dir / "captions.srt"
        self.ass_path = self.subtitles_dir / "captions.ass"
        self.captions_json_path = self.subtitles_dir / "captions.json"
        self.subtitle_report_path = self.subtitles_dir / "report.json"
        self.output_path = self.output_dir / "short.mp4"
        self.preview_path = self.output_dir / "preview.jpg"
        self.qc_path = confined_job_path(self.job_dir, "qc.json")
        self._prepare_manifest()

    def _build_logger(self) -> logging.Logger:
        logger = logging.getLogger(f"client_short_factory.{self.job_id}")
        logger.setLevel(logging.INFO)
        for handler in logger.handlers:
            handler.close()
        logger.handlers.clear()
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        file_handler = logging.FileHandler(
            self.logs_dir / "pipeline.log", encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        return logger

    def _prepare_manifest(self) -> None:
        signature_parts = [
            self.source,
            f"{self.start:.3f}",
            f"{self.end:.3f}",
            json.dumps(self.config, ensure_ascii=False, sort_keys=True),
            json.dumps(self.dictionary, ensure_ascii=False, sort_keys=True),
            str(self.options.bgm.resolve()) if self.options.bgm else "",
        ]
        input_files: dict[str, dict[str, Any]] = {}
        if not _is_url(self.source):
            input_files["source"] = _file_identity(Path(self.source))
            signature_parts.append(
                json.dumps(input_files["source"], ensure_ascii=False, sort_keys=True)
            )
        if self.options.bgm:
            input_files["bgm"] = _file_identity(self.options.bgm)
            signature_parts.append(
                json.dumps(input_files["bgm"], ensure_ascii=False, sort_keys=True)
            )
        signature = short_hash(signature_parts)
        manifest = {
            "version": WORKFLOW_MANIFEST_VERSION,
            "job_id": self.job_id,
            "signature": signature,
            "source": self.source,
            "source_type": "url" if _is_url(self.source) else "local",
            "start_seconds": self.start,
            "end_seconds": self.end,
            "duration_seconds": self.duration,
            "download_window": {
                "start_seconds": self.source_start,
                "end_seconds": self.source_end,
                "local_target_offset_seconds": self.local_offset,
            },
            "template": self.options.template,
            "dictionary": self.options.dictionary,
            "config": self.config,
            "rights": {
                "confirmed": bool(self.options.rights_confirmed),
                "authorization_note": self.options.authorization_note,
            },
            "privacy": {
                "local_processing_only": True,
                "automatic_upload": False,
            },
            "tools": {name: str(path) for name, path in self.tools.items()},
            "input_files": input_files,
            "created_at": _now(),
        }
        if self.manifest_path.is_file():
            existing = read_json(self.manifest_path)
            if existing.get("signature") != signature:
                raise RuntimeError(
                    f"job {self.job_id} already exists with different inputs; use another --job-id"
                )
            return
        atomic_write_json(self.manifest_path, manifest)

    def _save_state(self) -> None:
        self.state["updated_at"] = _now()
        atomic_write_json(self.state_path, self.state)

    def _reset_from(self, stage: str) -> None:
        if stage not in STAGES:
            raise ValueError(f"unknown rerun stage: {stage}")
        start_index = STAGES.index(stage)
        for name in STAGES[start_index:]:
            self.state["stages"].pop(name, None)
        self._save_state()
        self.logger.warning("RESET stages from %s for explicit rerun", stage)

    @staticmethod
    def _outputs_ready(outputs: list[Path]) -> bool:
        return all(path.is_file() and path.stat().st_size > 0 for path in outputs)

    def _stage(
        self, stage: str, outputs: list[Path], action: Callable[[], None]
    ) -> None:
        record = self.state["stages"].get(stage, {})
        if record.get("status") == "complete" and self._outputs_ready(outputs):
            self.logger.info("SKIP completed stage: %s", stage)
            return
        self.logger.info("START stage: %s", stage)
        self.state["stages"][stage] = {
            "status": "running",
            "started_at": _now(),
            "outputs": [str(path) for path in outputs],
        }
        self._save_state()
        try:
            action()
            if not self._outputs_ready(outputs):
                raise RuntimeError(f"stage {stage} completed without expected outputs")
        except Exception as exc:
            self.state["stages"][stage].update(
                {"status": "failed", "failed_at": _now(), "error": str(exc)}
            )
            self._save_state()
            self.logger.exception("FAILED stage: %s", stage)
            raise
        self.state["stages"][stage].update(
            {"status": "complete", "completed_at": _now(), "error": None}
        )
        self._save_state()
        self.logger.info("COMPLETE stage: %s", stage)

    def run(self) -> Path:
        self.logger.info(
            "JOB %s source=%s range=%s-%s",
            self.job_id,
            self.source,
            format_timecode(self.start),
            format_timecode(self.end),
        )
        self.run_until_subtitles()
        self._stage("render", [self.output_path], self._render)
        self._stage("qc", [self.qc_path, self.preview_path], self._quality_check)
        self.logger.info("DONE %s", self.output_path)
        return self.output_path

    def run_until_subtitles(self) -> dict[str, Any]:
        """Run the shared acquisition/transcription path without a mutable render.

        Candidate adoption uses this boundary and then publishes one explicit
        immutable render for caption revision 1.
        """
        self._stage("acquire", [self.acquired_path], self._acquire)
        self._stage("audio", [self.audio_path], self._extract_audio)
        self._stage(
            "transcribe",
            [self.raw_transcript_path, self.transcript_text_path],
            self._transcribe,
        )
        self._stage(
            "subtitles",
            [
                self.srt_path,
                self.ass_path,
                self.captions_json_path,
                self.subtitle_report_path,
            ],
            self._create_subtitles,
        )
        return load_current_caption(self.job_dir)

    def _acquire(self) -> None:
        if _is_url(self.source):
            partial_error: Exception | None = None
            if self.options.acquire_mode in {"auto", "partial"}:
                try:
                    self._download_partial()
                    return
                except Exception as exc:
                    partial_error = exc
                    self.logger.warning("Partial URL acquisition failed: %s", exc)
            if self.options.acquire_mode == "partial":
                raise RuntimeError("partial URL acquisition failed") from partial_error
            self.logger.info("Using resumable full-source cache fallback")
            cached_source = self._download_full_cache()
            self._slice_source(cached_source)
        else:
            self._slice_source(Path(self.source))

    def _download_partial(self) -> None:
        section = (
            "*"
            + format_timecode(self.source_start)
            + "-"
            + format_timecode(self.source_end)
        )
        max_height = int(self.config["download"]["max_height"])
        output_template = self.source_dir / "acquired.download.%(ext)s"
        for stale in self.source_dir.glob("acquired.download*"):
            if stale.is_file():
                stale.unlink()
        command = [
            str(self.tools["yt_dlp"]),
            "--force-ipv4",
            "--no-progress",
            "--no-playlist",
            "--force-overwrites",
            "--write-info-json",
            "--download-sections",
            section,
            "--force-keyframes-at-cuts",
            "--ffmpeg-location",
            str(self.tools["ffmpeg"].parent),
            "-f",
            (
                f"bv*[height<={max_height}][vcodec^=avc1]+ba[ext=m4a]/"
                f"b[height<={max_height}][ext=mp4]/"
                f"bv*[height<={max_height}]+ba/b[height<={max_height}]"
            ),
            "--merge-output-format",
            "mp4",
            "--output",
            str(output_template),
            self.source,
        ]
        try:
            run_command(
                command,
                self.logger,
                timeout=float(
                    self.config["download"].get("partial_timeout_seconds", 120)
                ),
            )
            candidates = [
                path
                for path in self.source_dir.glob("acquired.download.*")
                if path.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}
                and path.stat().st_size > 0
            ]
            if not candidates:
                raise RuntimeError("yt-dlp did not produce a complete section file")
            selected = max(candidates, key=lambda path: path.stat().st_size)
            self._validate_media(
                selected,
                min_duration=max(0.1, self.source_end - self.source_start - 1.0),
            )
            os.replace(selected, self.acquired_path)
        except Exception:
            for temporary in self.source_dir.glob("acquired.download*"):
                if temporary.is_file():
                    temporary.unlink()
            raise

    def _source_cache_key(self) -> str:
        parsed = urlparse(self.source)
        video_id = parse_qs(parsed.query).get("v", [""])[0]
        return re.sub(r"[^A-Za-z0-9._-]", "_", video_id) or short_hash([self.source])

    def _download_full_cache(self) -> Path:
        height = int(self.config["download"].get("fallback_height", 360))
        cache_dir = (
            self.options.jobs_root.expanduser().resolve()
            / "_source_cache"
            / self._source_cache_key()
            / f"{height}p"
        )
        cache_dir.mkdir(parents=True, exist_ok=True)
        existing = [
            path
            for path in cache_dir.glob("full.*")
            if path.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}
            and path.stat().st_size > 0
        ]
        if existing:
            selected = max(existing, key=lambda path: path.stat().st_size)
            try:
                self._validate_source_cache(selected, cache_dir, height)
            except Exception as exc:
                self.logger.warning("Ignoring invalid source cache %s: %s", selected, exc)
                quarantine_dir = cache_dir / "invalid"
                quarantine_dir.mkdir(parents=True, exist_ok=True)
                stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
                quarantine = quarantine_dir / f"{selected.name}.{stamp}"
                os.replace(selected, quarantine)
                self.logger.warning("Quarantined invalid cache as %s", quarantine)
            else:
                self.logger.info("Reusing validated source cache: %s", selected)
                return selected
        output_template = cache_dir / "full.%(ext)s"
        if height <= 360:
            selector = (
                f"b[height<={height}][ext=mp4]/"
                f"bv*[height<={height}][vcodec^=avc1]+ba[ext=m4a]/"
                f"bv*[height<={height}]+ba/b[height<={height}]"
            )
        else:
            selector = (
                f"bv*[height<={height}][vcodec^=avc1]+ba[ext=m4a]/"
                f"bv*[height<={height}]+ba/b[height<={height}]"
            )
        run_command(
            [
                str(self.tools["yt_dlp"]),
                "--force-ipv4",
                "--no-progress",
                "--no-playlist",
                "--continue",
                "--write-info-json",
                "--ffmpeg-location",
                str(self.tools["ffmpeg"].parent),
                "-f",
                selector,
                "--merge-output-format",
                "mkv",
                "--output",
                str(output_template),
                self.source,
            ],
            self.logger,
        )
        downloaded = [
            path
            for path in cache_dir.glob("full.*")
            if path.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}
            and path.stat().st_size > 0
        ]
        if not downloaded:
            raise RuntimeError("full-source fallback did not produce a media file")
        selected = max(downloaded, key=lambda path: path.stat().st_size)
        self._validate_source_cache(selected, cache_dir, height)
        return selected

    def _probe_media(self, path: Path) -> dict[str, Any]:
        result = run_command(
            [
                str(self.tools["ffprobe"]),
                "-v",
                "error",
                "-show_entries",
                "format=duration,size:stream=codec_type,codec_name,width,height",
                "-of",
                "json",
                str(path),
            ],
            self.logger,
        )
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"ffprobe returned invalid JSON for {path}") from exc

    def _validate_media(
        self,
        path: Path,
        *,
        min_duration: float = 0.1,
        require_video: bool = True,
        require_audio: bool = True,
        min_height: int | None = None,
        max_height: int | None = None,
        expected_width: int | None = None,
        expected_height: int | None = None,
    ) -> dict[str, Any]:
        if not path.is_file() or path.stat().st_size <= 0:
            raise RuntimeError(f"media file is missing or empty: {path}")
        metadata = self._probe_media(path)
        streams = metadata.get("streams", [])
        videos = [item for item in streams if item.get("codec_type") == "video"]
        audios = [item for item in streams if item.get("codec_type") == "audio"]
        duration = float(metadata.get("format", {}).get("duration") or 0)
        if require_video and not videos:
            raise RuntimeError(f"media has no video stream: {path}")
        if require_audio and not audios:
            raise RuntimeError(f"media has no audio stream: {path}")
        if duration < min_duration:
            raise RuntimeError(
                f"media is too short ({duration:.3f}s < {min_duration:.3f}s): {path}"
            )
        if min_height is not None and videos:
            actual_height = int(videos[0].get("height") or 0)
            if actual_height < min_height:
                raise RuntimeError(
                    f"video height is below cache target ({actual_height} < {min_height}): {path}"
                )
        if max_height is not None and videos:
            actual_height = int(videos[0].get("height") or 0)
            if actual_height > max_height:
                raise RuntimeError(
                    f"video height exceeds cache policy ({actual_height} > {max_height}): {path}"
                )
        if expected_width is not None and videos:
            actual_width = int(videos[0].get("width") or 0)
            if actual_width != expected_width:
                raise RuntimeError(
                    f"unexpected video width ({actual_width} != {expected_width}): {path}"
                )
        if expected_height is not None and videos:
            actual_height = int(videos[0].get("height") or 0)
            if actual_height != expected_height:
                raise RuntimeError(
                    f"unexpected video height ({actual_height} != {expected_height}): {path}"
                )
        return metadata

    def _validate_decode(self, path: Path) -> None:
        result = run_command(
            [
                str(self.tools["ffmpeg"]),
                "-v",
                "error",
                "-xerror",
                "-i",
                str(path),
                "-map",
                "0:v:0",
                "-map",
                "0:a:0?",
                "-f",
                "null",
                "NUL" if os.name == "nt" else "/dev/null",
            ],
            self.logger,
            check=False,
        )
        if result.returncode != 0:
            tail = (result.stderr or result.stdout)[-4000:]
            raise RuntimeError(f"media decode validation failed for {path}: {tail}")

    def _validate_source_cache(
        self, path: Path, cache_dir: Path, requested_height: int
    ) -> None:
        advertised_height: int | None = None
        info_path = cache_dir / "full.info.json"
        if info_path.is_file():
            try:
                advertised_height = int(read_json(info_path).get("height") or 0) or None
            except (ValueError, TypeError, json.JSONDecodeError):
                self.logger.warning("Could not read cache height from %s", info_path)
        minimum_height = (
            min(requested_height, advertised_height)
            if advertised_height is not None
            else None
        )
        metadata = self._validate_media(
            path,
            min_duration=max(0.1, self.source_end - 1.0),
            min_height=minimum_height,
            max_height=requested_height,
        )
        video = next(
            item
            for item in metadata.get("streams", [])
            if item.get("codec_type") == "video"
        )
        atomic_write_json(
            cache_dir / "validation.json",
            {
                "path": str(path),
                "requested_height": requested_height,
                "advertised_height": advertised_height,
                "actual_width": int(video.get("width") or 0),
                "actual_height": int(video.get("height") or 0),
                "duration": float(metadata.get("format", {}).get("duration") or 0),
                "checked_at": _now(),
            },
        )

    def _slice_command(
        self, source: Path, encoder: str, destination: Path
    ) -> list[str]:
        source_duration = self.source_end - self.source_start
        command = [
            str(self.tools["ffmpeg"]),
            "-y",
            "-ss",
            f"{self.source_start:.3f}",
            "-t",
            f"{source_duration:.3f}",
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0?",
        ]
        if encoder == "h264_nvenc":
            command.extend(
                ["-c:v", "h264_nvenc", "-preset", "p4", "-rc", "vbr", "-cq", "20", "-b:v", "0"]
            )
        else:
            command.extend(["-c:v", "libx264", "-preset", "veryfast", "-crf", "18"])
        command.extend(
            [
                "-c:a",
                "aac",
                "-b:a",
                "160k",
                "-movflags",
                "+faststart",
                str(destination),
            ]
        )
        return command

    def _slice_source(self, source: Path) -> None:
        temporary = self.acquired_path.with_name("acquired.tmp.mp4")
        temporary.unlink(missing_ok=True)
        result = run_command(
            self._slice_command(source, "h264_nvenc", temporary),
            self.logger,
            check=False,
        )
        if result.returncode != 0:
            temporary.unlink(missing_ok=True)
            self.logger.warning("NVENC source slicing failed; retrying with libx264")
            run_command(
                self._slice_command(source, "libx264", temporary), self.logger
            )
        try:
            self._validate_media(
                temporary,
                min_duration=max(0.1, self.source_end - self.source_start - 0.5),
            )
            os.replace(temporary, self.acquired_path)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    def _extract_audio(self) -> None:
        temporary = self.audio_path.with_name("speech_16k.tmp.wav")
        temporary.unlink(missing_ok=True)
        try:
            run_command(
                [
                    str(self.tools["ffmpeg"]),
                    "-y",
                    "-ss",
                    f"{self.local_offset:.3f}",
                    "-t",
                    f"{self.duration:.3f}",
                    "-i",
                    str(self.acquired_path),
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
                ],
                self.logger,
            )
            self._validate_media(
                temporary,
                min_duration=max(0.1, self.duration - 0.35),
                require_video=False,
            )
            os.replace(temporary, self.audio_path)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    def _transcribe_once(self, device: str, compute_type: str) -> dict[str, Any]:
        from faster_whisper import WhisperModel

        transcription = self.config["transcription"]
        self.logger.info(
            "Loading Whisper model=%s device=%s compute_type=%s",
            transcription["model"],
            device,
            compute_type,
        )
        model = WhisperModel(
            transcription["model"], device=device, compute_type=compute_type
        )
        prompt_terms = self.dictionary.get("prompt_terms", [])
        segments_iterator, info = model.transcribe(
            str(self.audio_path),
            language=transcription.get("language", "ja"),
            beam_size=int(transcription.get("beam_size", 5)),
            vad_filter=bool(transcription.get("vad_filter", False)),
            word_timestamps=bool(transcription.get("word_timestamps", True)),
            initial_prompt="、".join(prompt_terms) if prompt_terms else None,
            condition_on_previous_text=True,
        )
        segments: list[dict[str, Any]] = []
        all_words: list[dict[str, Any]] = []
        for segment in segments_iterator:
            words: list[dict[str, Any]] = []
            if segment.words:
                for word in segment.words:
                    item = {
                        "start": float(word.start),
                        "end": float(word.end),
                        "word": word.word,
                        "probability": (
                            float(word.probability)
                            if word.probability is not None
                            else None
                        ),
                    }
                    words.append(item)
                    all_words.append(item)
            else:
                text = segment.text.strip()
                if text:
                    chunks = list(text)
                    span = max(0.05, float(segment.end) - float(segment.start))
                    for index, character in enumerate(chunks):
                        item = {
                            "start": float(segment.start) + span * index / len(chunks),
                            "end": float(segment.start)
                            + span * (index + 1) / len(chunks),
                            "word": character,
                            "probability": None,
                        }
                        words.append(item)
                        all_words.append(item)
            segments.append(
                {
                    "start": float(segment.start),
                    "end": float(segment.end),
                    "text": segment.text.strip(),
                    "avg_logprob": float(segment.avg_logprob),
                    "no_speech_prob": float(segment.no_speech_prob),
                    "words": words,
                    "speaker": None,
                }
            )
        return {
            "model": transcription["model"],
            "device": device,
            "compute_type": compute_type,
            "language": info.language,
            "language_probability": float(info.language_probability),
            "duration": float(info.duration),
            "segments": segments,
            "words": all_words,
        }

    def _transcribe(self) -> None:
        transcription = self.config["transcription"]
        device = str(transcription.get("device", "cpu"))
        compute_type = str(transcription.get("compute_type", "int8"))
        try:
            result = self._transcribe_once(device, compute_type)
        except Exception:
            if device == "cpu":
                raise
            self.logger.exception("GPU transcription failed; retrying on CPU int8")
            result = self._transcribe_once("cpu", "int8")
            result["fallback_from"] = {
                "device": device,
                "compute_type": compute_type,
            }
        atomic_write_json(self.raw_transcript_path, result)
        transcript = "".join(segment["text"] for segment in result["segments"])
        self.transcript_text_path.write_text(transcript + "\n", encoding="utf-8")

    def _create_subtitles(self) -> None:
        try:
            caption_document = load_current_caption(self.job_dir)
            cues = [
                Cue(float(cue["start"]), float(cue["end"]), str(cue["text"]))
                for cue in caption_document["cues"]
            ]
        except NotFoundError:
            raw = read_json(self.raw_transcript_path)
            cues = build_cues(
                raw.get("words", []),
                self.config["subtitle"],
                self.dictionary.get("replacements", {}),
            )
            if not cues:
                raise RuntimeError("transcription produced no subtitle cues")
            caption_document = initialize_machine_revision(
                self.job_dir,
                [
                    {"start": cue.start, "end": cue.end, "text": cue.text}
                    for cue in cues
                ],
            )
        write_srt(self.srt_path, cues)
        write_ass(
            self.ass_path, cues, self.config["canvas"], self.config["subtitle"]
        )
        atomic_write_json(self.captions_json_path, caption_document)
        report = cue_report(cues, self.config["subtitle"], self.duration)
        atomic_write_json(self.subtitle_report_path, report)
        if report["issues"]:
            raise RuntimeError("subtitle validation failed: " + "; ".join(report["issues"]))
        cleaned = "\n".join(cue.text.replace("\n", "") for cue in cues)
        (self.transcript_dir / "caption_text.txt").write_text(
            cleaned + "\n", encoding="utf-8"
        )

    def _render_command(self, encoder: str, destination: Path) -> list[str]:
        canvas = self.config["canvas"]
        audio = self.config["audio"]
        render = self.config["render"]
        width = int(canvas["width"])
        height = int(canvas["height"])
        fps = int(canvas["fps"])
        blur = int(canvas.get("blur_radius", 28))
        brightness = float(canvas.get("background_brightness", -0.2))
        video_graph = (
            f"[0:v:0]split=2[bg][fg];"
            f"[bg]scale={width}:{height}:force_original_aspect_ratio=increase:"
            f"force_divisible_by=2,crop={width}:{height},gblur=sigma={blur},"
            f"eq=brightness={brightness}:saturation=0.85[bgv];"
            f"[fg]scale={width}:{height}:force_original_aspect_ratio=decrease:"
            f"force_divisible_by=2[fgv];"
            f"[bgv][fgv]overlay=(W-w)/2:(H-h)/2,"
            f"subtitles=filename='captions.ass',fps={fps},setsar=1,"
            f"format=yuv420p[v]"
        )
        loudnorm = (
            f"loudnorm=I={audio['target_lufs']}:TP={audio['true_peak']}:"
            f"LRA={audio['lra']}"
        )
        command = [
            str(self.tools["ffmpeg"]),
            "-y",
            "-ss",
            f"{self.local_offset:.3f}",
            "-i",
            str(self.acquired_path),
        ]
        if self.options.bgm:
            command.extend(["-stream_loop", "-1", "-i", str(self.options.bgm)])
            fade_start = max(0.0, self.duration - 1.0)
            audio_graph = (
                f"[0:a:0]{loudnorm},aresample=48000[voice];"
                f"[1:a:0]atrim=duration={self.duration:.3f},asetpts=N/SR/TB,"
                f"volume={audio['bgm_volume']},afade=t=out:st={fade_start:.3f}:d=1[music];"
                f"[voice][music]amix=inputs=2:duration=first:dropout_transition=2[a]"
            )
        else:
            audio_graph = f"[0:a:0]{loudnorm},aresample=48000[a]"
        command.extend(
            [
                "-t",
                f"{self.duration:.3f}",
                "-filter_complex",
                video_graph + ";" + audio_graph,
                "-map",
                "[v]",
                "-map",
                "[a]",
            ]
        )
        if encoder == "h264_nvenc":
            command.extend(
                [
                    "-c:v",
                    "h264_nvenc",
                    "-preset",
                    str(render["nvenc_preset"]),
                    "-rc",
                    "vbr",
                    "-cq",
                    str(render["nvenc_cq"]),
                    "-b:v",
                    "0",
                ]
            )
        else:
            command.extend(
                [
                    "-c:v",
                    "libx264",
                    "-preset",
                    str(render["x264_preset"]),
                    "-crf",
                    str(render["x264_crf"]),
                ]
            )
        command.extend(
            [
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                str(render["audio_bitrate"]),
                "-ar",
                "48000",
                "-ac",
                "2",
                "-movflags",
                "+faststart",
                "-map_metadata",
                "-1",
                str(destination),
            ]
        )
        return command

    def _render(self) -> None:
        requested = str(self.config["render"].get("encoder", "auto"))
        first_encoder = "h264_nvenc" if requested == "auto" else requested
        temporary = self.output_path.with_name("short.tmp.mp4")
        temporary.unlink(missing_ok=True)
        result = run_command(
            self._render_command(first_encoder, temporary),
            self.logger,
            cwd=self.subtitles_dir,
            check=False,
        )
        if result.returncode != 0 and (requested != "auto" or first_encoder == "libx264"):
            temporary.unlink(missing_ok=True)
            tail = (result.stderr or result.stdout)[-4000:]
            raise RuntimeError(f"render failed with {first_encoder}: {tail}")
        if result.returncode != 0:
            temporary.unlink(missing_ok=True)
            self.logger.warning("NVENC render failed; retrying with libx264")
            run_command(
                self._render_command("libx264", temporary),
                self.logger,
                cwd=self.subtitles_dir,
            )
        try:
            canvas = self.config["canvas"]
            self._validate_media(
                temporary,
                min_duration=max(0.1, self.duration - 0.35),
                expected_width=int(canvas["width"]),
                expected_height=int(canvas["height"]),
            )
            self._validate_decode(temporary)
            os.replace(temporary, self.output_path)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    def _quality_check(self) -> None:
        probe = run_command(
            [
                str(self.tools["ffprobe"]),
                "-v",
                "error",
                "-show_entries",
                (
                    "format=format_name,start_time,duration,size:"
                    "stream=index,codec_type,codec_name,profile,width,height,"
                    "sample_aspect_ratio,pix_fmt,r_frame_rate,avg_frame_rate,"
                    "sample_rate,channels,start_time,duration"
                ),
                "-of",
                "json",
                str(self.output_path),
            ],
            self.logger,
        )
        metadata = json.loads(probe.stdout)
        videos = [
            stream
            for stream in metadata.get("streams", [])
            if stream.get("codec_type") == "video"
        ]
        audios = [
            stream
            for stream in metadata.get("streams", [])
            if stream.get("codec_type") == "audio"
        ]
        checks: dict[str, bool] = {}
        video = videos[0] if videos else {}
        audio = audios[0] if audios else {}
        canvas = self.config["canvas"]
        checks["one_video_stream"] = len(videos) == 1
        checks["one_audio_stream"] = len(audios) == 1
        checks["h264"] = video.get("codec_name") == "h264"
        checks["resolution"] = (
            video.get("width") == int(canvas["width"])
            and video.get("height") == int(canvas["height"])
        )
        checks["pixel_format"] = video.get("pix_fmt") == "yuv420p"
        checks["frame_rate"] = video.get("avg_frame_rate") == f"{int(canvas['fps'])}/1"
        checks["aac"] = audio.get("codec_name") == "aac"
        checks["audio_48khz"] = audio.get("sample_rate") == "48000"
        checks["audio_stereo"] = audio.get("channels") == 2
        actual_duration = float(metadata.get("format", {}).get("duration", 0))
        checks["duration"] = abs(actual_duration - self.duration) <= 0.35
        checks["file_size"] = self.output_path.stat().st_size > 100_000

        decode = run_command(
            [
                str(self.tools["ffmpeg"]),
                "-v",
                "error",
                "-xerror",
                "-i",
                str(self.output_path),
                "-map",
                "0:v:0",
                "-map",
                "0:a:0?",
                "-f",
                "null",
                "NUL" if os.name == "nt" else "/dev/null",
            ],
            self.logger,
            check=False,
        )
        checks["decode_clean"] = decode.returncode == 0
        subtitle_report = read_json(self.subtitle_report_path)
        checks["subtitle_rules"] = not subtitle_report.get("issues")

        qc = {
            "passed": all(checks.values()),
            "technical_checks_passed": all(checks.values()),
            "semantic_transcript_accuracy_checked": False,
            "human_caption_review_required": True,
            "checks": checks,
            "expected_duration": self.duration,
            "actual_duration": actual_duration,
            "ffprobe": metadata,
            "subtitle_report": subtitle_report,
            "checked_at": _now(),
        }
        atomic_write_json(self.qc_path, qc)

        run_command(
            [
                str(self.tools["ffmpeg"]),
                "-y",
                "-ss",
                f"{self.duration / 2:.3f}",
                "-i",
                str(self.output_path),
                "-frames:v",
                "1",
                "-update",
                "1",
                "-q:v",
                "2",
                str(self.preview_path),
            ],
            self.logger,
        )
        if not qc["passed"]:
            failures = [name for name, passed in checks.items() if not passed]
            raise RuntimeError("quality checks failed: " + ", ".join(failures))
