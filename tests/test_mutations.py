import errno
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from short_factory.artifacts import initialize_machine_revision, load_current_caption
from short_factory.mutations import (
    BUSY_EXIT_CODE,
    GlobalMutationLock,
    _candidate_composition_plan,
    adopt_candidate_range,
)
from short_factory.composition_schema import validate_edit_plan


def snapshot_tree(root: Path):
    result = {}
    for path in root.rglob("*"):
        if path.is_file() and path.name != ".client-short-factory.lock":
            result[str(path.relative_to(root))] = path.read_bytes()
    return result


class MutationCommandTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.jobs_root = self.root / "jobs"
        self.job_dir = self.jobs_root / "test-job"
        self.job_dir.mkdir(parents=True)
        (self.job_dir / "job.json").write_text(
            json.dumps(
                {
                    "version": 3,
                    "job_id": "test-job",
                    "duration_seconds": 5.0,
                }
            ),
            encoding="utf-8",
        )
        self.first = initialize_machine_revision(
            self.job_dir,
            [{"start": 0.0, "end": 2.0, "text": "字幕です"}],
        )

    def tearDown(self):
        self.temporary.cleanup()

    def command(self, *args, input_text=None):
        return subprocess.run(
            [sys.executable, "-m", "short_factory", *args],
            cwd=Path(__file__).resolve().parent.parent,
            input=input_text,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def payload(self):
        cues = [dict(cue) for cue in self.first["cues"]]
        cues[0]["text"] = "修正済み字幕"
        return json.dumps({"base_revision": 1, "cues": cues}, ensure_ascii=False)

    def test_save_worker_reports_lock_then_publishes_revision(self):
        result = self.command(
            "save-captions",
            "--jobs-root",
            str(self.jobs_root),
            "--job-id",
            "test-job",
            "--stdin-json",
            input_text=self.payload(),
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], "LOCK_ACQUIRED")
        self.assertTrue(json.loads(lines[-1])["ok"])
        self.assertEqual(load_current_caption(self.job_dir)["revision"], 2)

    def test_save_worker_allocates_new_cue_id_after_lock(self):
        cues = [dict(self.first["cues"][0])]
        cues[0]["end"] = 1.2
        cues.append({"id": None, "start": 1.2, "end": 2.0, "text": "追加字幕"})
        payload = json.dumps(
            {"base_revision": 1, "cues": cues}, ensure_ascii=False
        )

        result = self.command(
            "save-captions",
            "--jobs-root",
            str(self.jobs_root),
            "--job-id",
            "test-job",
            "--stdin-json",
            input_text=payload,
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(result.stdout.splitlines()[0], "LOCK_ACQUIRED")
        current = load_current_caption(self.job_dir)
        self.assertEqual(current["revision"], 2)
        self.assertEqual(
            current["cues"][1]["id"], "cue-human-r000000002-0001"
        )

    def test_save_worker_rejects_extra_payload_keys_without_revision_change(self):
        payload = json.loads(self.payload())
        payload["unexpected"] = True

        result = self.command(
            "save-captions",
            "--jobs-root",
            str(self.jobs_root),
            "--job-id",
            "test-job",
            "--stdin-json",
            input_text=json.dumps(payload, ensure_ascii=False),
        )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.splitlines()[0], "LOCK_ACQUIRED")
        completion = json.loads(result.stdout.splitlines()[-1])
        self.assertFalse(completion["ok"])
        self.assertEqual(load_current_caption(self.job_dir)["revision"], 1)

    def test_busy_worker_does_not_change_job_tree(self):
        with GlobalMutationLock(self.jobs_root):
            before = snapshot_tree(self.jobs_root)
            result = self.command(
                "save-captions",
                "--jobs-root",
                str(self.jobs_root),
                "--job-id",
                "test-job",
                "--stdin-json",
                input_text=self.payload(),
            )
            after = snapshot_tree(self.jobs_root)
        self.assertEqual(result.returncode, BUSY_EXIT_CODE)
        self.assertEqual(result.stdout.splitlines()[0], "BUSY")
        self.assertEqual(before, after)

    def test_busy_run_does_not_create_requested_job_directory(self):
        requested = self.jobs_root / "must-not-exist"
        with GlobalMutationLock(self.jobs_root):
            result = self.command(
                "run",
                "--input",
                str(self.root / "missing.mp4"),
                "--start",
                "0",
                "--end",
                "5",
                "--job-id",
                requested.name,
                "--jobs-root",
                str(self.jobs_root),
            )
        self.assertEqual(result.returncode, BUSY_EXIT_CODE)
        self.assertFalse(requested.exists())

    def test_candidate_adoption_binds_server_source_range_and_immutable_render(self):
        source = self.root / "candidate-source.webm"
        source.write_bytes(b"source")
        captured = {}

        class FakePipeline:
            def __init__(_self, options):
                captured["options"] = options
                _self.job_dir = self.jobs_root / options.job_id

            def run_until_subtitles(_self):
                return {"revision": 1}

        with patch(
            "short_factory.mutations.candidate_source",
            return_value=(
                {
                    "sha256": "a" * 64,
                    "size_bytes": source.stat().st_size,
                    "duration_seconds": 120.0,
                    "content_type": "video/webm",
                },
                source,
            ),
        ), patch("short_factory.mutations.candidate_preview"), patch(
            "short_factory.mutations.sha256_file", return_value="a" * 64
        ), patch("short_factory.mutations.Pipeline", FakePipeline), patch(
            "short_factory.mutations.list_renders", return_value=[]
        ), patch(
            "short_factory.mutations.render_job",
            return_value={"render_id": "render-explicit"},
        ) as render, patch(
            "short_factory.mutations.load_current_caption",
            return_value={"revision": 1},
        ):
            result = adopt_candidate_range(
                jobs_root=self.jobs_root,
                candidate_root=self.jobs_root / ".candidate-runs",
                run_id="candidate-run1",
                candidate_id="candidate-001",
                start=8.5,
                end=52.25,
            )

        options = captured["options"]
        self.assertEqual(options.source, str(source))
        self.assertEqual(options.start, "8.500")
        self.assertEqual(options.end, "52.250")
        self.assertTrue(options.rights_confirmed)
        self.assertIn("candidate-run1", options.authorization_note)
        self.assertEqual(result["job_id"], options.job_id)
        self.assertEqual(result["render_id"], "render-explicit")
        render.assert_called_once_with(
            jobs_root=self.jobs_root,
            job_id=options.job_id,
            caption_revision=1,
        )

    def test_candidate_adoption_builds_editable_composition_plan(self):
        project = {
            "project_id": "clip-candidate",
            "source": {
                "source_id": "source-001",
                "analysis": {
                    "format": {"start_time_num": 0, "start_time_den": 1},
                    "video": {
                        "time_base_num": 1,
                        "time_base_den": 1000,
                        "start_pts": 0,
                        "duration_ts": 120000,
                    },
                    "audio": {
                        "time_base_num": 1,
                        "time_base_den": 48000,
                        "start_pts": 0,
                        "sample_rate": 48000,
                        "duration_samples": 120 * 48000,
                    },
                },
            },
            "config": {
                "canvas": {"fps": 30},
                "audio": {"sample_rate": 48000},
            },
        }
        caption = {
            "cues": [
                {"id": "cue-1", "start": 0.5, "end": 2.0, "text": "最初"},
                {"id": "cue-2", "start": 3.0, "end": 4.2, "text": "次"},
            ]
        }
        plan = _candidate_composition_plan(project, caption, start=10, end=40)
        normalized = validate_edit_plan(plan, project=project)
        clip = normalized["timeline_items"][0]
        self.assertEqual((clip["video_in_pts"], clip["video_out_pts"]), (10000, 40000))
        self.assertEqual((clip["audio_in_sample"], clip["audio_out_sample"]), (480000, 1920000))
        self.assertEqual(len(normalized["speech_captions"]), 2)
        self.assertEqual(normalized["speech_captions"][0]["source_in_pts"], 10500)

    def test_owner_process_exit_releases_os_lock(self):
        code = (
            "import os,sys; from pathlib import Path; "
            "from short_factory.mutations import GlobalMutationLock; "
            "lock=GlobalMutationLock(Path(sys.argv[1])); lock.__enter__(); "
            "print('LOCKED', flush=True); os._exit(91)"
        )
        process = subprocess.Popen(
            [sys.executable, "-c", code, str(self.jobs_root)],
            cwd=Path(__file__).resolve().parent.parent,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(process.stdout.readline().strip(), "LOCKED")
        remaining_stdout, stderr = process.communicate(timeout=5)
        self.assertEqual(remaining_stdout, "")
        self.assertEqual(stderr, "")
        self.assertEqual(process.returncode, 91)
        with GlobalMutationLock(self.jobs_root):
            self.assertTrue(True)

    @unittest.skipUnless(os.name == "nt", "Windows lock error classification")
    def test_noncontention_lock_error_is_not_reported_as_busy(self):
        with patch("msvcrt.locking", side_effect=OSError(errno.EIO, "forced I/O")):
            with self.assertRaises(OSError) as raised:
                GlobalMutationLock(self.jobs_root).__enter__()
        self.assertEqual(raised.exception.errno, errno.EIO)

    def test_hardlinked_lock_file_cannot_modify_external_file(self):
        outside = self.root / "outside-lock-target"
        outside.write_bytes(b"")
        lock_path = self.jobs_root / ".client-short-factory.lock"
        try:
            os.link(outside, lock_path)
        except OSError as exc:
            self.skipTest(f"hard links unavailable: {exc}")
        before = outside.read_bytes()
        with self.assertRaises(OSError):
            GlobalMutationLock(self.jobs_root).__enter__()
        self.assertEqual(outside.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
