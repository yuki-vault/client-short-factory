from __future__ import annotations

import json
import unittest
from pathlib import Path

from short_factory.composition_rendering import _segment_command
from short_factory.composition_schema import compile_edit_plan


ROOT = Path(__file__).resolve().parent.parent


class CompositionSourceClockTests(unittest.TestCase):
    def test_vfr_nonzero_pts_and_audio_lead_use_separate_exact_clocks(self):
        config = json.loads(
            (ROOT / "config" / "templates" / "default.json").read_text(
                encoding="utf-8"
            )
        )
        config["audio"]["sample_rate"] = 48000
        project = {
            "project_id": "clock-project",
            "source": {
                "source_id": "source-001",
                "analysis": {
                    "format": {"start_time_num": 1, "start_time_den": 2},
                    "video": {
                        "stream_index": 0,
                        "time_base_num": 1,
                        "time_base_den": 90000,
                        "start_pts": 135000,
                        "duration_ts": 10800000,
                        "width": 1920,
                        "height": 1080,
                        "avg_frame_rate": "30000/1001",
                        "real_frame_rate": "30/1",
                        "variable_frame_rate": True,
                    },
                    "audio": {
                        "stream_index": 1,
                        "time_base_num": 1,
                        "time_base_den": 48000,
                        "start_pts": 24000,
                        "sample_rate": 48000,
                        "channels": 2,
                        "duration_samples": 5760000,
                    },
                },
            },
            "config": config,
        }
        video_in = 135000
        video_out = video_in + 15 * 90000
        plan = {
            "schema_version": 1,
            "project_id": "clock-project",
            "source_id": "source-001",
            "story_beats": [
                {"id": "beat", "role": "hook", "source_order_lock": True, "timeline_item_ids": ["clip"]}
            ],
            "timeline_items": [
                {
                    "id": "clip",
                    "type": "source_clip",
                    "story_beat_id": "beat",
                    "video_in_pts": video_in,
                    "video_out_pts": video_out,
                    "audio_in_sample": 48000,
                    "audio_out_sample": 768000,
                }
            ],
            "presentation_events": [
                {"id": "event", "timeline_item_id": "clip", "source_in_pts": video_in, "source_out_pts": video_out, "layout": "standard"}
            ],
            "speech_captions": [
                {"id": "caption", "timeline_item_id": "clip", "source_in_pts": video_in + 90000, "source_out_pts": video_in + 180000, "text": "clock", "role": "normal", "token_ids": []}
            ],
            "editorial_overlays": [],
            "join_edges": [],
            "source_regions": {"person": None, "content": None, "comment": None},
        }
        compiled = compile_edit_plan(plan, project=project)
        self.assertEqual(compiled["output"]["total_frames"], 450)
        command = _segment_command(
            ffmpeg=Path("ffmpeg.exe"),
            source_path=Path("source.mp4"),
            project=project,
            compiled=compiled,
            video_segment=compiled["video_segments"][0],
            audio_segment=compiled["audio_segments"][0],
            destination=Path("segment.mkv"),
        )
        seek_values = [
            command[index + 1]
            for index, value in enumerate(command)
            if value == "-ss"
        ]
        self.assertEqual(seek_values, ["1.000000000", "1.000000000"])
        self.assertEqual(compiled["audio_segments"][0]["source_in_sample"], 48000)
        self.assertEqual(compiled["captions"][0]["output_start_frame"], 30)


if __name__ == "__main__":
    unittest.main()
