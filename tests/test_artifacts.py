import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from short_factory.artifacts import (
    ConflictError,
    LegacyJobError,
    ValidationError,
    caption_layout_limits,
    caption_hash,
    initialize_machine_revision,
    list_caption_revisions,
    list_renders,
    load_caption_revision,
    load_current_caption,
    load_render,
    project_job,
    publish_render,
    save_caption_revision,
)


def create_directory_link(link: Path, target: Path) -> None:
    failure: OSError | None = None
    try:
        os.symlink(target, link, target_is_directory=True)
        return
    except OSError as exc:
        failure = exc
        if os.name != "nt":
            raise
    result = subprocess.run(
        ["cmd", "/d", "/c", "mklink", "/J", str(link), str(target)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        assert failure is not None
        raise failure


class WorkflowJobCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.jobs_root = Path(self.temporary.name) / "jobs"
        self.job_dir = self.jobs_root / "test-job"
        self.job_dir.mkdir(parents=True)
        (self.job_dir / "job.json").write_text(
            json.dumps(
                {
                    "version": 3,
                    "job_id": "test-job",
                    "duration_seconds": 12.0,
                }
            ),
            encoding="utf-8",
        )
        self.machine_cues = [
            {"start": 0.0, "end": 2.0, "text": "最初の字幕"},
            {"start": 2.1, "end": 4.0, "text": "次の字幕"},
        ]

    def tearDown(self):
        self.temporary.cleanup()

    def initialize(self):
        return initialize_machine_revision(self.job_dir, self.machine_cues)

    def edited_cues(self, document, text="修正した字幕"):
        cues = [dict(cue) for cue in document["cues"]]
        cues[0]["text"] = text
        return cues


class CaptionRevisionTests(WorkflowJobCase):
    def test_machine_revision_one_is_idempotent_and_never_overwritten(self):
        first = self.initialize()
        original = (
            self.job_dir / "subtitles" / "revisions" / "000001" / "captions.json"
        ).read_bytes()
        second = initialize_machine_revision(
            self.job_dir,
            [{"start": 0.0, "end": 1.0, "text": "別内容"}],
        )
        self.assertEqual(first, second)
        self.assertEqual(
            original,
            (
                self.job_dir
                / "subtitles"
                / "revisions"
                / "000001"
                / "captions.json"
            ).read_bytes(),
        )

    def test_human_edit_creates_next_revision_and_preserves_prior_bytes(self):
        first = self.initialize()
        revision_one_path = (
            self.job_dir / "subtitles" / "revisions" / "000001" / "captions.json"
        )
        before = revision_one_path.read_bytes()
        second = save_caption_revision(
            self.job_dir,
            base_revision=1,
            cues=self.edited_cues(first),
        )
        self.assertEqual(second["revision"], 2)
        self.assertEqual(before, revision_one_path.read_bytes())
        self.assertEqual(load_current_caption(self.job_dir)["revision"], 2)
        self.assertEqual(list_caption_revisions(self.job_dir), [1, 2])

    def test_stale_base_revision_is_rejected_without_allocating_revision(self):
        first = self.initialize()
        save_caption_revision(
            self.job_dir,
            base_revision=1,
            cues=self.edited_cues(first),
        )
        with self.assertRaises(ConflictError):
            save_caption_revision(
                self.job_dir,
                base_revision=1,
                cues=self.edited_cues(first, "古い編集"),
            )
        self.assertEqual(list_caption_revisions(self.job_dir), [1, 2])

    def test_restart_restores_revision_named_by_current_pointer(self):
        first = self.initialize()
        second = save_caption_revision(
            self.job_dir,
            base_revision=1,
            cues=self.edited_cues(first),
        )
        del first
        self.assertEqual(load_current_caption(self.job_dir), second)

    def test_publish_failure_before_pointer_preserves_old_pointer(self):
        first = self.initialize()
        pointer = self.job_dir / "subtitles" / "current.json"
        before = pointer.read_bytes()

        def failpoint(name):
            if name == "caption_after_revision_publish":
                raise RuntimeError("forced stop")

        with self.assertRaisesRegex(RuntimeError, "forced stop"):
            save_caption_revision(
                self.job_dir,
                base_revision=1,
                cues=self.edited_cues(first),
                failpoint=failpoint,
            )
        self.assertEqual(before, pointer.read_bytes())
        self.assertEqual(load_current_caption(self.job_dir)["revision"], 1)
        self.assertEqual(load_caption_revision(self.job_dir, 2)["revision"], 2)
        recovery = json.loads(
            (self.job_dir / "subtitles" / "recovery.json").read_text(encoding="utf-8")
        )
        self.assertEqual(recovery["latest_published_revision"], 2)

    def test_human_edit_can_change_timing_and_add_server_identified_cue(self):
        first = self.initialize()
        revision_one = (
            self.job_dir / "subtitles" / "revisions" / "000001" / "captions.json"
        )
        before = revision_one.read_bytes()
        changed = [dict(first["cues"][0])]
        changed[0]["end"] = 1.2
        changed.append(
            {"id": None, "start": 1.2, "end": 2.0, "text": "追加字幕"}
        )
        changed.append(dict(first["cues"][1]))

        second = save_caption_revision(
            self.job_dir, base_revision=1, cues=changed
        )

        self.assertEqual(second["revision"], 2)
        self.assertEqual(second["cues"][0]["end"], 1.2)
        self.assertEqual(
            second["cues"][1]["id"], "cue-human-r000000002-0001"
        )
        self.assertEqual(before, revision_one.read_bytes())
        self.assertEqual(load_current_caption(self.job_dir), second)

    def test_added_cue_id_stays_stable_in_later_revision(self):
        first = self.initialize()
        cues = [dict(first["cues"][0])]
        cues[0]["end"] = 1.2
        cues.append({"id": None, "start": 1.2, "end": 2.0, "text": "追加"})
        cues.append(dict(first["cues"][1]))
        second = save_caption_revision(self.job_dir, base_revision=1, cues=cues)
        added_id = second["cues"][1]["id"]

        third_cues = [dict(cue) for cue in second["cues"]]
        third_cues[1]["text"] = "追加を修正"
        third = save_caption_revision(
            self.job_dir, base_revision=2, cues=third_cues
        )

        self.assertEqual(third["revision"], 3)
        self.assertEqual(third["cues"][1]["id"], added_id)

    def test_orphaned_revision_number_is_not_reused_for_new_cue_id(self):
        first = self.initialize()
        cues = [dict(first["cues"][0])]
        cues[0]["end"] = 1.2
        cues.append({"id": None, "start": 1.2, "end": 2.0, "text": "orphan"})
        cues.append(dict(first["cues"][1]))

        def failpoint(name):
            if name == "caption_after_revision_publish":
                raise RuntimeError("forced stop")

        with self.assertRaisesRegex(RuntimeError, "forced stop"):
            save_caption_revision(
                self.job_dir,
                base_revision=1,
                cues=cues,
                failpoint=failpoint,
            )
        orphan = load_caption_revision(self.job_dir, 2)
        self.assertEqual(
            orphan["cues"][1]["id"], "cue-human-r000000002-0001"
        )
        self.assertEqual(load_current_caption(self.job_dir)["revision"], 1)

        replacement = [dict(first["cues"][0])]
        replacement[0]["end"] = 1.2
        replacement.append(
            {"id": None, "start": 1.2, "end": 2.0, "text": "replacement"}
        )
        replacement.append(dict(first["cues"][1]))
        third = save_caption_revision(
            self.job_dir, base_revision=1, cues=replacement
        )
        self.assertEqual(third["revision"], 3)
        self.assertEqual(
            third["cues"][1]["id"], "cue-human-r000000003-0001"
        )

    def test_edit_rejects_unknown_deleted_reordered_and_duplicate_ids(self):
        first = self.initialize()

        unknown = [dict(cue) for cue in first["cues"]]
        unknown[0]["id"] = "caller-created-id"
        with self.assertRaisesRegex(ValidationError, "unknown cue id"):
            save_caption_revision(self.job_dir, base_revision=1, cues=unknown)

        deleted = [dict(first["cues"][0])]
        deleted[0]["text"] = "変更"
        with self.assertRaisesRegex(ValidationError, "must be preserved"):
            save_caption_revision(self.job_dir, base_revision=1, cues=deleted)

        reordered = [dict(first["cues"][1]), dict(first["cues"][0])]
        with self.assertRaisesRegex(ValidationError, "order must be preserved"):
            save_caption_revision(self.job_dir, base_revision=1, cues=reordered)

        duplicated = [dict(first["cues"][0]), dict(first["cues"][0])]
        with self.assertRaisesRegex(ValidationError, "duplicate cue id"):
            save_caption_revision(self.job_dir, base_revision=1, cues=duplicated)
        self.assertEqual(list_caption_revisions(self.job_dir), [1])

    def test_edit_rejects_overlap_nonfinite_timing_and_full_noop(self):
        first = self.initialize()

        overlap = [dict(cue) for cue in first["cues"]]
        overlap[1]["start"] = 1.999
        with self.assertRaisesRegex(ValidationError, "overlaps"):
            save_caption_revision(self.job_dir, base_revision=1, cues=overlap)

        nonfinite = [dict(cue) for cue in first["cues"]]
        nonfinite[0]["start"] = float("nan")
        with self.assertRaisesRegex(ValidationError, "invalid timing"):
            save_caption_revision(self.job_dir, base_revision=1, cues=nonfinite)

        too_short = [dict(cue) for cue in first["cues"]]
        too_short[0]["end"] = 0.649
        with self.assertRaisesRegex(ValidationError, "duration is too short"):
            save_caption_revision(self.job_dir, base_revision=1, cues=too_short)

        rounded_negative = [dict(cue) for cue in first["cues"]]
        rounded_negative[0]["start"] = -0.0001
        with self.assertRaisesRegex(ValidationError, "outside"):
            save_caption_revision(
                self.job_dir, base_revision=1, cues=rounded_negative
            )

        rounded_past_end = [dict(cue) for cue in first["cues"]]
        rounded_past_end[-1]["end"] = 12.0001
        with self.assertRaisesRegex(ValidationError, "outside"):
            save_caption_revision(
                self.job_dir, base_revision=1, cues=rounded_past_end
            )

        with self.assertRaisesRegex(ValidationError, "does not change any cue"):
            save_caption_revision(
                self.job_dir,
                base_revision=1,
                cues=[dict(cue) for cue in first["cues"]],
            )
        self.assertEqual(list_caption_revisions(self.job_dir), [1])

    def test_edit_uses_job_minimum_caption_duration_threshold(self):
        first = self.initialize()
        job_path = self.job_dir / "job.json"
        job = json.loads(job_path.read_text(encoding="utf-8"))
        job["config"] = {"subtitle": {"min_cue_seconds": 1.2}}
        job_path.write_text(json.dumps(job), encoding="utf-8")
        cues = [dict(cue) for cue in first["cues"]]
        cues[0]["end"] = 1.1

        with self.assertRaisesRegex(ValidationError, "duration is too short"):
            save_caption_revision(self.job_dir, base_revision=1, cues=cues)
        self.assertEqual(list_caption_revisions(self.job_dir), [1])

    def test_machine_load_and_edit_enforce_caption_layout_limits(self):
        job_path = self.job_dir / "job.json"
        job = json.loads(job_path.read_text(encoding="utf-8"))
        job["config"] = {
            "subtitle": {
                "min_cue_seconds": 0.7,
                "max_chars_per_line": 4,
                "max_lines": 2,
            }
        }
        job_path.write_text(json.dumps(job), encoding="utf-8")

        with self.assertRaisesRegex(ValidationError, "line that is too long"):
            initialize_machine_revision(
                self.job_dir,
                [{"start": 0.0, "end": 2.0, "text": "12345"}],
            )
        self.assertEqual(list_caption_revisions(self.job_dir), [])

        first = initialize_machine_revision(
            self.job_dir,
            [{"start": 0.0, "end": 2.0, "text": "1234"}],
        )
        too_long = [dict(first["cues"][0])]
        too_long[0]["text"] = "12345"
        with self.assertRaisesRegex(ValidationError, "line that is too long"):
            save_caption_revision(self.job_dir, base_revision=1, cues=too_long)

        too_many_lines = [dict(first["cues"][0])]
        too_many_lines[0]["text"] = "1\n2\n3"
        with self.assertRaisesRegex(ValidationError, "too many lines"):
            save_caption_revision(
                self.job_dir, base_revision=1, cues=too_many_lines
            )

        revision_path = (
            self.job_dir / "subtitles" / "revisions" / "000001" / "captions.json"
        )
        tampered = json.loads(revision_path.read_text(encoding="utf-8"))
        tampered["cues"][0]["text"] = "12345"
        revision_path.write_text(json.dumps(tampered), encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "line that is too long"):
            load_caption_revision(self.job_dir, 1)

    def test_caption_layout_config_is_integer_and_bounded(self):
        for field, value in (
            ("max_chars_per_line", True),
            ("max_chars_per_line", "15"),
            ("max_chars_per_line", 0),
            ("max_chars_per_line", 501),
            ("max_lines", False),
            ("max_lines", "2"),
            ("max_lines", 0),
            ("max_lines", 501),
        ):
            with self.subTest(field=field, value=value):
                subtitle = {"max_chars_per_line": 15, "max_lines": 2}
                subtitle[field] = value
                with self.assertRaises(ValidationError):
                    caption_layout_limits({"config": {"subtitle": subtitle}})
        for job in (
            {"config": None},
            {"config": "invalid"},
            {"config": {"subtitle": None}},
            {"config": {"subtitle": "invalid"}},
        ):
            with self.subTest(job=job):
                with self.assertRaises(ValidationError):
                    caption_layout_limits(job)

    def test_project_job_exposes_only_caption_constraint_scalars(self):
        job_path = self.job_dir / "job.json"
        job = json.loads(job_path.read_text(encoding="utf-8"))
        job["config"] = {
            "subtitle": {
                "min_cue_seconds": 0.8,
                "max_chars_per_line": 12,
                "max_lines": 1,
                "font_name": "must-not-be-projected",
            },
            "secret": "must-not-be-projected",
        }
        job_path.write_text(json.dumps(job), encoding="utf-8")
        self.initialize()

        state = project_job(self.job_dir)

        self.assertAlmostEqual(state["caption_minimum_seconds"], 0.75)
        self.assertEqual(state["caption_max_chars_per_line"], 12)
        self.assertEqual(state["caption_max_lines"], 1)
        self.assertNotIn("config", state)
        self.assertNotIn("secret", state)

    def test_legacy_job_is_read_only(self):
        job = json.loads((self.job_dir / "job.json").read_text(encoding="utf-8"))
        job["version"] = 2
        (self.job_dir / "job.json").write_text(json.dumps(job), encoding="utf-8")
        with self.assertRaises(LegacyJobError):
            initialize_machine_revision(self.job_dir, self.machine_cues)


class RenderRevisionTests(WorkflowJobCase):
    @staticmethod
    def fake_renderer(captured):
        def render(job_dir, caption, render_dir):
            captured.append(caption)
            (render_dir / "short.mp4").write_bytes(
                (caption["cues"][0]["text"] + "-video").encode("utf-8")
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
            return {"engine": "fake"}

        return render

    def test_render_uses_explicit_revision_snapshot_and_records_hash(self):
        first = self.initialize()
        save_caption_revision(
            self.job_dir,
            base_revision=1,
            cues=self.edited_cues(first),
        )
        captured = []
        metadata = publish_render(
            self.job_dir,
            caption_revision=1,
            renderer=self.fake_renderer(captured),
        )
        self.assertEqual(captured[0]["revision"], 1)
        self.assertEqual(captured[0]["cues"][0]["text"], "最初の字幕")
        self.assertEqual(metadata["caption_hash"], caption_hash(first))
        video = self.job_dir / "renders" / metadata["render_id"] / "short.mp4"
        self.assertEqual(metadata["output_hash"], hashlib.sha256(video.read_bytes()).hexdigest())

    def test_render_snapshot_contains_added_cue_and_edited_timing(self):
        first = self.initialize()
        cues = [dict(first["cues"][0])]
        cues[0]["end"] = 1.2
        cues.append({"id": None, "start": 1.2, "end": 2.0, "text": "追加字幕"})
        cues.append(dict(first["cues"][1]))
        second = save_caption_revision(self.job_dir, base_revision=1, cues=cues)
        captured = []

        metadata = publish_render(
            self.job_dir,
            caption_revision=2,
            renderer=self.fake_renderer(captured),
        )

        self.assertEqual(captured[0], second)
        self.assertEqual(captured[0]["cues"][0]["end"], 1.2)
        self.assertEqual(captured[0]["cues"][1]["text"], "追加字幕")
        self.assertEqual(metadata["caption_hash"], caption_hash(second))

    def test_render_fault_never_publishes_partial_directory(self):
        self.initialize()
        captured = []

        def failpoint(name):
            if name == "render_after_qc_before_publish":
                raise RuntimeError("forced stop")

        with self.assertRaisesRegex(RuntimeError, "forced stop"):
            publish_render(
                self.job_dir,
                caption_revision=1,
                renderer=self.fake_renderer(captured),
                failpoint=failpoint,
            )
        self.assertEqual(list_renders(self.job_dir), [])

    def test_render_directories_are_immutable(self):
        self.initialize()
        captured = []
        first = publish_render(
            self.job_dir,
            caption_revision=1,
            renderer=self.fake_renderer(captured),
        )
        first_path = self.job_dir / "renders" / first["render_id"] / "short.mp4"
        before = first_path.read_bytes()
        second = publish_render(
            self.job_dir,
            caption_revision=1,
            renderer=self.fake_renderer(captured),
        )
        self.assertNotEqual(first["render_id"], second["render_id"])
        self.assertEqual(before, first_path.read_bytes())

    def test_render_load_rejects_tampered_video_identity(self):
        self.initialize()
        captured = []
        metadata = publish_render(
            self.job_dir,
            caption_revision=1,
            renderer=self.fake_renderer(captured),
        )
        video = self.job_dir / "renders" / metadata["render_id"] / "short.mp4"
        video.write_bytes(b"tampered")
        with self.assertRaisesRegex(ConflictError, "output hash mismatch"):
            load_render(self.job_dir, metadata["render_id"])

    def test_render_load_rejects_contradictory_qc(self):
        self.initialize()
        captured = []
        metadata = publish_render(
            self.job_dir,
            caption_revision=1,
            renderer=self.fake_renderer(captured),
        )
        qc_path = self.job_dir / "renders" / metadata["render_id"] / "qc.json"
        qc = json.loads(qc_path.read_text(encoding="utf-8"))
        qc["passed"] = False
        qc["checks"]["fixture"] = False
        qc_path.write_text(json.dumps(qc), encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "internally inconsistent"):
            load_render(self.job_dir, metadata["render_id"])

    def test_nested_artifact_symlink_cannot_escape_job(self):
        outside = Path(self.temporary.name) / "outside-subtitles"
        outside.mkdir()
        subtitles = self.job_dir / "subtitles"
        try:
            create_directory_link(subtitles, outside)
        except OSError as exc:
            self.skipTest(f"directory symlink unavailable: {exc}")
        try:
            with self.assertRaisesRegex(ValidationError, "escapes"):
                self.initialize()
            self.assertEqual(list(outside.iterdir()), [])
        finally:
            os.rmdir(subtitles)

    def test_nested_revision_junction_cannot_escape_job(self):
        self.initialize()
        revision_dir = self.job_dir / "subtitles" / "revisions" / "000001"
        outside = Path(self.temporary.name) / "outside-revision"
        outside.mkdir()
        (outside / "captions.json").write_bytes(
            (revision_dir / "captions.json").read_bytes()
        )
        shutil.rmtree(revision_dir)
        try:
            create_directory_link(revision_dir, outside)
        except OSError as exc:
            self.skipTest(f"directory junction unavailable: {exc}")
        try:
            with self.assertRaisesRegex(ValidationError, "escapes"):
                load_current_caption(self.job_dir)
            self.assertEqual(list_caption_revisions(self.job_dir), [])
        finally:
            os.rmdir(revision_dir)

    def test_nonfinite_job_and_cue_values_are_rejected(self):
        job_path = self.job_dir / "job.json"
        job = json.loads(job_path.read_text(encoding="utf-8"))
        job["duration_seconds"] = float("nan")
        job_path.write_text(json.dumps(job), encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "duration"):
            self.initialize()

        job["duration_seconds"] = 12.0
        job_path.write_text(json.dumps(job), encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "timing"):
            initialize_machine_revision(
                self.job_dir,
                [{"start": float("nan"), "end": 1.0, "text": "bad"}],
            )

    def test_state_projection_separates_technical_and_content(self):
        self.initialize()
        captured = []
        publish_render(
            self.job_dir,
            caption_revision=1,
            renderer=self.fake_renderer(captured),
        )
        state = project_job(self.job_dir)
        self.assertEqual(state["technical_state"], "passed")
        self.assertEqual(state["content_state"], "pending")
        self.assertFalse(state["can_approve"])

    def test_multiple_renders_have_no_automatic_canonical_selection(self):
        self.initialize()
        captured = []
        first = publish_render(
            self.job_dir,
            caption_revision=1,
            renderer=self.fake_renderer(captured),
        )
        second = publish_render(
            self.job_dir,
            caption_revision=1,
            renderer=self.fake_renderer(captured),
        )
        state = project_job(self.job_dir)
        self.assertNotIn("latest_current_render", state)
        self.assertEqual(
            state["current_caption_render_ids"],
            [first["render_id"], second["render_id"]],
        )
        self.assertEqual(state["technical_state"], "pending")


if __name__ == "__main__":
    unittest.main()
