from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


FILLERS = {
    "えー",
    "えーと",
    "えっと",
    "あー",
    "あの",
    "あのー",
    "そのー",
    "うーん",
}

BREAK_PUNCTUATION = "。！？!?、,"
FORBIDDEN_LINE_START = "、。，．！？!?)]}）】』」〉》＞…ー"
FORBIDDEN_LINE_END = "([{（【『「〈《＜"
PREFERRED_BREAK_SUFFIXES = (
    "、",
    "。",
    "！",
    "？",
    "から",
    "ので",
    "けど",
    "なら",
    "って",
    "だけ",
    "まで",
    "とか",
    "ても",
    "では",
    "には",
    "は",
    "が",
    "を",
    "に",
    "で",
    "と",
    "も",
)


@dataclass
class Cue:
    start: float
    end: float
    text: str


def _plain_token(value: str) -> str:
    return re.sub(r"[\s、。，．！？!?…]+", "", value)


def apply_replacements(text: str, replacements: dict[str, str]) -> str:
    for source, replacement in sorted(
        replacements.items(), key=lambda item: len(item[0]), reverse=True
    ):
        text = text.replace(source, replacement)
    return text


def wrap_japanese(text: str, max_chars: int, max_lines: int = 2) -> str:
    text = re.sub(r"\s+", "", text).strip()
    if len(text) <= max_chars or max_lines <= 1:
        return text

    lower = max(1, len(text) - max_chars)
    upper = min(max_chars, len(text) - 1)
    ideal = len(text) / 2
    candidates: list[tuple[float, int]] = []
    for index in range(lower, upper + 1):
        left = text[:index]
        right = text[index:]
        penalty = abs(index - ideal)
        if right and right[0] in FORBIDDEN_LINE_START:
            penalty += 20
        if left and left[-1] in FORBIDDEN_LINE_END:
            penalty += 20
        if left and left[-1] in BREAK_PUNCTUATION:
            penalty -= 8
        elif left.endswith(PREFERRED_BREAK_SUFFIXES):
            penalty -= 4
        if left and right:
            if left[-1].isalnum() and right[0].isalnum():
                penalty += 4
            if (
                "ァ" <= left[-1] <= "ヶ"
                and "ァ" <= right[0] <= "ヶ"
            ):
                penalty += 8
            if "一" <= left[-1] <= "龯" and "一" <= right[0] <= "龯":
                penalty += 3
        candidates.append((penalty, index))
    split_at = min(candidates)[1] if candidates else max_chars
    return text[:split_at] + "\n" + text[split_at:]


def _finalize_cue(
    words: list[dict[str, Any]],
    subtitle: dict[str, Any],
    replacements: dict[str, str],
) -> Cue | None:
    if not words:
        return None
    text = "".join(str(word["word"]) for word in words)
    text = apply_replacements(text, replacements)
    wrapped = wrap_japanese(
        text,
        int(subtitle["max_chars_per_line"]),
        int(subtitle.get("max_lines", 2)),
    )
    if not wrapped:
        return None
    return Cue(
        start=max(0.0, float(words[0]["start"])),
        end=max(float(words[-1]["end"]), float(words[0]["start"]) + 0.05),
        text=wrapped,
    )


def build_cues(
    words: list[dict[str, Any]],
    subtitle: dict[str, Any],
    replacements: dict[str, str] | None = None,
) -> list[Cue]:
    replacements = replacements or {}
    max_chars = int(subtitle["max_chars_per_line"]) * int(
        subtitle.get("max_lines", 2)
    )
    min_chars = int(subtitle.get("min_chars_per_cue", 6))
    max_seconds = float(subtitle.get("max_cue_seconds", 3.8))
    pause_break = float(subtitle.get("pause_break_seconds", 0.55))
    remove_fillers = bool(subtitle.get("remove_fillers", False))

    cleaned: list[dict[str, Any]] = []
    removed_filler_tail = False
    for item in words:
        token = str(item.get("word", "")).strip()
        if not token:
            continue
        if remove_fillers and _plain_token(token) in FILLERS:
            removed_filler_tail = True
            continue
        if remove_fillers and removed_filler_tail and _plain_token(token) in {"ー", "〜"}:
            continue
        removed_filler_tail = False
        cleaned.append(
            {
                "start": float(item["start"]),
                "end": float(item["end"]),
                "word": token,
            }
        )

    cues: list[Cue] = []
    current: list[dict[str, Any]] = []
    current_chars = 0
    for word in cleaned:
        token = str(word["word"])
        token_chars = len(re.sub(r"\s+", "", token))
        if current:
            pause = float(word["start"]) - float(current[-1]["end"])
            duration = float(word["end"]) - float(current[0]["start"])
            prior_text = "".join(str(item["word"]) for item in current)
            boundary = (
                current_chars + token_chars > max_chars
                or (pause >= pause_break and current_chars >= min_chars)
                or (duration > max_seconds and current_chars >= min_chars)
                or (
                    prior_text.endswith(tuple(BREAK_PUNCTUATION))
                    and current_chars >= min_chars
                )
            )
            if boundary:
                cue = _finalize_cue(current, subtitle, replacements)
                if cue:
                    cues.append(cue)
                current = []
                current_chars = 0
        current.append(word)
        current_chars += token_chars

    cue = _finalize_cue(current, subtitle, replacements)
    if cue:
        cues.append(cue)

    minimum = float(subtitle.get("min_cue_seconds", 0.7))
    merge_gap = float(subtitle.get("short_cue_merge_gap_seconds", 0.3))

    # Whisper can emit a very short question or interjection between two words.
    # Merge those fragments before extending timings so every retained cue is
    # actually readable and the text remains synchronized to nearby speech.
    index = 0
    while index < len(cues):
        cue = cues[index]
        if cue.end - cue.start >= minimum:
            index += 1
            continue

        merge_with_next = False
        if index + 1 < len(cues):
            next_cue = cues[index + 1]
            combined = cue.text.replace("\n", "") + next_cue.text.replace("\n", "")
            merge_with_next = (
                next_cue.start - cue.end <= merge_gap
                and len(combined) <= max_chars
            )
            if merge_with_next:
                cues[index] = Cue(
                    start=cue.start,
                    end=next_cue.end,
                    text=wrap_japanese(
                        combined,
                        int(subtitle["max_chars_per_line"]),
                        int(subtitle.get("max_lines", 2)),
                    ),
                )
                del cues[index + 1]
                continue

        if index > 0:
            previous = cues[index - 1]
            combined = previous.text.replace("\n", "") + cue.text.replace("\n", "")
            if cue.start - previous.end <= merge_gap and len(combined) <= max_chars:
                cues[index - 1] = Cue(
                    start=previous.start,
                    end=max(previous.end, cue.end),
                    text=wrap_japanese(
                        combined,
                        int(subtitle["max_chars_per_line"]),
                        int(subtitle.get("max_lines", 2)),
                    ),
                )
                del cues[index]
                index = max(0, index - 1)
                continue

        index += 1

    for index, cue in enumerate(cues):
        next_start = cues[index + 1].start if index + 1 < len(cues) else None
        desired_end = max(cue.end, cue.start + minimum)
        if next_start is not None:
            desired_end = min(desired_end, max(cue.start + 0.05, next_start))
        cue.end = desired_end
        if index and cue.start < cues[index - 1].end:
            cue.start = cues[index - 1].end
            cue.end = max(cue.end, cue.start + 0.05)
    return cues


def _srt_time(seconds: float) -> str:
    milliseconds = int(round(max(0.0, seconds) * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _ass_time(seconds: float) -> str:
    centiseconds = int(round(max(0.0, seconds) * 100))
    hours, remainder = divmod(centiseconds, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    secs, centis = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def write_srt(path: Path, cues: list[Cue]) -> None:
    blocks = []
    for index, cue in enumerate(cues, start=1):
        blocks.append(
            f"{index}\n{_srt_time(cue.start)} --> {_srt_time(cue.end)}\n{cue.text}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


def _ass_escape(text: str) -> str:
    return text.replace("{", "\\{").replace("}", "\\}").replace("\n", "\\N")


def write_ass(
    path: Path,
    cues: list[Cue],
    canvas: dict[str, Any],
    subtitle: dict[str, Any],
) -> None:
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {int(canvas['width'])}
PlayResY: {int(canvas['height'])}
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,{subtitle['font_name']},{int(subtitle['font_size'])},{subtitle['primary_color']},&H000000FF,{subtitle['outline_color']},{subtitle['back_color']},-1,0,0,0,{int(subtitle.get('scale_x', 100))},100,0,0,1,{int(subtitle['outline'])},{int(subtitle['shadow'])},{int(subtitle['alignment'])},{int(subtitle['margin_left'])},{int(subtitle['margin_right'])},{int(subtitle['margin_vertical'])},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = [
        f"Dialogue: 0,{_ass_time(cue.start)},{_ass_time(cue.end)},Main,,0,0,0,,{_ass_escape(cue.text)}"
        for cue in cues
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8-sig")


def cue_report(cues: list[Cue], subtitle: dict[str, Any], duration: float) -> dict[str, Any]:
    max_chars = int(subtitle["max_chars_per_line"])
    minimum = float(subtitle.get("min_cue_seconds", 0.7))
    issues: list[str] = []
    for index, cue in enumerate(cues, start=1):
        lines = cue.text.splitlines()
        if len(lines) > int(subtitle.get("max_lines", 2)):
            issues.append(f"cue {index}: too many lines")
        if any(len(line) > max_chars for line in lines):
            issues.append(f"cue {index}: line exceeds {max_chars} characters")
        if cue.start < 0 or cue.end > duration + 0.25 or cue.end <= cue.start:
            issues.append(f"cue {index}: invalid time range")
        if cue.end - cue.start < minimum - 0.05:
            issues.append(
                f"cue {index}: duration below {minimum:.2f} seconds"
            )
        if index > 1 and cue.start < cues[index - 2].end:
            issues.append(f"cue {index}: overlaps previous cue")
    coverage = sum(max(0.0, cue.end - cue.start) for cue in cues)
    return {
        "cue_count": len(cues),
        "caption_coverage_ratio": round(coverage / duration, 4) if duration else 0,
        "issues": issues,
        "cues": [asdict(cue) for cue in cues],
    }
