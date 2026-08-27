import json
import logging
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from short_factory.artifacts import load_current_caption, save_caption_revision
from short_factory.pipeline import Pipeline, RunOptions


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


class PipelineWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "source.mp4"
        self.source.write_bytes(b"fixture")
        self.jobs_root = self.root / "jobs"
        executable = Path(sys.executable)
        self.tools = {
            "yt_dlp": executable,
            "ffmpeg": executable,
            "ffprobe": executable,
        }
        self.pipelines = []

    def tearDown(self):
        for pipeline in self.pipelines:
            for handler in pipeline.logger.handlers:
                handler.close()
            pipeline.logger.handlers.clear()
        logging.shutdown()
        self.temporary.cleanup()

    def pipeline(self, job_id="new-job", **overrides):
        options = {
            "source": str(self.source),
            "start": "0",
            "end": "5",
            "job_id": job_id,
            "jobs_root": self.jobs_root,
        }
        options.update(overrides)
        with patch("short_factory.pipeline.resolve_tools", return_value=self.tools):
            value = Pipeline(RunOptions(**options))
        self.pipelines.append(value)
        return value

    def test_new_job_manifest_uses_workflow_version_three(self):
        pipeline = self.pipeline()
        manifest = json.loads(pipeline.manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], 3)

    def test_legacy_job_is_rejected_before_any_job_file_changes(self):
        job_dir = self.jobs_root / "legacy"
        job_dir.mkdir(parents=True)
        job_json = job_dir / "job.json"
        job_json.write_text(
            json.dumps({"version": 2, "job_id": "legacy"}),
            encoding="utf-8",
        )
        sentinel = job_dir / "sentinel.txt"
        sentinel.write_text("keep", encoding="utf-8")
        before = {path.name: path.read_bytes() for path in job_dir.iterdir()}
        with self.assertRaisesRegex(RuntimeError, "legacy/read-only"):
            self.pipeline("legacy")
        after = {path.name: path.read_bytes() for path in job_dir.iterdir()}
        self.assertEqual(before, after)

    def test_mutable_rerun_is_rejected_before_job_directory_creation(self):
        for stage in ("acquire", "transcribe", "subtitles", "render", "qc"):
            with self.subTest(stage=stage):
                job_id = f"rerun-{stage}"
                with self.assertRaisesRegex(ValueError, "do not support mutable"):
                    self.pipeline(job_id, rerun_from=stage)
                self.assertFalse((self.jobs_root / job_id).exists())

    def test_windows_alias_job_ids_are_rejected(self):
        for job_id in ("job.", "NUL", "CON.txt", "LPT1"):
            with self.subTest(job_id=job_id):
                with self.assertRaisesRegex(ValueError, "Windows-safe"):
                    self.pipeline(job_id)

    def test_preexisting_job_directory_symlink_cannot_escape_jobs_root(self):
        outside = self.root / "escape"
        outside.mkdir()
        self.jobs_root.mkdir()
        link = self.jobs_root / "escape"
        try:
            create_directory_link(link, outside)
        except OSError as exc:
            self.skipTest(f"directory symlink unavailable: {exc}")
        try:
            with self.assertRaisesRegex(ValueError, "escapes jobs root"):
                self.pipeline("escape")
            self.assertEqual(list(outside.iterdir()), [])
        finally:
            os.rmdir(link)

    def test_subtitle_stage_initializes_schema_and_never_overwrites_human_revision(self):
        pipeline = self.pipeline()
        pipeline.raw_transcript_path.parent.mkdir(parents=True, exist_ok=True)
        pipeline.raw_transcript_path.write_text(
            json.dumps(
                {
                    "words": [
                        {"start": 0.0, "end": 0.8, "word": "テスト"},
                        {"start": 0.8, "end": 2.0, "word": "字幕です。"},
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        pipeline._create_subtitles()
        first = load_current_caption(pipeline.job_dir)
        self.assertEqual(first["schema_version"], 1)
        self.assertEqual(first["revision"], 1)
        self.assertEqual(first["cues"][0]["id"], "cue-000001")

        cues = [dict(cue) for cue in first["cues"]]
        cues[0]["text"] = "人間が修正した字幕です。"
        save_caption_revision(pipeline.job_dir, base_revision=1, cues=cues)
        pipeline._create_subtitles()
        current = load_current_caption(pipeline.job_dir)
        compatibility = json.loads(
            pipeline.captions_json_path.read_text(encoding="utf-8")
        )
        self.assertEqual(current["revision"], 2)
        self.assertEqual(compatibility, current)
        self.assertIn("人間が修正", pipeline.ass_path.read_text(encoding="utf-8-sig"))

    def test_candidate_boundary_stops_before_mutable_render_and_qc(self):
        pipeline = self.pipeline("candidate-boundary")
        stages = []

        def record(stage, outputs, action):
            stages.append(stage)

        with patch.object(pipeline, "_stage", side_effect=record), patch(
            "short_factory.pipeline.load_current_caption",
            return_value={"revision": 1, "cues": []},
        ):
            result = pipeline.run_until_subtitles()
        self.assertEqual(stages, ["acquire", "audio", "transcribe", "subtitles"])
        self.assertEqual(result["revision"], 1)


if __name__ == "__main__":
    unittest.main()
