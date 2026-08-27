import tempfile
import unittest
from pathlib import Path

from short_factory.subtitles import (
    Cue,
    build_cues,
    cue_report,
    wrap_japanese,
    write_ass,
    write_srt,
)


SUBTITLE = {
    "font_name": "Yu Gothic UI",
    "font_size": 62,
    "scale_x": 90,
    "primary_color": "&H00FFFFFF",
    "outline_color": "&H00111111",
    "back_color": "&H78000000",
    "outline": 7,
    "shadow": 2,
    "alignment": 2,
    "margin_left": 90,
    "margin_right": 210,
    "margin_vertical": 390,
    "max_chars_per_line": 15,
    "max_lines": 2,
    "min_chars_per_cue": 6,
    "max_cue_seconds": 3.8,
    "min_cue_seconds": 0.7,
    "pause_break_seconds": 0.55,
    "remove_fillers": True,
}


class SubtitleTests(unittest.TestCase):
    def test_line_break_prefers_meaningful_boundary(self):
        wrapped = wrap_japanese("これね、ギアとか全部分解していいから、", 15, 2)
        self.assertNotIn("全\n部", wrapped)
        self.assertTrue(all(len(line) <= 15 for line in wrapped.splitlines()))

        katakana = wrap_japanese("パイプも1スタックでいいんですか?", 15, 2)
        self.assertNotIn("スタッ\nク", katakana)

    def test_builds_bounded_cues_and_removes_fillers(self):
        tokens = [
            (0.0, 0.2, "えー"),
            (0.2, 0.5, "この"),
            (0.5, 0.8, "素材は"),
            (0.8, 1.1, "分解して"),
            (1.1, 1.5, "大丈夫です。"),
            (2.2, 2.5, "弾薬は"),
            (2.5, 2.9, "ここに"),
            (2.9, 3.3, "残してください。"),
        ]
        words = [
            {"start": start, "end": end, "word": word}
            for start, end, word in tokens
        ]
        cues = build_cues(words, SUBTITLE)
        self.assertGreaterEqual(len(cues), 2)
        self.assertNotIn("えー", "".join(cue.text for cue in cues))
        report = cue_report(cues, SUBTITLE, 5.0)
        self.assertEqual(report["issues"], [])

    def test_writes_utf8_ass_and_srt(self):
        words = [
            {"start": 0.0, "end": 0.5, "word": "テスト"},
            {"start": 0.5, "end": 1.0, "word": "字幕です。"},
        ]
        cues = build_cues(words, SUBTITLE)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ass = root / "captions.ass"
            srt = root / "captions.srt"
            write_ass(ass, cues, {"width": 1080, "height": 1920}, SUBTITLE)
            write_srt(srt, cues)
            self.assertIn("PlayResX: 1080", ass.read_text(encoding="utf-8-sig"))
            self.assertIn("字幕", srt.read_text(encoding="utf-8"))

    def test_merges_unreadably_short_adjacent_cues(self):
        words = [
            {"start": 0.0, "end": 0.48, "word": "ほぐちゃん"},
            {"start": 0.52, "end": 0.66, "word": "これ?"},
            {"start": 1.4, "end": 2.2, "word": "分解していいよ。"},
        ]
        short_boundary = dict(SUBTITLE)
        short_boundary["min_chars_per_cue"] = 1
        short_boundary["pause_break_seconds"] = 0.01
        cues = build_cues(words, short_boundary)
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[0].text.replace("\n", ""), "ほぐちゃんこれ?")
        report = cue_report(cues, short_boundary, 3.0)
        self.assertFalse(
            any("duration below" in issue for issue in report["issues"]),
            report["issues"],
        )

    def test_reports_unmergeable_short_cue(self):
        report = cue_report([Cue(0.0, 0.1, "短い発話")], SUBTITLE, 1.0)
        self.assertTrue(
            any("duration below" in issue for issue in report["issues"])
        )

    def test_wrapping_never_silently_truncates_text(self):
        text = "あ" * 31
        wrapped = wrap_japanese(text, 15, 2)
        self.assertEqual(wrapped.replace("\n", ""), text)


if __name__ == "__main__":
    unittest.main()
