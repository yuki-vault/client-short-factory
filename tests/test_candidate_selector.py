from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from short_factory.candidate_selector import (
    CandidateConfigurationError,
    CandidateSelectionError,
    load_selector_config,
    select_candidates,
    validate_candidate_set,
    validate_loopback_base_url,
)


MODEL = "qwen3.5-9b-uncensored-hauhaucs-aggressive.gguf"


def transcript():
    segments = []
    for index in range(20):
        start = index * 5.0
        segments.append(
            {
                "start": start,
                "end": start + 5.0,
                "text": f"話の区間{index}",
                "avg_logprob": -0.2,
                "no_speech_prob": 0.0,
                "words": [],
                "speaker": None,
            }
        )
    return {
        "source": {"duration_seconds": 100.0},
        "segments": segments,
    }


def config_file(root: Path, **selection_overrides) -> Path:
    selection = {
        "provider": "lmstudio",
        "base_url": "http://127.0.0.1:1234/v1",
        "model": MODEL,
        "timeout_seconds": 10.0,
        "temperature": 0.0,
        "map_window_seconds": 100.0,
        "map_overlap_seconds": 0.0,
        "map_max_candidates": 3,
        "max_candidates": 5,
        "min_duration_seconds": 30.0,
        "max_duration_seconds": 60.0,
    }
    selection.update(selection_overrides)
    path = root / "candidate.json"
    path.write_text(json.dumps({"selection": selection}), encoding="utf-8")
    return path


def openai_response(document):
    return {
        "choices": [
            {
                "message": {"content": json.dumps(document, ensure_ascii=False)},
                "finish_reason": "stop",
            }
        ]
    }


class FakeTransport:
    def __init__(self, mapped, reduced):
        self.mapped = mapped
        self.reduced = reduced
        self.calls = []

    def __call__(self, url, payload, timeout):
        self.calls.append((url, payload, timeout))
        if url.endswith("/models"):
            self.assert_empty_model_request(payload)
            return {"data": [{"id": MODEL}]}
        schema = payload["response_format"]["json_schema"]["name"]
        if schema == "candidate_map":
            return openai_response(self.mapped)
        return openai_response(self.reduced)

    @staticmethod
    def assert_empty_model_request(payload):
        if payload != {}:
            raise AssertionError(payload)


class CandidateSelectorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_remote_and_hostname_urls_are_rejected(self):
        for value in (
            "https://127.0.0.1:1234/v1",
            "http://localhost:1234/v1",
            "http://127.0.0.1:4321/v1",
            "http://192.168.1.10:1234/v1",
            "http://127.0.0.1:1234/v1?forward=1",
            "http://user@127.0.0.1:1234/v1",
        ):
            with self.subTest(value=value), self.assertRaises(
                CandidateConfigurationError
            ):
                validate_loopback_base_url(value)
        self.assertEqual(
            validate_loopback_base_url("http://127.0.0.1:1234"),
            "http://127.0.0.1:1234/v1",
        )

    def test_config_is_strict_and_zero_temperature(self):
        config = load_selector_config(config_file(self.root))
        self.assertEqual(config.model, MODEL)
        self.assertEqual(config.temperature, 0.0)
        bad = json.loads((self.root / "candidate.json").read_text(encoding="utf-8"))
        bad["selection"]["api_key"] = "must-not-be-supported"
        (self.root / "candidate.json").write_text(json.dumps(bad), encoding="utf-8")
        with self.assertRaises(CandidateSelectionError):
            load_selector_config(self.root / "candidate.json")

    def test_default_config_uses_bounded_fifteen_minute_map_windows(self):
        config = load_selector_config(
            Path(__file__).resolve().parent.parent
            / "config"
            / "candidates"
            / "default.json"
        )
        self.assertEqual(config.map_window_seconds, 900.0)
        self.assertEqual(config.map_overlap_seconds, 30.0)
        duration = 8555.041
        expected_calls = 1 + int((duration - 1) // (900.0 - 30.0))
        self.assertEqual(expected_calls, 10)

    def test_silent_or_too_short_source_completes_with_zero_candidates(self):
        config = load_selector_config(config_file(self.root))

        def transport(*args, **kwargs):
            raise AssertionError("LM Studio must not be called for an empty source")

        silent = {
            "source": {"duration_seconds": 120.0},
            "segments": [],
        }
        result = select_candidates(silent, config, transport=transport)
        self.assertEqual(result["assessment"]["mode"], "reject")
        self.assertEqual(result["candidates"], [])

        short = transcript()
        short["source"]["duration_seconds"] = 20.0
        short["segments"] = [
            {**short["segments"][0], "start": 0.0, "end": 5.0}
        ]
        result = select_candidates(short, config, transport=transport)
        self.assertEqual(result["assessment"]["mode"], "reject")
        self.assertEqual(result["candidates"], [])

    def test_map_reduce_returns_ranked_nonoverlapping_candidates(self):
        mapped = {
            "source_assessment": {"mode": "paced", "reason": "話は閉じる"},
            "candidates": [
                {
                    "start": 0.0,
                    "end": 40.0,
                    "hook_at": 0.0,
                    "payoff_at": 40.0,
                    "hook": "驚く発言",
                    "setup": "背景を説明",
                    "payoff": "明確なオチ",
                    "summary": "マイク事故のオチまでを語る",
                    "reason": "単体で意味が閉じている",
                    "context_dependency": "低い",
                    "risk": "固有名詞を確認",
                    "mode": "paced",
                },
                {
                    "start": 60.0,
                    "end": 95.0,
                    "hook_at": 60.0,
                    "payoff_at": 95.0,
                    "hook": "数字の驚き",
                    "setup": "期間を説明",
                    "payoff": "感謝で着地",
                    "summary": "強い数字から感謝へ着地する",
                    "reason": "数字のhookと着地がある",
                    "context_dependency": "低い",
                    "risk": "数字を確認",
                    "mode": "straight",
                },
            ],
        }
        reduced = {
            "source_assessment": {"mode": "paced", "reason": "候補が二つある"},
            "candidate_ids": ["w0000-p0002", "w0000-p0001"],
        }
        transport = FakeTransport(mapped, reduced)
        result = select_candidates(
            transcript(), load_selector_config(config_file(self.root)), transport=transport
        )
        self.assertEqual([item["start"] for item in result["candidates"]], [60.0, 0.0])
        self.assertEqual([item["rank"] for item in result["candidates"]], [1, 2])
        self.assertEqual(result["provider"], "lmstudio")
        self.assertEqual(result["model"], MODEL)
        self.assertEqual(result["prompt_version"], "candidate-map-reduce-v3")
        map_payload = transport.calls[1][1]
        self.assertEqual(
            map_payload["response_format"]["type"], "json_schema"
        )
        self.assertEqual(map_payload["reasoning_effort"], "none")
        self.assertEqual(map_payload["max_tokens"], 2500)
        self.assertIn(
            "<SEARCH_ZONE_1>", map_payload["messages"][1]["content"]
        )
        self.assertTrue(
            map_payload["response_format"]["json_schema"]["strict"]
        )
        reduce_payload = transport.calls[2][1]
        self.assertIn("evidence_text", reduce_payload["messages"][1]["content"])

    def test_zero_candidates_is_a_valid_reject_result(self):
        mapped = {
            "source_assessment": {"mode": "reject", "reason": "着地がない"},
            "candidates": [],
        }
        reduced = {
            "source_assessment": {"mode": "reject", "reason": "全区間に着地がない"},
            "candidate_ids": [],
        }
        result = select_candidates(
            transcript(),
            load_selector_config(config_file(self.root)),
            transport=FakeTransport(mapped, reduced),
        )
        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["assessment"]["mode"], "reject")

    def test_unavailable_model_fails_before_transcript_completion(self):
        calls = []

        def no_model(url, payload, timeout):
            calls.append(url)
            return {"data": []}

        with self.assertRaisesRegex(CandidateSelectionError, "not available"):
            select_candidates(
                transcript(),
                load_selector_config(config_file(self.root)),
                transport=no_model,
            )
        self.assertEqual(calls, ["http://127.0.0.1:1234/v1/models"])

    def test_extra_llm_field_and_non_boundary_timestamp_fail_closed(self):
        base = {
            "source_assessment": {"mode": "straight", "reason": "閉じる"},
            "candidates": [],
        }
        with self.subTest("extra field"):
            broken = dict(base)
            broken["unexpected"] = True
            with self.assertRaises(CandidateSelectionError):
                select_candidates(
                    transcript(),
                    load_selector_config(config_file(self.root)),
                    transport=FakeTransport(
                        broken,
                        {
                            "source_assessment": {"mode": "reject", "reason": "なし"},
                            "candidate_ids": [],
                        },
                    ),
                )
        with self.subTest("invented timestamp"):
            broken = dict(base)
            broken["candidates"] = [
                {
                    "start": 0.7,
                    "end": 40.0,
                    "hook_at": 0.0,
                    "payoff_at": 40.0,
                    "hook": "h",
                    "setup": "s",
                    "payoff": "p",
                    "summary": "m",
                    "reason": "g",
                    "context_dependency": "c",
                    "risk": "r",
                    "mode": "straight",
                }
            ]
            result = select_candidates(
                transcript(),
                load_selector_config(config_file(self.root)),
                transport=FakeTransport(
                    broken,
                    {
                        "source_assessment": {"mode": "reject", "reason": "なし"},
                        "candidate_ids": [],
                    },
                ),
            )
            self.assertEqual(result["candidates"], [])

    def test_short_map_candidate_expands_only_to_transcript_boundaries(self):
        mapped = {
            "source_assessment": {"mode": "straight", "reason": "話は閉じる"},
            "candidates": [
                {
                    "start": 20.0,
                    "end": 40.0,
                    "hook_at": 20.0,
                    "payoff_at": 40.0,
                    "hook": "h",
                    "setup": "s",
                    "payoff": "p",
                    "summary": "m",
                    "reason": "g",
                    "context_dependency": "c",
                    "risk": "r",
                    "mode": "straight",
                }
            ],
        }
        reduced = {
            "source_assessment": {"mode": "straight", "reason": "候補あり"},
            "candidate_ids": ["w0000-p0001"],
        }
        result = select_candidates(
            transcript(),
            load_selector_config(config_file(self.root)),
            transport=FakeTransport(mapped, reduced),
        )
        candidate = result["candidates"][0]
        self.assertEqual(candidate["end"] - candidate["start"], 30.0)
        self.assertIn(candidate["start"], {10.0, 15.0, 20.0})

    def test_candidate_range_must_encompass_its_late_payoff(self):
        mapped = {
            "source_assessment": {"mode": "straight", "reason": "話は閉じる"},
            "candidates": [
                {
                    "start": 30.0,
                    "end": 70.0,
                    "hook_at": 30.0,
                    "payoff_at": 85.0,
                    "hook": "問題が起きる",
                    "setup": "原因を探す",
                    "payoff": "80秒台で真相が分かる",
                    "summary": "問題の真相が判明する話",
                    "reason": "明確な解決がある",
                    "context_dependency": "低い",
                    "risk": "固有名詞を確認",
                    "mode": "straight",
                }
            ],
        }
        reduced = {
            "source_assessment": {"mode": "reject", "reason": "有効候補なし"},
            "candidate_ids": [],
        }
        result = select_candidates(
            transcript(),
            load_selector_config(config_file(self.root)),
            transport=FakeTransport(mapped, reduced),
        )
        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["assessment"]["mode"], "reject")

    def test_candidate_set_rejects_overlap_and_nonfinite_time(self):
        def candidate(identifier, rank, start, end):
            return {
                "candidate_id": identifier,
                "rank": rank,
                "start": start,
                "end": end,
                "duration": end - start,
                "hook": "h",
                "setup": "u",
                "payoff": "p",
                "summary": "s",
                "reason": "r",
                "context_dependency": "c",
                "risk": "a",
                "mode": "straight",
            }

        document = {
            "schema_version": 1,
            "assessment": {"mode": "straight", "reason": "候補あり"},
            "provider": "lmstudio",
            "model": MODEL,
            "prompt_version": "candidate-map-reduce-v2",
            "candidates": [
                candidate("a", 1, 0.0, 40.0),
                candidate("b", 2, 30.0, 70.0),
            ],
        }
        with self.assertRaisesRegex(CandidateSelectionError, "overlap"):
            validate_candidate_set(document, source_duration=100.0)
        document["candidates"] = [candidate("a", 1, float("nan"), 40.0)]
        with self.assertRaisesRegex(CandidateSelectionError, "finite"):
            validate_candidate_set(document, source_duration=100.0)


if __name__ == "__main__":
    unittest.main()
