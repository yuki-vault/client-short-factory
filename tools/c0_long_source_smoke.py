from __future__ import annotations

import json
import subprocess
import tempfile
import time
from fractions import Fraction
from pathlib import Path

from short_factory.composition_artifacts import (
    create_composition_project,
    publish_edit_revision,
)
from short_factory.composition_rendering import render_composition_revision
from short_factory.settings import load_config, resolve_media_tools


def _run(command: list[str]) -> None:
    result = subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-4000:])


def main() -> int:
    tools = resolve_media_tools()
    config, _ = load_config("default", "default")
    config["render"]["encoder"] = "libx264"
    config["render"]["x264_preset"] = "ultrafast"
    config["render"]["x264_crf"] = 35
    timings: dict[str, float] = {}
    with tempfile.TemporaryDirectory(prefix="short-factory-c0-long-") as directory:
        root = Path(directory)
        source = root / "two-hours.mp4"
        started = time.perf_counter()
        _run(
            [
                str(tools["ffmpeg"]),
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=0x234060:size=160x90:rate=2:duration=7200",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=330:sample_rate=16000:duration=7200",
                "-shortest",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-tune",
                "stillimage",
                "-crf",
                "45",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "16k",
                str(source),
            ]
        )
        timings["generate_two_hour_source_seconds"] = time.perf_counter() - started

        started = time.perf_counter()
        project = create_composition_project(
            root / "projects",
            "long-smoke",
            source_path=source,
            rights_confirmed=True,
            authorization_note="generated two-hour technical fixture",
            config=config,
            ffmpeg=tools["ffmpeg"],
            ffprobe=tools["ffprobe"],
        )
        timings["init_and_hash_seconds"] = time.perf_counter() - started
        video = project["source"]["analysis"]["video"]
        audio = project["source"]["analysis"]["audio"]
        time_base = Fraction(video["time_base_num"], video["time_base_den"])
        video_start = int(video["start_pts"])
        audio_rate = int(audio["sample_rate"])

        def pts(seconds: int) -> int:
            value = Fraction(seconds, 1) / time_base
            if value.denominator != 1:
                raise RuntimeError("fixture boundary is not on a source PTS")
            return video_start + value.numerator

        positions = [0, 1200, 2400, 3600, 4800, 6000]
        beats = []
        items = []
        events = []
        edges = []
        for index, position in enumerate(positions, start=1):
            beat_id = f"beat-{index:02d}"
            item_id = f"clip-{index:02d}"
            beats.append(
                {
                    "id": beat_id,
                    "role": "hook" if index == 1 else ("payoff" if index == 6 else "development"),
                    "source_order_lock": True,
                    "timeline_item_ids": [item_id],
                }
            )
            items.append(
                {
                    "id": item_id,
                    "type": "source_clip",
                    "story_beat_id": beat_id,
                    "video_in_pts": pts(position),
                    "video_out_pts": pts(position + 10),
                    "audio_in_sample": position * audio_rate,
                    "audio_out_sample": (position + 10) * audio_rate,
                }
            )
            events.append(
                {
                    "id": f"event-{index:02d}",
                    "timeline_item_id": item_id,
                    "source_in_pts": pts(position),
                    "source_out_pts": pts(position + 10),
                    "layout": "standard",
                }
            )
            if index > 1:
                edges.append(
                    {
                        "id": f"join-{index - 1:02d}-{index:02d}",
                        "from_item_id": f"clip-{index - 1:02d}",
                        "to_item_id": item_id,
                        "audio_transition": "micro_fade",
                    }
                )
        plan = {
            "schema_version": 1,
            "project_id": "long-smoke",
            "source_id": "source-001",
            "story_beats": beats,
            "timeline_items": items,
            "presentation_events": events,
            "speech_captions": [],
            "editorial_overlays": [],
            "join_edges": edges,
            "source_regions": {"person": None, "content": None, "comment": None},
        }
        project_dir = root / "projects" / "long-smoke"
        started = time.perf_counter()
        edit = publish_edit_revision(project_dir, plan, base_revision=None)
        timings["publish_edit_seconds"] = time.perf_counter() - started
        started = time.perf_counter()
        render = render_composition_revision(
            project_dir, edit["revision"], render_profile="proxy"
        )
        timings["render_sixty_second_proxy_seconds"] = time.perf_counter() - started
        output = project_dir / "renders" / render["render_id"] / "short.mp4"
        result = {
            "ok": True,
            "source_duration_seconds": 7200,
            "source_size_bytes": source.stat().st_size,
            "output_size_bytes": output.stat().st_size,
            "compiled_timeline_hash": render["compiled_timeline_hash"],
            "timings": {name: round(value, 3) for name, value in timings.items()},
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
