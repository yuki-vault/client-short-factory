from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from short_factory.artifacts import ValidationError
from short_factory.composition_schema import (
    compile_edit_plan,
    content_hash,
    validate_edit_plan,
)


ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures" / "composition"


def fixture_project() -> dict:
    config = json.loads(
        (ROOT / "config" / "templates" / "default.json").read_text(encoding="utf-8")
    )
    config["audio"]["sample_rate"] = 48000
    return {
        "schema_version": 1,
        "version": 4,
        "project_id": "fixture-project",
        "source": {
            "source_id": "source-001",
            "analysis": {
                "video": {
                    "stream_index": 0,
                    "time_base_num": 1,
                    "time_base_den": 30,
                    "start_pts": 0,
                    "duration_ts": 3600,
                    "width": 1920,
                    "height": 1080,
                    "avg_frame_rate": "30/1",
                    "real_frame_rate": "30/1",
                    "variable_frame_rate": False,
                },
                "audio": {
                    "stream_index": 1,
                    "time_base_num": 1,
                    "time_base_den": 48000,
                    "sample_rate": 48000,
                    "channels": 2,
                    "duration_samples": 5760000,
                },
            },
        },
        "config": config,
    }


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class CompositionSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.project = fixture_project()

    def test_three_structure_fixtures_compile_to_fifteen_seconds(self):
        expectations = {
            "dialogue.json": (3, 3, 0),
            "event-reaction.json": (3, 2, 1),
            "montage.json": (4, 3, 4),
        }
        for name, (segments, captions, overlays) in expectations.items():
            with self.subTest(name=name):
                compiled = compile_edit_plan(load_fixture(name), project=self.project)
                self.assertEqual(compiled["output"]["total_frames"], 450)
                self.assertEqual(compiled["output"]["total_samples"], 720000)
                self.assertEqual(len(compiled["video_segments"]), segments)
                self.assertEqual(len(compiled["captions"]), captions)
                self.assertEqual(len(compiled["overlays"]), overlays)

    def test_normalized_plan_and_compiled_timeline_are_deterministic(self):
        plan = load_fixture("montage.json")
        plan_hashes = set()
        timeline_hashes = set()
        for _ in range(100):
            normalized = validate_edit_plan(copy.deepcopy(plan), project=self.project)
            compiled = compile_edit_plan(copy.deepcopy(plan), project=self.project)
            plan_hashes.add(content_hash(normalized))
            timeline_hashes.add(content_hash(compiled))
        self.assertEqual(len(plan_hashes), 1)
        self.assertEqual(len(timeline_hashes), 1)

    def test_compiled_video_and_audio_maps_are_contiguous(self):
        compiled = compile_edit_plan(load_fixture("event-reaction.json"), project=self.project)
        video_cursor = 0
        audio_cursor = 0
        for video, audio in zip(
            compiled["video_segments"], compiled["audio_segments"]
        ):
            self.assertEqual(video["output_start_frame"], video_cursor)
            self.assertEqual(audio["output_start_sample"], audio_cursor)
            video_cursor = video["output_end_frame"]
            audio_cursor = audio["output_end_sample"]
        self.assertEqual(video_cursor, compiled["output"]["total_frames"])
        self.assertEqual(audio_cursor, compiled["output"]["total_samples"])

    def test_caption_trim_orphan_is_rejected_instead_of_reanchored(self):
        plan = load_fixture("dialogue.json")
        plan["timeline_items"][0]["video_out_pts"] = 60
        plan["timeline_items"][0]["audio_out_sample"] = 96000
        plan["presentation_events"][0]["source_out_pts"] = 60
        with self.assertRaisesRegex(ValidationError, "ORPHANED"):
            validate_edit_plan(plan, project=self.project)

    def test_presentation_gap_and_missing_region_are_rejected(self):
        plan = load_fixture("event-reaction.json")
        plan["presentation_events"][1]["source_in_pts"] += 1
        with self.assertRaisesRegex(ValidationError, "coverage has a gap"):
            validate_edit_plan(plan, project=self.project)

        plan = load_fixture("event-reaction.json")
        plan["source_regions"]["content"] = None
        with self.assertRaisesRegex(ValidationError, "requires source region content"):
            validate_edit_plan(plan, project=self.project)

    def test_non_adjacent_or_missing_join_is_rejected(self):
        plan = load_fixture("dialogue.json")
        plan["join_edges"][0]["to_item_id"] = "clip-payoff"
        with self.assertRaisesRegex(ValidationError, "missing join edge"):
            validate_edit_plan(plan, project=self.project)

    def test_source_range_requires_integer_clock_and_synced_audio(self):
        plan = load_fixture("dialogue.json")
        plan["timeline_items"][0]["video_in_pts"] = 0.5
        with self.assertRaisesRegex(ValidationError, "must be an integer"):
            validate_edit_plan(plan, project=self.project)

        plan = load_fixture("dialogue.json")
        plan["timeline_items"][0]["audio_out_sample"] = 48000
        with self.assertRaisesRegex(ValidationError, "durations disagree"):
            validate_edit_plan(plan, project=self.project)

    def test_generated_json_schema_is_present_and_parseable(self):
        schema_path = ROOT / "short_factory" / "schemas" / "editplan.v1.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["schema_version"]["const"], 1)
        self.assertFalse(schema["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
