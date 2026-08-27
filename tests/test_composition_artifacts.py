from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from short_factory.artifacts import ConflictError, ValidationError
from short_factory.composition_artifacts import (
    create_composition_project,
    list_composition_renders,
    list_edit_revisions,
    load_composition_render,
    load_composition_project,
    load_current_edit,
    load_edit_revision,
    publish_composition_render,
    publish_edit_revision,
)


ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "composition" / "dialogue.json"


def fake_probe(source: Path, ffprobe: Path) -> dict:
    return {
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
    }


def fake_renderer(project_dir, project, edit, compiled, render_dir):
    (render_dir / "short.mp4").write_bytes(
        f"composition-{edit['revision']}".encode("utf-8")
    )
    (render_dir / "qc.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "passed": True,
                "technical_checks_passed": True,
                "content_review": "pending",
                "checks": {"fixture": True},
            }
        ),
        encoding="utf-8",
    )
    return {"engine": "fixture", "encoder": "none"}


class CompositionArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "projects"
        source = Path(self.temporary.name) / "source.mp4"
        source.write_bytes(b"authorized-source")
        ffmpeg = Path(self.temporary.name) / "ffmpeg.exe"
        ffprobe = Path(self.temporary.name) / "ffprobe.exe"
        ffmpeg.write_bytes(b"tool")
        ffprobe.write_bytes(b"tool")
        config = json.loads(
            (ROOT / "config" / "templates" / "default.json").read_text(
                encoding="utf-8"
            )
        )
        create_composition_project(
            self.root,
            "fixture-project",
            source_path=source,
            rights_confirmed=True,
            authorization_note="unit test fixture",
            config=config,
            ffmpeg=ffmpeg,
            ffprobe=ffprobe,
            probe=fake_probe,
        )
        self.project_dir = self.root / "fixture-project"
        self.source = source
        self.plan = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_project_creation_requires_rights(self):
        with self.assertRaisesRegex(ValidationError, "rights confirmation"):
            create_composition_project(
                self.root,
                "no-rights",
                source_path=self.source,
                rights_confirmed=False,
                authorization_note="not enough",
                config=json.loads(
                    (ROOT / "config" / "templates" / "default.json").read_text(
                        encoding="utf-8"
                    )
                ),
                ffmpeg=Path(self.temporary.name) / "ffmpeg.exe",
                ffprobe=Path(self.temporary.name) / "ffprobe.exe",
                probe=fake_probe,
            )

    def test_project_metadata_is_immutable_by_content_hash(self):
        project_path = self.project_dir / "project.json"
        project = json.loads(project_path.read_text(encoding="utf-8"))
        project["config"]["canvas"]["fps"] = 60
        project_path.write_text(json.dumps(project), encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "identity hash mismatch"):
            load_composition_project(self.project_dir)

    def test_edit_revisions_are_immutable_and_stale_base_is_rejected(self):
        first = publish_edit_revision(
            self.project_dir, self.plan, base_revision=None
        )
        first_bytes = (
            self.project_dir / "edits" / "revisions" / "000001" / "edit.json"
        ).read_bytes()
        changed = copy.deepcopy(self.plan)
        changed["speech_captions"][0]["text"] = "変更した字幕"
        second = publish_edit_revision(
            self.project_dir, changed, base_revision=1
        )
        self.assertEqual(first["revision"], 1)
        self.assertEqual(second["revision"], 2)
        self.assertEqual(load_current_edit(self.project_dir)["revision"], 2)
        self.assertEqual(
            (
                self.project_dir / "edits" / "revisions" / "000001" / "edit.json"
            ).read_bytes(),
            first_bytes,
        )
        with self.assertRaisesRegex(ConflictError, "stale"):
            publish_edit_revision(self.project_dir, self.plan, base_revision=1)

    def test_pointer_fault_preserves_last_known_good_revision(self):
        publish_edit_revision(self.project_dir, self.plan, base_revision=None)
        changed = copy.deepcopy(self.plan)
        changed["speech_captions"][0]["text"] = "未公開ポインター"

        def failpoint(name: str) -> None:
            if name == "edit_after_revision_publish":
                raise RuntimeError("simulated exit")

        with self.assertRaisesRegex(RuntimeError, "simulated"):
            publish_edit_revision(
                self.project_dir,
                changed,
                base_revision=1,
                failpoint=failpoint,
            )
        self.assertEqual(list_edit_revisions(self.project_dir), [1, 2])
        self.assertEqual(load_current_edit(self.project_dir)["revision"], 1)
        self.assertEqual(load_edit_revision(self.project_dir, 2)["plan"]["speech_captions"][0]["text"], "未公開ポインター")

    def test_render_is_bound_to_explicit_revision_and_becomes_stale(self):
        first = publish_edit_revision(
            self.project_dir, self.plan, base_revision=None
        )
        render = publish_composition_render(
            self.project_dir,
            edit_revision=first["revision"],
            renderer=fake_renderer,
        )
        loaded = load_composition_render(self.project_dir, render["render_id"])
        self.assertTrue(loaded["is_current_edit"])
        self.assertEqual(loaded["edit_plan_hash"], first["plan_hash"])

        changed = copy.deepcopy(self.plan)
        changed["speech_captions"][0]["text"] = "現在の編集"
        publish_edit_revision(self.project_dir, changed, base_revision=1)
        loaded = load_composition_render(self.project_dir, render["render_id"])
        self.assertFalse(loaded["is_current_edit"])

    def test_render_fault_never_publishes_partial_directory(self):
        publish_edit_revision(self.project_dir, self.plan, base_revision=None)

        def failpoint(name: str) -> None:
            if name == "composition_render_after_qc_before_publish":
                raise RuntimeError("simulated exit")

        with self.assertRaisesRegex(RuntimeError, "simulated"):
            publish_composition_render(
                self.project_dir,
                edit_revision=1,
                renderer=fake_renderer,
                failpoint=failpoint,
            )
        self.assertEqual(list_composition_renders(self.project_dir), [])
        self.assertEqual(
            [path for path in (self.project_dir / "renders").iterdir()], []
        )

    def test_source_change_blocks_render_before_renderer_runs(self):
        publish_edit_revision(self.project_dir, self.plan, base_revision=None)
        self.source.write_bytes(b"changed-source")
        called = False

        def renderer(*args):
            nonlocal called
            called = True
            return fake_renderer(*args)

        with self.assertRaisesRegex(ConflictError, "identity changed"):
            publish_composition_render(
                self.project_dir,
                edit_revision=1,
                renderer=renderer,
            )
        self.assertFalse(called)


if __name__ == "__main__":
    unittest.main()
