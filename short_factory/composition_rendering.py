from __future__ import annotations

import json
import logging
import os
import shutil
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping

from .artifacts import ValidationError
from .composition_artifacts import (
    confined_composition_path,
    publish_composition_render,
)
from .composition_schema import content_hash
from .utils import atomic_write_json, run_command


class _ReopeningFileHandler(logging.FileHandler):
    """Write one record at a time without holding a Windows file lock."""

    def emit(self, record: logging.LogRecord) -> None:
        if self.stream is None:
            self.stream = self._open()
        try:
            super().emit(record)
        finally:
            if self.stream is not None:
                self.stream.close()
                self.stream = None


def _logger_for(project_dir: Path) -> logging.Logger:
    logger = logging.getLogger(
        f"client_short_factory.composition_render.{project_dir.name}"
    )
    logger.setLevel(logging.INFO)
    for handler in logger.handlers:
        handler.close()
    logger.handlers.clear()
    log_dir = confined_composition_path(project_dir, "logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = _ReopeningFileHandler(
        log_dir / "composition-render.log", encoding="utf-8", delay=True
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    return logger


def _tool(project: Mapping[str, Any], name: str) -> Path:
    tools = project.get("tools")
    if not isinstance(tools, Mapping) or not isinstance(tools.get(name), str):
        raise ValidationError(f"composition tool is missing: {name}")
    path = Path(tools[name]).expanduser().resolve()
    if not path.is_file():
        raise ValidationError(f"composition tool no longer exists: {name}")
    return path


def _seconds(value: Fraction) -> str:
    return f"{float(value):.9f}"


def _ass_time(frame: int, fps: int) -> str:
    centiseconds = (frame * 100 * 2 + fps) // (2 * fps)
    hours, remainder = divmod(centiseconds, 360000)
    minutes, remainder = divmod(remainder, 6000)
    seconds, cents = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{cents:02d}"


def _ass_escape(text: str) -> str:
    return text.replace("{", "｛").replace("}", "｝").replace("\n", r"\N")


def _write_composition_ass(
    path: Path,
    *,
    compiled: Mapping[str, Any],
    config: Mapping[str, Any],
) -> None:
    canvas = config["canvas"]
    subtitle = config["subtitle"]
    width = int(canvas["width"])
    height = int(canvas["height"])
    fps = int(canvas["fps"])
    font = str(subtitle.get("font_name", "Yu Gothic UI"))
    base_size = int(subtitle.get("font_size", 62))
    margin_left = int(subtitle.get("margin_left", 80))
    margin_right = int(subtitle.get("margin_right", 210))
    margin_vertical = int(subtitle.get("margin_vertical", 390))
    outline = int(subtitle.get("outline", 7))
    shadow = int(subtitle.get("shadow", 2))
    styles = [
        ("Normal", base_size, "&H00FFFFFF", "&H00111111", 0, 2, margin_vertical),
        ("Comment", max(36, base_size - 6), "&H00FFF2A8", "&H00332111", 0, 8, 150),
        ("Quote", base_size, "&H0066E6FF", "&H00111111", 0, 2, margin_vertical),
        ("Emphasis", base_size + 12, "&H003333FF", "&H00FFFFFF", -1, 5, 260),
        ("Chapter", base_size + 24, "&H00FFFFFF", "&H00111111", -1, 5, 0),
        ("Context", max(34, base_size - 10), "&H00FFFFFF", "&H00111111", 0, 8, 150),
    ]
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "YCbCr Matrix: TV.709",
        "",
        "[V4+ Styles]",
        (
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding"
        ),
    ]
    for name, size, primary, outline_color, bold, alignment, margin_v in styles:
        lines.append(
            f"Style: {name},{font},{size},{primary},&H000000FF,{outline_color},"
            f"&H78000000,{bold},0,0,0,100,100,0,0,1,{outline},{shadow},"
            f"{alignment},{margin_left},{margin_right},{margin_v},1"
        )
    lines.extend(
        [
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        ]
    )
    role_styles = {
        "normal": "Normal",
        "comment": "Comment",
        "quote": "Quote",
        "emphasis": "Emphasis",
    }
    overlay_styles = {
        "chapter_card": "Chapter",
        "comment_card": "Comment",
        "context": "Context",
    }
    for caption in compiled.get("captions", []):
        lines.append(
            "Dialogue: 0,"
            + _ass_time(int(caption["output_start_frame"]), fps)
            + ","
            + _ass_time(int(caption["output_end_frame"]), fps)
            + f",{role_styles[caption['role']]},,0,0,0,,"
            + _ass_escape(str(caption["text"]))
        )
    for overlay in compiled.get("overlays", []):
        lines.append(
            "Dialogue: 1,"
            + _ass_time(int(overlay["output_start_frame"]), fps)
            + ","
            + _ass_time(int(overlay["output_end_frame"]), fps)
            + f",{overlay_styles[overlay['kind']]},,0,0,0,,"
            + _ass_escape(str(overlay["text"]))
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig", newline="\n")


def _region(plan_regions: Mapping[str, Any], name: str) -> tuple[float, float, float, float]:
    raw = plan_regions.get(name)
    if not isinstance(raw, list) or len(raw) != 4:
        raise ValidationError(f"layout source region is missing: {name}")
    return tuple(float(value) / 1_000_000 for value in raw)  # type: ignore[return-value]


def _fill_region_filter(
    input_label: str,
    output_label: str,
    rect: tuple[float, float, float, float],
    *,
    width: int,
    height: int,
) -> str:
    x, y, region_width, region_height = rect
    return (
        f"{input_label}crop=w=iw*{region_width:.6f}:h=ih*{region_height:.6f}:"
        f"x=iw*{x:.6f}:y=ih*{y:.6f},"
        f"scale={width}:{height}:force_original_aspect_ratio=increase:"
        f"force_divisible_by=2,crop={width}:{height}{output_label}"
    )


def _layout_graph(
    *,
    layout: str,
    regions: Mapping[str, Any],
    width: int,
    height: int,
    blur: int,
    brightness: float,
    duration: str,
    fps: int,
) -> str:
    finish = (
        f",trim=duration={duration},fps={fps},setpts=PTS-STARTPTS,"
        "setsar=1,format=yuv420p[v]"
    )
    if layout == "standard":
        return (
            "[0:v:0]split=2[bg][fg];"
            f"[bg]scale={width}:{height}:force_original_aspect_ratio=increase:"
            f"force_divisible_by=2,crop={width}:{height},gblur=sigma={blur},"
            f"eq=brightness={brightness}:saturation=0.85[bgv];"
            f"[fg]scale={width}:{height}:force_original_aspect_ratio=decrease:"
            "force_divisible_by=2[fgv];"
            "[bgv][fgv]overlay=(W-w)/2:(H-h)/2"
            + finish
        )
    if layout in {"person", "content", "comment"}:
        chain = _fill_region_filter(
            "[0:v:0]",
            "[focus]",
            _region(regions, layout),
            width=width,
            height=height,
        )
        return chain + ";[focus]null" + finish
    if layout == "split":
        half = height // 2
        content = _fill_region_filter(
            "[content_src]",
            "[content_view]",
            _region(regions, "content"),
            width=width,
            height=half,
        )
        person = _fill_region_filter(
            "[person_src]",
            "[person_view]",
            _region(regions, "person"),
            width=width,
            height=height - half,
        )
        return (
            "[0:v:0]split=2[content_src][person_src];"
            + content
            + ";"
            + person
            + ";[content_view][person_view]vstack=inputs=2"
            + finish
        )
    raise ValidationError(f"unsupported composition layout: {layout}")


def _audio_graph(duration: float, *, fade_in: bool, fade_out: bool) -> str:
    filters = [
        "[1:a:0]aresample=48000",
        f"atrim=duration={duration:.9f}",
        "asetpts=N/SR/TB",
    ]
    fade_duration = min(0.02, duration / 4)
    if fade_in and fade_duration > 0:
        filters.append(f"afade=t=in:st=0:d={fade_duration:.6f}")
    if fade_out and fade_duration > 0:
        filters.append(
            f"afade=t=out:st={max(0.0, duration - fade_duration):.6f}:"
            f"d={fade_duration:.6f}"
        )
    return ",".join(filters) + "[a]"


def _segment_command(
    *,
    ffmpeg: Path,
    source_path: Path,
    project: Mapping[str, Any],
    compiled: Mapping[str, Any],
    video_segment: Mapping[str, Any],
    audio_segment: Mapping[str, Any],
    destination: Path,
) -> list[str]:
    config = project["config"]
    canvas = config["canvas"]
    width = int(canvas["width"])
    height = int(canvas["height"])
    fps = int(canvas["fps"])
    frames = int(video_segment["output_end_frame"]) - int(
        video_segment["output_start_frame"]
    )
    duration_value = Fraction(frames, fps)
    duration = _seconds(duration_value)
    if video_segment["item_type"] == "generated_card":
        return [
            str(ffmpeg),
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=black:s={width}x{height}:r={fps}:d={duration}",
            "-f",
            "lavfi",
            "-i",
            f"anullsrc=r=48000:cl=stereo:d={duration}",
            "-frames:v",
            str(frames),
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "16",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "pcm_s16le",
            "-ar",
            "48000",
            "-ac",
            "2",
            str(destination),
        ]

    analysis = project["source"]["analysis"]
    video = analysis["video"]
    audio = analysis["audio"]
    format_analysis = analysis.get("format", {})
    time_base = Fraction(int(video["time_base_num"]), int(video["time_base_den"]))
    audio_time_base = Fraction(
        int(audio.get("time_base_num", 1)),
        int(audio.get("time_base_den", audio["sample_rate"])),
    )
    format_start = Fraction(
        int(format_analysis.get("start_time_num", 0)),
        int(format_analysis.get("start_time_den", 1)),
    )
    video_seek = Fraction(int(video_segment["source_in_pts"])) * time_base - format_start
    audio_stream_start = Fraction(int(audio.get("start_pts", 0))) * audio_time_base
    audio_seek = (
        audio_stream_start
        + Fraction(int(audio_segment["source_in_sample"]), int(audio["sample_rate"]))
        - format_start
    )
    if video_seek < 0 or audio_seek < 0:
        raise ValidationError("compiled source seek precedes the media start")
    video_graph = _layout_graph(
        layout=str(video_segment["layout"]),
        regions=compiled["source_regions"],
        width=width,
        height=height,
        blur=int(canvas.get("blur_radius", 28)),
        brightness=float(canvas.get("background_brightness", -0.12)),
        duration=duration,
        fps=fps,
    )
    audio_graph = _audio_graph(
        float(duration_value),
        fade_in=bool(audio_segment["fade_in"]),
        fade_out=bool(audio_segment["fade_out"]),
    )
    return [
        str(ffmpeg),
        "-y",
        "-ss",
        _seconds(video_seek),
        "-i",
        str(source_path),
        "-ss",
        _seconds(audio_seek),
        "-i",
        str(source_path),
        "-filter_complex",
        video_graph + ";" + audio_graph,
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-frames:v",
        str(frames),
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-crf",
        "16",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "pcm_s16le",
        "-ar",
        "48000",
        "-ac",
        "2",
        str(destination),
    ]


def _final_command(
    *,
    ffmpeg: Path,
    segment_paths: list[Path],
    compiled: Mapping[str, Any],
    config: Mapping[str, Any],
    encoder: str,
    render_profile: str,
    destination: Path,
) -> list[str]:
    command = [str(ffmpeg), "-y"]
    for path in segment_paths:
        command.extend(["-i", str(path)])
    concat_inputs = "".join(f"[{index}:v:0][{index}:a:0]" for index in range(len(segment_paths)))
    audio = config["audio"]
    total_samples = int(compiled["output"]["total_samples"])
    filter_graph = (
        concat_inputs
        + f"concat=n={len(segment_paths)}:v=1:a=1[vcat][acat];"
        "[vcat]subtitles=filename='captions.ass'[v];"
        f"[acat]loudnorm=I={audio['target_lufs']}:TP={audio['true_peak']}:"
        f"LRA={audio['lra']},aresample=48000,apad,"
        f"atrim=end_sample={total_samples}[a]"
    )
    command.extend(["-filter_complex", filter_graph, "-map", "[v]", "-map", "[a]"])
    render = dict(config["render"])
    if render_profile == "proxy":
        encoder = "libx264"
        render["x264_preset"] = "ultrafast"
        render["x264_crf"] = min(35, max(28, int(render["x264_crf"])))
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
            "-frames:v",
            str(compiled["output"]["total_frames"]),
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
    project: Mapping[str, Any],
    compiled: Mapping[str, Any],
    video_path: Path,
    logger: logging.Logger,
) -> tuple[dict[str, Any], dict[str, bool]]:
    ffprobe = _tool(project, "ffprobe")
    probe = run_command(
        [
            str(ffprobe),
            "-v",
            "error",
            "-count_frames",
            "-show_entries",
            (
                "format=format_name,start_time,duration,size:"
                "stream=index,codec_type,codec_name,width,height,pix_fmt,"
                "avg_frame_rate,sample_rate,channels,nb_read_frames"
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
    canvas = project["config"]["canvas"]
    fps = int(canvas["fps"])
    expected_frames = int(compiled["output"]["total_frames"])
    expected_duration = expected_frames / fps
    actual_duration = float(metadata.get("format", {}).get("duration", 0))
    try:
        actual_frames = int(video.get("nb_read_frames"))
    except (TypeError, ValueError):
        actual_frames = -1
    checks = {
        "one_video_stream": len(videos) == 1,
        "one_audio_stream": len(audios) == 1,
        "h264": video.get("codec_name") == "h264",
        "resolution": (
            video.get("width") == int(canvas["width"])
            and video.get("height") == int(canvas["height"])
        ),
        "pixel_format": video.get("pix_fmt") == "yuv420p",
        "frame_rate": video.get("avg_frame_rate") == f"{fps}/1",
        "frame_count": actual_frames == expected_frames,
        "aac": audio.get("codec_name") == "aac",
        "audio_48khz": audio.get("sample_rate") == "48000",
        "audio_stereo": audio.get("channels") == 2,
        "duration": abs(actual_duration - expected_duration) <= (1 / fps + 0.05),
        "file_size": video_path.stat().st_size > 1_000,
    }
    decode = run_command(
        [
            str(_tool(project, "ffmpeg")),
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


def ffmpeg_composition_renderer(
    project_dir: Path,
    project: Mapping[str, Any],
    edit: Mapping[str, Any],
    compiled: Mapping[str, Any],
    render_dir: Path,
) -> Mapping[str, Any]:
    if edit.get("compiled_timeline_hash") != content_hash(compiled):
        raise ValidationError("renderer received a mismatched compiled timeline")
    logger = _logger_for(project_dir)
    ffmpeg = _tool(project, "ffmpeg")
    source_path = Path(project["source"]["path"]).expanduser().resolve()
    config = project["config"]
    render_input_path = render_dir / "render-input.json"
    if not render_input_path.is_file():
        raise ValidationError("composition render input snapshot is missing")
    render_input = json.loads(render_input_path.read_text(encoding="utf-8"))
    render_profile = render_input.get("render_profile")
    if render_profile not in {"proxy", "final"}:
        raise ValidationError("composition render profile is invalid")
    _write_composition_ass(render_dir / "captions.ass", compiled=compiled, config=config)

    video_segments = compiled.get("video_segments")
    audio_segments = compiled.get("audio_segments")
    if not isinstance(video_segments, list) or not isinstance(audio_segments, list):
        raise ValidationError("compiled render segments are missing")
    if len(video_segments) != len(audio_segments) or not video_segments:
        raise ValidationError("compiled video/audio segments disagree")
    segment_dir = render_dir / ".segments"
    segment_dir.mkdir()
    segment_paths: list[Path] = []
    try:
        previous_frame = 0
        previous_sample = 0
        for index, (video_segment, audio_segment) in enumerate(
            zip(video_segments, audio_segments), start=1
        ):
            if video_segment.get("id") != audio_segment.get("id"):
                raise ValidationError("compiled segment identity mismatch")
            if (
                video_segment.get("output_start_frame") != previous_frame
                or audio_segment.get("output_start_sample") != previous_sample
            ):
                raise ValidationError("compiled segments are not contiguous")
            previous_frame = int(video_segment["output_end_frame"])
            previous_sample = int(audio_segment["output_end_sample"])
            destination = segment_dir / f"{index:04d}.mkv"
            run_command(
                _segment_command(
                    ffmpeg=ffmpeg,
                    source_path=source_path,
                    project=project,
                    compiled=compiled,
                    video_segment=video_segment,
                    audio_segment=audio_segment,
                    destination=destination,
                ),
                logger,
                cwd=render_dir,
            )
            segment_paths.append(destination)
        if previous_frame != int(compiled["output"]["total_frames"]):
            raise ValidationError("compiled video segments do not reach output end")
        if previous_sample != int(compiled["output"]["total_samples"]):
            raise ValidationError("compiled audio segments do not reach output end")

        requested = (
            "libx264"
            if render_profile == "proxy"
            else str(config["render"].get("encoder", "auto"))
        )
        first_encoder = "h264_nvenc" if requested == "auto" else requested
        if first_encoder not in {"h264_nvenc", "libx264"}:
            raise ValidationError("unsupported composition encoder")
        video_path = render_dir / "short.mp4"
        result = run_command(
            _final_command(
                ffmpeg=ffmpeg,
                segment_paths=segment_paths,
                compiled=compiled,
                config=config,
                encoder=first_encoder,
                render_profile=render_profile,
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
                raise RuntimeError(
                    f"composition render failed with {first_encoder}: {tail}"
                )
            used_encoder = "libx264"
            run_command(
                _final_command(
                    ffmpeg=ffmpeg,
                    segment_paths=segment_paths,
                    compiled=compiled,
                    config=config,
                    encoder=used_encoder,
                    render_profile=render_profile,
                    destination=video_path,
                ),
                logger,
                cwd=render_dir,
            )
    finally:
        shutil.rmtree(segment_dir, ignore_errors=True)

    metadata, checks = _probe_and_validate(
        project=project,
        compiled=compiled,
        video_path=render_dir / "short.mp4",
        logger=logger,
    )
    passed = all(checks.values())
    qc = {
        "schema_version": 1,
        "passed": passed,
        "technical_checks_passed": passed,
        "content_review": "pending",
        "checks": checks,
        "expected_frames": int(compiled["output"]["total_frames"]),
        "expected_samples": int(compiled["output"]["total_samples"]),
        "actual_duration": float(metadata.get("format", {}).get("duration", 0)),
        "compiled_timeline_hash": content_hash(compiled),
        "ffprobe": metadata,
    }
    atomic_write_json(render_dir / "qc.json", qc)
    if not passed:
        failures = [name for name, value in checks.items() if value is not True]
        raise ValidationError("composition quality checks failed: " + ", ".join(failures))
    return {
        "engine": "ffmpeg-composition",
        "encoder": used_encoder,
        "profile": render_profile,
    }


def render_composition_revision(
    project_dir: Path,
    edit_revision: int,
    *,
    render_profile: str = "final",
    renderer=ffmpeg_composition_renderer,
    failpoint=None,
) -> dict[str, Any]:
    return publish_composition_render(
        project_dir,
        edit_revision=edit_revision,
        render_profile=render_profile,
        renderer=renderer,
        failpoint=failpoint,
    )
