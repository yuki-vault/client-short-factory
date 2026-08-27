from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from short_factory.candidate_worker import (
    CandidateCancelled,
    CandidateWorkerError,
    _check_cancel,
    _load_worker_config,
    _prepare_work_manifest,
    _render_preview,
    _seal_transcript_chunk,
    _validate_transcript_chunk,
    _worker_fingerprint,
    run_candidate_worker,
)


ROOT = Path(__file__).resolve().parent.parent


class CandidateWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.config_path = ROOT / "config" / "candidates" / "default.json"

    def tearDown(self):
        self.temporary.cleanup()

    def test_default_config_pins_verified_local_pipeline(self):
        config = _load_worker_config(self.config_path)
        self.assertEqual(config["transcription"]["model"], "small")
        self.assertEqual(config["transcription"]["device"], "cpu")
        self.assertEqual(config["transcription"]["compute_type"], "int8")
        self.assertEqual(config["transcription"]["beam_size"], 1)
        self.assertEqual(config["transcription"]["chunk_seconds"], 900.0)
        self.assertEqual(config["transcription"]["overlap_seconds"], 5.0)
        self.assertEqual(config["selection"]["map_window_seconds"], 900.0)
        self.assertEqual(config["selection"]["map_overlap_seconds"], 30.0)
        self.assertEqual(config["preview"]["video_codec"], "libx264")
        self.assertEqual(config["preview"]["audio_codec"], "aac")
        self.assertEqual(config["preview"]["movflags"], "+faststart")

    def test_unverified_transcription_setting_is_rejected(self):
        document = json.loads(self.config_path.read_text(encoding="utf-8"))
        document["transcription"]["device"] = "cuda"
        path = self.root / "bad.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        with self.assertRaisesRegex(CandidateWorkerError, "unverified"):
            _load_worker_config(path)

    def test_work_manifest_resumes_only_identical_fingerprint(self):
        work = self.root / "work"
        first = {"fingerprint_sha256": "a", "source_sha256": "b"}
        _prepare_work_manifest(work, first)
        _prepare_work_manifest(work, first)
        with self.assertRaisesRegex(CandidateWorkerError, "fingerprint mismatch"):
            _prepare_work_manifest(work, {**first, "fingerprint_sha256": "changed"})

    def test_fingerprint_binds_source_and_config(self):
        config = _load_worker_config(self.config_path)
        one = _worker_fingerprint("a" * 64, 100.0, config, self.config_path)
        two = _worker_fingerprint("b" * 64, 100.0, config, self.config_path)
        self.assertNotEqual(one["fingerprint_sha256"], two["fingerprint_sha256"])
        self.assertEqual(
            len(bytes.fromhex(one["fingerprint_sha256"])), hashlib.sha256().digest_size
        )

    def test_cancel_is_checked_between_stages(self):
        with self.assertRaises(CandidateCancelled):
            _check_cancel(lambda run_dir: True, self.root)
        _check_cancel(lambda run_dir: False, self.root)

    def test_cached_transcript_chunk_is_schema_and_hash_validated(self):
        window = {
            "index": 0,
            "owned_start": 0.0,
            "owned_end": 60.0,
            "input_start": 0.0,
            "input_end": 60.0,
        }
        payload = _seal_transcript_chunk(
            {
                "schema_version": 1,
                "fingerprint_sha256": "f" * 64,
                "window": window,
                "detected_language": "ja",
                "language_probability": 0.9,
                "segments": [
                    {
                        "start": 1.0,
                        "end": 2.0,
                        "text": "安全な字幕",
                        "avg_logprob": -0.2,
                        "no_speech_prob": 0.0,
                        "words": [],
                        "speaker": None,
                    }
                ],
            }
        )
        _validate_transcript_chunk(payload, fingerprint="f" * 64, window=window)
        payload["segments"][0]["text"] = "tampered"
        with self.assertRaisesRegex(CandidateWorkerError, "integrity"):
            _validate_transcript_chunk(payload, fingerprint="f" * 64, window=window)

    def test_preview_command_is_libx264_aac_faststart_and_atomic(self):
        source = self.root / "source.mp4"
        source.write_bytes(b"source")
        work = self.root / "work"
        commands = []

        def fake_run(command):
            commands.append(command)
            output = Path(command[-1])
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"preview")

            class Result:
                stdout = ""

            return Result()

        with patch("short_factory.candidate_worker._run", side_effect=fake_run), patch(
            "short_factory.candidate_worker._probe_duration", return_value=40.0
        ):
            output = _render_preview(
                Path("ffmpeg"),
                Path("ffprobe"),
                source,
                work,
                {"candidate_id": "candidate-001", "start": 10.0, "end": 50.0},
                _load_worker_config(self.config_path)["preview"],
            )
        command = commands[0]
        self.assertIn("libx264", command)
        self.assertIn("aac", command)
        self.assertIn("+faststart", command)
        self.assertTrue(output.is_file())
        self.assertFalse((output.parent / ".candidate-001.tmp.mp4").exists())

    def test_worker_publishes_complete_status(self):
        source = self.root / "source.mp4"
        source.write_bytes(b"source")
        run_dir = self.root / "run"
        run_dir.mkdir()
        published = {
            "candidate_set_id": "set-1",
            "candidates": [],
        }
        statuses = []

        def update_status(run_dir, **kwargs):
            statuses.append(kwargs)
            return kwargs

        artifacts = type(
            "Artifacts",
            (),
            {
                "cancel_requested": staticmethod(lambda run_dir: False),
                "candidate_run_dir": staticmethod(lambda root, run_id: run_dir),
                "candidate_run_lock": staticmethod(lambda run_dir: _NoopContext()),
                "candidate_work_dir": staticmethod(lambda run_dir: run_dir / "work"),
                "load_run": staticmethod(
                    lambda root, run_id: {
                        "run_dir": run_dir,
                        "source_path": source,
                        "status": {"state": "queued"},
                        "manifest": {
                            "source": {
                                "sha256": hashlib.sha256(b"source").hexdigest(),
                                "duration_seconds": 100.0,
                            }
                        },
                    }
                ),
                "load_external_ai_authorization": staticmethod(lambda run_dir: None),
                "publish_candidate_set": staticmethod(
                    lambda run_dir, document, preview_sources=None: published
                ),
                "update_status": staticmethod(update_status),
            },
        )
        import sys

        with patch.dict(sys.modules, {"short_factory.candidate_artifacts": artifacts}), patch(
            "short_factory.candidate_worker._resolve_media_tools",
            return_value={"ffmpeg": Path("ffmpeg"), "ffprobe": Path("ffprobe")},
        ), patch("short_factory.candidate_worker._probe_duration", return_value=100.0), patch(
            "short_factory.candidate_worker._ensure_audio",
            return_value=self.root / "audio.wav",
        ), patch(
            "short_factory.candidate_worker._transcribe_resumable",
            return_value={"source": {"duration_seconds": 100.0}, "segments": []},
        ), patch(
            "short_factory.candidate_worker.select_candidates",
            return_value={
                "assessment": {"mode": "reject", "reason": "なし"},
                "provider": "lmstudio",
                "model": "local",
                "prompt_version": "candidate-map-reduce-v2",
                "candidates": [],
            },
        ):
            result = run_candidate_worker(self.root, "run-1", self.config_path)
        self.assertIs(result, published)
        self.assertEqual(statuses[-1]["state"], "complete")
        self.assertEqual(statuses[-1]["stage"], "complete")

    def test_worker_rejects_nonqueued_run_without_status_mutation(self):
        run_dir = self.root / "run"
        run_dir.mkdir()
        updates = []
        artifacts = type(
            "Artifacts",
            (),
            {
                "cancel_requested": staticmethod(lambda run_dir: False),
                "candidate_run_dir": staticmethod(lambda root, run_id: run_dir),
                "candidate_run_lock": staticmethod(lambda run_dir: _NoopContext()),
                "candidate_work_dir": staticmethod(lambda run_dir: run_dir / "work"),
                "load_run": staticmethod(
                    lambda root, run_id: {
                        "run_dir": run_dir,
                        "source_path": run_dir / "source.media",
                        "status": {"state": "complete"},
                        "manifest": {},
                    }
                ),
                "load_external_ai_authorization": staticmethod(lambda run_dir: None),
                "publish_candidate_set": staticmethod(lambda *args, **kwargs: None),
                "update_status": staticmethod(lambda *args, **kwargs: updates.append(kwargs)),
            },
        )
        import sys

        with patch.dict(sys.modules, {"short_factory.candidate_artifacts": artifacts}):
            with self.assertRaisesRegex(CandidateWorkerError, "not queued"):
                run_candidate_worker(self.root, "run-1", self.config_path)
        self.assertEqual(updates, [])


class _NoopContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return None


if __name__ == "__main__":
    unittest.main()
