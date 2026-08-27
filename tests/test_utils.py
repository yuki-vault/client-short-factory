import unittest

from short_factory.pipeline import canonicalize_source
from short_factory.utils import format_timecode, parse_timecode


class TimecodeTests(unittest.TestCase):
    def test_parse_supported_formats(self):
        self.assertEqual(parse_timecode("12.5"), 12.5)
        self.assertEqual(parse_timecode("02:03.5"), 123.5)
        self.assertEqual(parse_timecode("01:02:03.250"), 3723.25)

    def test_invalid_timecode(self):
        with self.assertRaises(ValueError):
            parse_timecode("01:90")
        for value in ("nan", "inf", "-inf"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parse_timecode(value)

    def test_format_timecode(self):
        self.assertEqual(format_timecode(3723.25), "01:02:03.250")

    def test_canonicalize_youtube_live_url(self):
        source = canonicalize_source(
            "https://www.youtube.com/live/pJFBzCQq7M8?si=tracking-value"
        )
        self.assertEqual(
            source, "https://www.youtube.com/watch?v=pJFBzCQq7M8"
        )


if __name__ == "__main__":
    unittest.main()
