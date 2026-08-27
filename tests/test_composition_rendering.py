from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

from short_factory.composition_artifacts import (
    create_composition_project,
    load_composition_render,
    publish_edit_revision,
)
from short_factory.composition_rendering import render_composition_revision
from short_factory.settings import resolve_media_tools


ROOT = Path(__file__).resolve().parent.parent


class CompositionRenderingSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            cls.tools = resolve_media_tools()
        except FileNotFoundError as exc:
            raise unittest.SkipTest(str(exc)) from exc

    def test_real_ffmpeg_renders_layout_switch_card_captions_and_montage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mp4"
            generated = subprocess.run(
                [
                    str(self.tools["ffmpeg"]),
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc2=size=320x180:rate=30:duration=14",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:sample_rate=48000:duration=14",
                    "-shortest",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "ultrafast",
                    "-crf",
                    "30",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(generated.returncode, 0, generated.stderr[-2000:])
            config = json.loads(
                (ROOT / "config" / "templates" / "default.json").read_text(
                    encoding="utf-8"
                )
            )
            config["render"]["encoder"] = "libx264"
            config["render"]["x264_preset"] = "ultrafast"
            config["render"]["x264_crf"] = 30
            project = create_composition_project(
                root / "projects",
                "render-project",
                source_path=source,
                rights_confirmed=True,
                authorization_note="generated technical fixture",
                config=config,
                ffmpeg=self.tools["ffmpeg"],
                ffprobe=self.tools["ffprobe"],
            )
            project_dir = root / "projects" / "render-project"
            video = project["source"]["analysis"]["video"]
            audio = project["source"]["analysis"]["audio"]
            time_base = Fraction(video["time_base_num"], video["time_base_den"])
            start_pts = int(video["start_pts"])
            sample_rate = int(audio["sample_rate"])

            def pts(seconds: Fraction | int) -> int:
                value = Fraction(seconds) / time_base
                self.assertEqual(value.denominator, 1)
                return start_pts + value.numerator

            def sample(seconds: Fraction | int) -> int:
                value = Fraction(seconds) * sample_rate
                self.assertEqual(value.denominator, 1)
                return value.numerator

            plan = {
                "schema_version": 1,
                "project_id": "render-project",
                "source_id": "source-001",
                "story_beats": [
                    {"id": "beat-title", "role": "hook", "source_order_lock": True, "timeline_item_ids": ["card-title"]},
                    {"id": "beat-one", "role": "setup", "source_order_lock": True, "timeline_item_ids": ["clip-one"]},
                    {"id": "beat-two", "role": "reaction", "source_order_lock": True, "timeline_item_ids": ["clip-two"]},
                    {"id": "beat-three", "role": "payoff", "source_order_lock": True, "timeline_item_ids": ["clip-three"]},
                ],
                "timeline_items": [
                    {"id": "card-title", "type": "generated_card", "story_beat_id": "beat-title", "duration_frames": 30, "text": "3つの見せ場"},
                    {"id": "clip-one", "type": "source_clip", "story_beat_id": "beat-one", "video_in_pts": pts(0), "video_out_pts": pts(4), "audio_in_sample": sample(0), "audio_out_sample": sample(4)},
                    {"id": "clip-two", "type": "source_clip", "story_beat_id": "beat-two", "video_in_pts": pts(4), "video_out_pts": pts(9), "audio_in_sample": sample(4), "audio_out_sample": sample(9)},
                    {"id": "clip-three", "type": "source_clip", "story_beat_id": "beat-three", "video_in_pts": pts(9), "video_out_pts": pts(14), "audio_in_sample": sample(9), "audio_out_sample": sample(14)},
                ],
                "presentation_events": [
                    {"id": "event-one", "timeline_item_id": "clip-one", "source_in_pts": pts(0), "source_out_pts": pts(4), "layout": "standard"},
                    {"id": "event-two-a", "timeline_item_id": "clip-two", "source_in_pts": pts(4), "source_out_pts": pts(Fraction(13, 2)), "layout": "content"},
                    {"id": "event-two-b", "timeline_item_id": "clip-two", "source_in_pts": pts(Fraction(13, 2)), "source_out_pts": pts(9), "layout": "split"},
                    {"id": "event-three", "timeline_item_id": "clip-three", "source_in_pts": pts(9), "source_out_pts": pts(14), "layout": "person"},
                ],
                "speech_captions": [
                    {"id": "caption-one", "timeline_item_id": "clip-one", "source_in_pts": pts(1), "source_out_pts": pts(3), "text": "最初の場面", "role": "normal", "token_ids": ["word-001"]},
                    {"id": "caption-two", "timeline_item_id": "clip-two", "source_in_pts": pts(5), "source_out_pts": pts(8), "text": "画面を切り替える", "role": "comment", "token_ids": ["word-002"]},
                    {"id": "caption-three", "timeline_item_id": "clip-three", "source_in_pts": pts(10), "source_out_pts": pts(13), "text": "最後のリアクション！", "role": "emphasis", "token_ids": ["word-003"]},
                ],
                "editorial_overlays": [
                    {"id": "overlay-one", "timeline_item_id": "clip-one", "local_in_frame": 0, "local_out_frame": 30, "kind": "context", "text": "1戦目"}
                ],
                "join_edges": [
                    {"id": "join-title-one", "from_item_id": "card-title", "to_item_id": "clip-one", "audio_transition": "hard"},
                    {"id": "join-one-two", "from_item_id": "clip-one", "to_item_id": "clip-two", "audio_transition": "micro_fade"},
                    {"id": "join-two-three", "from_item_id": "clip-two", "to_item_id": "clip-three", "audio_transition": "micro_fade"},
                ],
                "source_regions": {
                    "person": [650000, 350000, 350000, 650000],
                    "content": [0, 0, 1000000, 850000],
                    "comment": [100000, 100000, 800000, 250000],
                },
            }
            edit = publish_edit_revision(project_dir, plan, base_revision=None)
            proxy = render_composition_revision(
                project_dir, edit["revision"], render_profile="proxy"
            )
            render = render_composition_revision(
                project_dir, edit["revision"], render_profile="final"
            )
            loaded = load_composition_render(project_dir, render["render_id"])
            loaded_proxy = load_composition_render(project_dir, proxy["render_id"])
            output = project_dir / "renders" / render["render_id"] / "short.mp4"
            qc = json.loads(
                (output.parent / "qc.json").read_text(encoding="utf-8")
            )
            proxy_dir = project_dir / "renders" / proxy["render_id"]
            proxy_qc = json.loads(
                (proxy_dir / "qc.json").read_text(encoding="utf-8")
            )
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 1000)
            self.assertTrue(qc["passed"])
            self.assertEqual(qc["expected_frames"], 450)
            self.assertEqual(proxy_qc["expected_frames"], 450)
            self.assertEqual(
                loaded_proxy["compiled_timeline_hash"],
                loaded["compiled_timeline_hash"],
            )
            self.assertEqual(
                (proxy_dir / "captions.ass").read_bytes(),
                (output.parent / "captions.ass").read_bytes(),
            )
            self.assertTrue(loaded["is_current_edit"])
            self.assertEqual(loaded["renderer"]["engine"], "ffmpeg-composition")
            self.assertEqual(loaded_proxy["render_profile"], "proxy")
            self.assertEqual(loaded["render_profile"], "final")


if __name__ == "__main__":
    unittest.main()
