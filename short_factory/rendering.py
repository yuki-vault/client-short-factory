from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Mapping

from .artifacts import (
    ValidationError,
    confined_job_path,
    ensure_workflow_job,
    publish_render,
)
from .subtitles import Cue, cue_report, write_ass, write_srt
from .utils import atomic_write_json, run_command


def _logger_for(job_dir: Path) -> logging.Logger:
    logger = logging.getLogger(f"client_short_factory.revision_render.{job_dir.name}")
    logger.setLevel(logging.INFO)
    for handler in logger.handlers:
        handler.close()
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    log_dir = confined_job_path(job_dir, "logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(
        log_dir / "revision-render.log",
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def _tool(job: Mapping[str, Any], name: str) -> Path:
    tools = job.get("tools")
    if not isinstance(tools, Mapping):
        raise ValidationError("job tool metadata is missing")
    raw = tools.get(name)
    if not isinstance(raw, str):
        raise ValidationError(f"job tool is missing: {name}")
    path = Path(raw).expanduser().resolve()
    if not path.is_file():
        raise ValidationError(f"job tool no longer exists: {name}")
    return path


def _render_command(
    *,
    job: Mapping[str, Any],
    job_dir: Path,
    encoder: str,
    destination: Path,
) -> list[str]:
    config = job.get("config")
    if not isinstance(config, Mapping):
        raise ValidationError("job config is missing")
    canvas = config["canvas"]
    audio = config["audio"]
    render = config["render"]
    width = int(canvas["width"])
    height = int(canvas["height"])
    fps = int(canvas["fps"])
    blur = int(canvas.get("blur_radius", 28))
    brightness = float(canvas.get("background_brightness", -0.2))
    duration = float(job["duration_seconds"])
    download_window = job.get("download_window", {})
    local_offset = float(download_window.get("local_target_offset_seconds", 0.0))
    acquired_path = confined_job_path(job_dir, "source", "acquired.mp4")
    if not acquired_path.is_file():
        raise ValidationError("acquired source is missing")

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
        str(_tool(job, "ffmpeg")),
        "-y",
        "-ss",
        f"{local_offset:.3f}",
        "-i",
        str(acquired_path),
    ]
    input_files = job.get("input_files", {})
    bgm = input_files.get("bgm") if isinstance(input_files, Mapping) else None
    bgm_path: Path | None = None
    if isinstance(bgm, Mapping) and isinstance(bgm.get("path"), str):
        bgm_path = Path(bgm["path"]).expanduser().resolve()
        if not bgm_path.is_file():
            raise ValidationError("configured BGM no longer exists")
    if bgm_path:
        command.extend(["-stream_loop", "-1", "-i", str(bgm_path)])
        fade_start = max(0.0, duration - 1.0)
        audio_graph = (
            f"[0:a:0]{loudnorm},aresample=48000[voice];"
            f"[1:a:0]atrim=duration={duration:.3f},asetpts=N/SR/TB,"
            f"volume={audio['bgm_volume']},"
            f"afade=t=out:st={fade_start:.3f}:d=1[music];"
            "[voice][music]amix=inputs=2:duration=first:dropout_transition=2[a]"
        )
    else:
        audio_graph = f"[0:a:0]{loudnorm},aresample=48000[a]"
    command.extend(
        [
            "-t",
            f"{duration:.3f}",
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


def _probe_and_validate(
    *,
    job: Mapping[str, Any],
    video_path: Path,
    logger: logging.Logger,
) -> tuple[dict[str, Any], dict[str, bool]]:
    config = job["config"]
    canvas = config["canvas"]
    probe = run_command(
        [
            str(_tool(job, "ffprobe")),
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
            str(video_path),
        ],
        logger,
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
    video = videos[0] if videos else {}
    audio = audios[0] if audios else {}
    expected_duration = float(job["duration_seconds"])
    actual_duration = float(metadata.get("format", {}).get("duration", 0))
    checks = {
        "one_video_stream": len(videos) == 1,
        "one_audio_stream": len(audios) == 1,
        "h264": video.get("codec_name") == "h264",
        "resolution": (
            video.get("width") == int(canvas["width"])
            and video.get("height") == int(canvas["height"])
        ),
        "pixel_format": video.get("pix_fmt") == "yuv420p",
        "frame_rate": video.get("avg_frame_rate") == f"{int(canvas['fps'])}/1",
        "aac": audio.get("codec_name") == "aac",
        "audio_48khz": audio.get("sample_rate") == "48000",
        "audio_stereo": audio.get("channels") == 2,
        "duration": abs(actual_duration - expected_duration) <= 0.35,
        "file_size": video_path.stat().st_size > 100_000,
    }
    decode = run_command(
        [
            str(_tool(job, "ffmpeg")),
            "-v",
            "error",
            "-xerror",
            "-i",
            str(video_path),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0?",
            "-f",
            "null",
            "NUL" if os.name == "nt" else "/dev/null",
        ],
        logger,
        check=False,
    )
    checks["decode_clean"] = decode.returncode == 0
    return metadata, checks


def ffmpeg_renderer(
    job_dir: Path,
    caption: Mapping[str, Any],
    render_dir: Path,
) -> Mapping[str, Any]:
    job = ensure_workflow_job(job_dir)
    config = job["config"]
    logger = _logger_for(job_dir)
    cues = [
        Cue(float(cue["start"]), float(cue["end"]), str(cue["text"]))
        for cue in caption["cues"]
    ]
    report = cue_report(cues, config["subtitle"], float(job["duration_seconds"]))
    if report.get("issues"):
        raise ValidationError(
            "subtitle validation failed: " + "; ".join(report["issues"])
        )
    write_ass(render_dir / "captions.ass", cues, config["canvas"], config["subtitle"])
    write_srt(render_dir / "captions.srt", cues)

    requested = str(config["render"].get("encoder", "auto"))
    first_encoder = "h264_nvenc" if requested == "auto" else requested
    if first_encoder not in {"h264_nvenc", "libx264"}:
        raise ValidationError("unsupported encoder")
    video_path = render_dir / "short.mp4"
    result = run_command(
        _render_command(
            job=job,
            job_dir=job_dir,
            encoder=first_encoder,
            destination=video_path,
        ),
        logger,
        cwd=render_dir,
        check=False,
    )
    used_encoder = first_encoder
    if result.returncode != 0:
        video_path.unlink(missing_ok=True)
        if requested != "auto" or first_encoder == "libx264":
            tail = (result.stderr or result.stdout)[-4000:]
            raise RuntimeError(f"render failed with {first_encoder}: {tail}")
        logger.warning("NVENC render failed; retrying with libx264")
        used_encoder = "libx264"
        run_command(
            _render_command(
                job=job,
                job_dir=job_dir,
                encoder=used_encoder,
                destination=video_path,
            ),
            logger,
            cwd=render_dir,
        )

    metadata, checks = _probe_and_validate(
        job=job,
        video_path=video_path,
        logger=logger,
    )
    checks["subtitle_rules"] = not report.get("issues")
    passed = all(checks.values())
    qc = {
        "schema_version": 1,
        "passed": passed,
        "technical_checks_passed": passed,
        "content_review": "pending",
        "checks": checks,
        "expected_duration": float(job["duration_seconds"]),
        "actual_duration": float(metadata.get("format", {}).get("duration", 0)),
        "ffprobe": metadata,
        "subtitle_report": report,
    }
    atomic_write_json(render_dir / "qc.json", qc)
    if not passed:
        failures = [name for name, value in checks.items() if not value]
        raise ValidationError("quality checks failed: " + ", ".join(failures))
    return {"engine": "ffmpeg", "encoder": used_encoder}


def render_caption_revision(
    job_dir: Path,
    caption_revision: int,
    *,
    renderer=ffmpeg_renderer,
    failpoint=None,
) -> dict[str, Any]:
    return publish_render(
        job_dir,
        caption_revision=caption_revision,
        renderer=renderer,
        failpoint=failpoint,
    )
