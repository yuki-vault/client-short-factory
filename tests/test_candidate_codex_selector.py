from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from short_factory.candidate_codex_selector import (
    MODEL,
    PROVIDER,
    PROMPT_VERSION,
    select_candidates_with_codex,
)
from short_factory.candidate_selector import CandidateSelectionError, load_selector_config


ROOT = Path(__file__).resolve().parent.parent


class CandidateCodexSelectorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.work = Path(self.temporary.name)
        self.config = load_selector_config(
            ROOT / "config" / "candidates" / "default.json"
        )
        self.authorization = {
            "schema_version": 1,
            "run_id": "candidate-test",
            "source_sha256": "a" * 64,
            "provider": PROVIDER,
            "model": MODEL,
            "payload_scope": "timestamped transcript text only; no source video, audio, or frames",
            "local_session_persistence": "ephemeral",
            "provider_retention": "not_inferred",
            "approved_at": "2026-08-16T00:00:00+00:00",
            "approval_note": "approved",
            "rights_record": "RIGHTS_AND_USAGE.md",
        }
        encoded = json.dumps(
            self.authorization,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        self.authorization["content_sha256"] = hashlib.sha256(encoded).hexdigest()
        self.transcript = {
            "schema_version": 1,
            "source": {"duration_seconds": 120.0},
            "segments": [
                {
                    "start": float(index),
                    "end": float(index + 1),
                    "text": f"発話{index}",
                    "avg_logprob": -0.1,
                    "no_speech_prob": 0.0,
                    "words": [],
                    "speaker": None,
                }
                for index in range(120)
            ],
        }

    def tearDown(self):
        self.temporary.cleanup()

    def test_structured_result_is_snapped_validated_and_cached(self):
        calls = []

        def executor(prompt, schema, work_dir, timeout):
            calls.append((prompt, schema, timeout))
            return {
                "assessment": {"mode": "straight", "reason": "一話で完結"},
                "candidates": [
                    {
                        "start": 10.0,
                        "end": 50.0,
                        "hook_at": 10.0,
                        "payoff_at": 45.0,
                        "hook": "強い導入",
                        "setup": "状況説明",
                        "payoff": "明確な着地",
                        "summary": "完結した短い話",
                        "reason": "前後を知らなくても成立",
                        "context_dependency": "低い",
                        "risk": "固有名詞を音声確認",
                        "mode": "straight",
                    }
                ],
            }

        first = select_candidates_with_codex(
            self.transcript,
            self.config,
            work_dir=self.work,
            authorization=self.authorization,
            executor=executor,
        )
        second = select_candidates_with_codex(
            self.transcript,
            self.config,
            work_dir=self.work,
            authorization=self.authorization,
            executor=lambda *args: self.fail("cache was not reused"),
        )
        self.assertEqual(first, second)
        self.assertEqual(first["provider"], PROVIDER)
        self.assertEqual(first["model"], MODEL)
        self.assertEqual(first["prompt_version"], PROMPT_VERSION)
        self.assertEqual(len(calls), 1)
        self.assertIn("<UNTRUSTED_TRANSCRIPT>", calls[0][0])

    def test_timestamp_without_transcript_evidence_is_rejected(self):
        def executor(*args):
            return {
                "assessment": {"mode": "straight", "reason": "候補"},
                "candidates": [
                    {
                        "start": 10.2,
                        "end": 50.0,
                        "hook_at": 10.0,
                        "payoff_at": 45.0,
                        "hook": "hook",
                        "setup": "setup",
                        "payoff": "payoff",
                        "summary": "summary",
                        "reason": "reason",
                        "context_dependency": "low",
                        "risk": "low",
                        "mode": "straight",
                    }
                ],
            }

        with self.assertRaisesRegex(CandidateSelectionError, "evidence"):
            select_candidates_with_codex(
                self.transcript,
                self.config,
                work_dir=self.work,
                authorization=self.authorization,
                executor=executor,
            )


if __name__ == "__main__":
    unittest.main()
