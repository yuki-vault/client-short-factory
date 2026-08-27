from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from typing import Any, Iterable, Mapping

from .artifacts import ValidationError, validate_safe_id


EDIT_PLAN_SCHEMA_VERSION = 1
COMPILED_TIMELINE_SCHEMA_VERSION = 1
COMPILER_VERSION = "c0-1"

MIN_OUTPUT_SECONDS = 15
MAX_OUTPUT_SECONDS = 60
MAX_STORY_BEATS = 12
MAX_SOURCE_CLIPS = 24
MAX_PRESENTATION_EVENTS = 24
MAX_CAPTIONS = 80

STORY_ROLES = {"hook", "setup", "development", "reaction", "payoff", "aftertaste"}
LAYOUT_PRESETS = {"standard", "person", "content", "split", "comment"}
CAPTION_ROLES = {"normal", "comment", "quote", "emphasis"}
OVERLAY_KINDS = {"chapter_card", "comment_card", "context"}
AUDIO_TRANSITIONS = {"hard", "micro_fade"}


def canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def content_hash(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _object(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{label} must be an object")
    return value


def _list(value: Any, label: str, *, minimum: int = 0, maximum: int) -> list[Any]:
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise ValidationError(
            f"{label} must contain between {minimum} and {maximum} items"
        )
    return value


def _fields(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ValidationError(f"{label} has invalid fields")


def _integer(value: Any, label: str, *, minimum: int | None = None) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError(f"{label} must be an integer")
    if minimum is not None and value < minimum:
        raise ValidationError(f"{label} must be at least {minimum}")
    return value


def _text(value: Any, label: str, *, maximum: int = 500) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or "\x00" in value
        or len(value) > maximum
    ):
        raise ValidationError(f"{label} is invalid")
    return value


def _enum(value: Any, allowed: set[str], label: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ValidationError(f"invalid {label}")
    return value


def _round_fraction(value: Fraction) -> int:
    if value < 0:
        raise ValidationError("negative timeline value")
    return (value.numerator * 2 + value.denominator) // (2 * value.denominator)


def _frame_for_pts(
    pts: int,
    clip_in_pts: int,
    *,
    time_base: Fraction,
    fps: Fraction,
) -> int:
    return _round_fraction(Fraction(pts - clip_in_pts) * time_base * fps)


def _output_sample_for_frame(frame: int, *, fps: Fraction, sample_rate: int) -> int:
    return _round_fraction(Fraction(frame * sample_rate, 1) / fps)


def _source_context(project: Mapping[str, Any]) -> dict[str, Any]:
    source = _object(project.get("source"), "project source")
    analysis = _object(source.get("analysis"), "source analysis")
    video = _object(analysis.get("video"), "source video analysis")
    audio = _object(analysis.get("audio"), "source audio analysis")
    config = _object(project.get("config"), "project config")
    canvas = _object(config.get("canvas"), "canvas config")

    source_id = validate_safe_id(source.get("source_id"), "source id")
    video_start_pts = _integer(video.get("start_pts"), "video start PTS")
    video_duration_ts = _integer(
        video.get("duration_ts"), "video duration TS", minimum=1
    )
    time_base_num = _integer(
        video.get("time_base_num"), "video time base numerator", minimum=1
    )
    time_base_den = _integer(
        video.get("time_base_den"), "video time base denominator", minimum=1
    )
    audio_sample_rate = _integer(
        audio.get("sample_rate"), "source audio sample rate", minimum=1
    )
    audio_duration_samples = _integer(
        audio.get("duration_samples"), "source audio duration samples", minimum=1
    )
    fps = _integer(canvas.get("fps"), "output fps", minimum=1)
    output_sample_rate = _integer(
        _object(config.get("audio"), "audio config").get("sample_rate", 48000),
        "output audio sample rate",
        minimum=1,
    )
    return {
        "source_id": source_id,
        "video_start_pts": video_start_pts,
        "video_end_pts": video_start_pts + video_duration_ts,
        "time_base": Fraction(time_base_num, time_base_den),
        "audio_sample_rate": audio_sample_rate,
        "audio_duration_samples": audio_duration_samples,
        "fps": Fraction(fps, 1),
        "fps_integer": fps,
        "output_sample_rate": output_sample_rate,
    }


def _rect(value: Any, label: str) -> list[int] | None:
    if value is None:
        return None
    if (
        not isinstance(value, list)
        or len(value) != 4
        or any(not isinstance(item, int) or isinstance(item, bool) for item in value)
    ):
        raise ValidationError(f"{label} must be null or four integer millionths")
    x, y, width, height = value
    if (
        x < 0
        or y < 0
        or width <= 0
        or height <= 0
        or x + width > 1_000_000
        or y + height > 1_000_000
    ):
        raise ValidationError(f"{label} is outside the normalized source frame")
    return list(value)


def _claim_id(raw: Any, label: str, claimed: set[str]) -> str:
    value = validate_safe_id(raw, label)
    if value in claimed:
        raise ValidationError(f"duplicate edit object id: {value}")
    claimed.add(value)
    return value


def validate_edit_plan(
    plan: Mapping[str, Any], *, project: Mapping[str, Any]
) -> dict[str, Any]:
    plan = _object(plan, "edit plan")
    _fields(
        plan,
        {
            "schema_version",
            "project_id",
            "source_id",
            "story_beats",
            "timeline_items",
            "presentation_events",
            "speech_captions",
            "editorial_overlays",
            "join_edges",
            "source_regions",
        },
        "edit plan",
    )
    if plan.get("schema_version") != EDIT_PLAN_SCHEMA_VERSION:
        raise ValidationError("unsupported edit plan schema version")
    if plan.get("project_id") != project.get("project_id"):
        raise ValidationError("edit plan project id mismatch")
    source = _source_context(project)
    if plan.get("source_id") != source["source_id"]:
        raise ValidationError("edit plan source id mismatch")

    claimed: set[str] = set()
    raw_items = _list(
        plan.get("timeline_items"),
        "timeline items",
        minimum=1,
        maximum=MAX_SOURCE_CLIPS + MAX_STORY_BEATS,
    )
    items: dict[str, dict[str, Any]] = {}
    item_duration_frames: dict[str, int] = {}
    source_clip_count = 0
    for index, raw_value in enumerate(raw_items, start=1):
        raw = _object(raw_value, f"timeline item {index}")
        item_type = raw.get("type")
        if item_type == "source_clip":
            _fields(
                raw,
                {
                    "id",
                    "type",
                    "story_beat_id",
                    "video_in_pts",
                    "video_out_pts",
                    "audio_in_sample",
                    "audio_out_sample",
                },
                f"timeline item {index}",
            )
        elif item_type == "generated_card":
            _fields(
                raw,
                {"id", "type", "story_beat_id", "duration_frames", "text"},
                f"timeline item {index}",
            )
        else:
            raise ValidationError(f"timeline item {index} has invalid type")
        item_id = _claim_id(raw.get("id"), "timeline item id", claimed)
        beat_id = validate_safe_id(raw.get("story_beat_id"), "story beat id")
        if item_type == "source_clip":
            source_clip_count += 1
            if source_clip_count > MAX_SOURCE_CLIPS:
                raise ValidationError("too many source clips")
            video_in = _integer(raw.get("video_in_pts"), f"{item_id} video in PTS")
            video_out = _integer(raw.get("video_out_pts"), f"{item_id} video out PTS")
            audio_in = _integer(
                raw.get("audio_in_sample"), f"{item_id} audio in sample", minimum=0
            )
            audio_out = _integer(
                raw.get("audio_out_sample"), f"{item_id} audio out sample", minimum=1
            )
            if not (
                source["video_start_pts"] <= video_in < video_out <= source["video_end_pts"]
            ):
                raise ValidationError(f"{item_id} video range is outside the source")
            if not 0 <= audio_in < audio_out <= source["audio_duration_samples"]:
                raise ValidationError(f"{item_id} audio range is outside the source")
            duration_frames = _frame_for_pts(
                video_out,
                video_in,
                time_base=source["time_base"],
                fps=source["fps"],
            )
            if duration_frames < 1:
                raise ValidationError(f"{item_id} is shorter than one output frame")
            video_duration = Fraction(video_out - video_in) * source["time_base"]
            audio_duration = Fraction(
                audio_out - audio_in, source["audio_sample_rate"]
            )
            if abs(video_duration - audio_duration) > Fraction(1, source["fps_integer"]):
                raise ValidationError(f"{item_id} video and audio durations disagree")
            normalized_item = {
                "id": item_id,
                "type": "source_clip",
                "story_beat_id": beat_id,
                "video_in_pts": video_in,
                "video_out_pts": video_out,
                "audio_in_sample": audio_in,
                "audio_out_sample": audio_out,
            }
        else:
            duration_frames = _integer(
                raw.get("duration_frames"), f"{item_id} duration frames", minimum=1
            )
            if duration_frames > source["fps_integer"] * 5:
                raise ValidationError("generated cards may not exceed five seconds")
            normalized_item = {
                "id": item_id,
                "type": "generated_card",
                "story_beat_id": beat_id,
                "duration_frames": duration_frames,
                "text": _text(raw.get("text"), f"{item_id} text", maximum=120),
            }
        items[item_id] = normalized_item
        item_duration_frames[item_id] = duration_frames

    raw_beats = _list(
        plan.get("story_beats"),
        "story beats",
        minimum=1,
        maximum=MAX_STORY_BEATS,
    )
    beats: list[dict[str, Any]] = []
    ordered_item_ids: list[str] = []
    assigned_items: set[str] = set()
    for index, raw_value in enumerate(raw_beats, start=1):
        raw = _object(raw_value, f"story beat {index}")
        _fields(
            raw,
            {"id", "role", "source_order_lock", "timeline_item_ids"},
            f"story beat {index}",
        )
        beat_id = _claim_id(raw.get("id"), "story beat id", claimed)
        role = _enum(raw.get("role"), STORY_ROLES, "story role")
        source_order_lock = raw.get("source_order_lock")
        if not isinstance(source_order_lock, bool):
            raise ValidationError(f"{beat_id} source_order_lock must be boolean")
        item_ids = _list(
            raw.get("timeline_item_ids"),
            f"{beat_id} timeline items",
            minimum=1,
            maximum=MAX_SOURCE_CLIPS + MAX_STORY_BEATS,
        )
        normalized_ids: list[str] = []
        previous_pts: int | None = None
        for raw_item_id in item_ids:
            item_id = validate_safe_id(raw_item_id, "timeline item id")
            if item_id not in items:
                raise ValidationError(f"unknown timeline item: {item_id}")
            if item_id in assigned_items:
                raise ValidationError(f"timeline item is assigned twice: {item_id}")
            item = items[item_id]
            if item["story_beat_id"] != beat_id:
                raise ValidationError(f"{item_id} story beat mismatch")
            if source_order_lock and item["type"] == "source_clip":
                current_pts = int(item["video_in_pts"])
                if previous_pts is not None and current_pts < previous_pts:
                    raise ValidationError(f"{beat_id} reverses locked source order")
                previous_pts = current_pts
            assigned_items.add(item_id)
            ordered_item_ids.append(item_id)
            normalized_ids.append(item_id)
        beats.append(
            {
                "id": beat_id,
                "role": role,
                "source_order_lock": source_order_lock,
                "timeline_item_ids": normalized_ids,
            }
        )
    if assigned_items != set(items):
        raise ValidationError("every timeline item must belong to exactly one story beat")

    raw_regions = _object(plan.get("source_regions"), "source regions")
    _fields(raw_regions, {"person", "content", "comment"}, "source regions")
    regions = {
        name: _rect(raw_regions.get(name), f"source region {name}")
        for name in ("person", "content", "comment")
    }

    raw_events = _list(
        plan.get("presentation_events"),
        "presentation events",
        maximum=MAX_PRESENTATION_EVENTS,
    )
    events_by_item: dict[str, list[dict[str, Any]]] = {
        item_id: [] for item_id in ordered_item_ids
    }
    required_region = {
        "person": ("person",),
        "content": ("content",),
        "split": ("person", "content"),
        "comment": ("comment",),
        "standard": (),
    }
    for index, raw_value in enumerate(raw_events, start=1):
        raw = _object(raw_value, f"presentation event {index}")
        _fields(
            raw,
            {"id", "timeline_item_id", "source_in_pts", "source_out_pts", "layout"},
            f"presentation event {index}",
        )
        event_id = _claim_id(raw.get("id"), "presentation event id", claimed)
        item_id = validate_safe_id(raw.get("timeline_item_id"), "timeline item id")
        item = items.get(item_id)
        if item is None or item["type"] != "source_clip":
            raise ValidationError(f"{event_id} must reference a source clip")
        start_pts = _integer(raw.get("source_in_pts"), f"{event_id} source in PTS")
        end_pts = _integer(raw.get("source_out_pts"), f"{event_id} source out PTS")
        if not item["video_in_pts"] <= start_pts < end_pts <= item["video_out_pts"]:
            raise ValidationError(f"{event_id} is outside its source clip")
        layout = _enum(raw.get("layout"), LAYOUT_PRESETS, "layout preset")
        for region_name in required_region[layout]:
            if regions[region_name] is None:
                raise ValidationError(f"{event_id} requires source region {region_name}")
        events_by_item[item_id].append(
            {
                "id": event_id,
                "timeline_item_id": item_id,
                "source_in_pts": start_pts,
                "source_out_pts": end_pts,
                "layout": layout,
            }
        )

    events: list[dict[str, Any]] = []
    for item_id in ordered_item_ids:
        item = items[item_id]
        item_events = sorted(
            events_by_item[item_id], key=lambda event: event["source_in_pts"]
        )
        if item["type"] == "generated_card":
            if item_events:
                raise ValidationError("generated cards cannot have presentation events")
            continue
        if not item_events:
            raise ValidationError(f"{item_id} requires presentation coverage")
        cursor = item["video_in_pts"]
        for event in item_events:
            if event["source_in_pts"] != cursor:
                raise ValidationError(f"{item_id} presentation coverage has a gap")
            cursor = event["source_out_pts"]
        if cursor != item["video_out_pts"]:
            raise ValidationError(f"{item_id} presentation coverage is incomplete")
        events.extend(item_events)

    item_index = {item_id: index for index, item_id in enumerate(ordered_item_ids)}
    raw_captions = _list(
        plan.get("speech_captions"),
        "speech captions",
        maximum=MAX_CAPTIONS,
    )
    captions: list[dict[str, Any]] = []
    for index, raw_value in enumerate(raw_captions, start=1):
        raw = _object(raw_value, f"speech caption {index}")
        _fields(
            raw,
            {
                "id",
                "timeline_item_id",
                "source_in_pts",
                "source_out_pts",
                "text",
                "role",
                "token_ids",
            },
            f"speech caption {index}",
        )
        caption_id = _claim_id(raw.get("id"), "speech caption id", claimed)
        item_id = validate_safe_id(raw.get("timeline_item_id"), "timeline item id")
        item = items.get(item_id)
        if item is None or item["type"] != "source_clip":
            raise ValidationError(f"{caption_id} must reference a source clip")
        start_pts = _integer(raw.get("source_in_pts"), f"{caption_id} source in PTS")
        end_pts = _integer(raw.get("source_out_pts"), f"{caption_id} source out PTS")
        if not item["video_in_pts"] <= start_pts < end_pts <= item["video_out_pts"]:
            raise ValidationError(f"{caption_id} is ORPHANED by its source clip")
        token_values = _list(
            raw.get("token_ids"), f"{caption_id} token ids", maximum=100
        )
        token_ids: list[str] = []
        token_seen: set[str] = set()
        for token in token_values:
            token_id = validate_safe_id(token, "token id")
            if token_id in token_seen:
                raise ValidationError(f"{caption_id} has duplicate token ids")
            token_seen.add(token_id)
            token_ids.append(token_id)
        captions.append(
            {
                "id": caption_id,
                "timeline_item_id": item_id,
                "source_in_pts": start_pts,
                "source_out_pts": end_pts,
                "text": _text(raw.get("text"), f"{caption_id} text"),
                "role": _enum(raw.get("role"), CAPTION_ROLES, "caption role"),
                "token_ids": token_ids,
            }
        )
    captions.sort(
        key=lambda value: (
            item_index[value["timeline_item_id"]],
            value["source_in_pts"],
            value["id"],
        )
    )
    previous_caption_end: dict[str, int] = {}
    for caption in captions:
        item_id = caption["timeline_item_id"]
        if caption["source_in_pts"] < previous_caption_end.get(item_id, -10**30):
            raise ValidationError(f"{item_id} speech captions overlap")
        previous_caption_end[item_id] = caption["source_out_pts"]

    raw_overlays = _list(
        plan.get("editorial_overlays"),
        "editorial overlays",
        maximum=MAX_CAPTIONS,
    )
    overlays: list[dict[str, Any]] = []
    for index, raw_value in enumerate(raw_overlays, start=1):
        raw = _object(raw_value, f"editorial overlay {index}")
        _fields(
            raw,
            {"id", "timeline_item_id", "local_in_frame", "local_out_frame", "kind", "text"},
            f"editorial overlay {index}",
        )
        overlay_id = _claim_id(raw.get("id"), "editorial overlay id", claimed)
        item_id = validate_safe_id(raw.get("timeline_item_id"), "timeline item id")
        item = items.get(item_id)
        if item is None:
            raise ValidationError(f"unknown timeline item: {item_id}")
        start_frame = _integer(
            raw.get("local_in_frame"), f"{overlay_id} local in frame", minimum=0
        )
        end_frame = _integer(
            raw.get("local_out_frame"), f"{overlay_id} local out frame", minimum=1
        )
        if not 0 <= start_frame < end_frame <= item_duration_frames[item_id]:
            raise ValidationError(f"{overlay_id} is outside its timeline item")
        overlays.append(
            {
                "id": overlay_id,
                "timeline_item_id": item_id,
                "local_in_frame": start_frame,
                "local_out_frame": end_frame,
                "kind": _enum(raw.get("kind"), OVERLAY_KINDS, "overlay kind"),
                "text": _text(raw.get("text"), f"{overlay_id} text"),
            }
        )
    overlays.sort(
        key=lambda value: (
            item_index[value["timeline_item_id"]],
            value["local_in_frame"],
            value["id"],
        )
    )

    raw_edges = _list(
        plan.get("join_edges"),
        "join edges",
        minimum=max(0, len(ordered_item_ids) - 1),
        maximum=max(0, len(ordered_item_ids) - 1),
    )
    edges_by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    for index, raw_value in enumerate(raw_edges, start=1):
        raw = _object(raw_value, f"join edge {index}")
        _fields(
            raw,
            {"id", "from_item_id", "to_item_id", "audio_transition"},
            f"join edge {index}",
        )
        edge_id = _claim_id(raw.get("id"), "join edge id", claimed)
        from_id = validate_safe_id(raw.get("from_item_id"), "timeline item id")
        to_id = validate_safe_id(raw.get("to_item_id"), "timeline item id")
        pair = (from_id, to_id)
        if pair in edges_by_pair:
            raise ValidationError("duplicate join edge")
        edges_by_pair[pair] = {
            "id": edge_id,
            "from_item_id": from_id,
            "to_item_id": to_id,
            "audio_transition": _enum(
                raw.get("audio_transition"), AUDIO_TRANSITIONS, "audio transition"
            ),
        }
    edges: list[dict[str, Any]] = []
    for previous, current in zip(ordered_item_ids, ordered_item_ids[1:]):
        edge = edges_by_pair.pop((previous, current), None)
        if edge is None:
            raise ValidationError(f"missing join edge: {previous} -> {current}")
        edges.append(edge)
    if edges_by_pair:
        raise ValidationError("join edges must connect adjacent timeline items")

    ordered_items = [items[item_id] for item_id in ordered_item_ids]
    total_frames = sum(item_duration_frames[item["id"]] for item in ordered_items)
    minimum_frames = MIN_OUTPUT_SECONDS * source["fps_integer"]
    maximum_frames = MAX_OUTPUT_SECONDS * source["fps_integer"]
    if not minimum_frames <= total_frames <= maximum_frames:
        raise ValidationError("compiled output must be between 15 and 60 seconds")

    return {
        "schema_version": EDIT_PLAN_SCHEMA_VERSION,
        "project_id": project["project_id"],
        "source_id": source["source_id"],
        "story_beats": beats,
        "timeline_items": ordered_items,
        "presentation_events": events,
        "speech_captions": captions,
        "editorial_overlays": overlays,
        "join_edges": edges,
        "source_regions": regions,
    }


def compile_edit_plan(
    plan: Mapping[str, Any], *, project: Mapping[str, Any]
) -> dict[str, Any]:
    normalized = validate_edit_plan(plan, project=project)
    source = _source_context(project)
    item_by_id = {item["id"]: item for item in normalized["timeline_items"]}
    events_by_item: dict[str, list[dict[str, Any]]] = {}
    for event in normalized["presentation_events"]:
        events_by_item.setdefault(event["timeline_item_id"], []).append(event)
    edge_by_from = {edge["from_item_id"]: edge for edge in normalized["join_edges"]}
    edge_by_to = {edge["to_item_id"]: edge for edge in normalized["join_edges"]}

    item_spans: dict[str, tuple[int, int]] = {}
    video_segments: list[dict[str, Any]] = []
    audio_segments: list[dict[str, Any]] = []
    output_cursor = 0
    segment_ordinal = 0
    for item in normalized["timeline_items"]:
        item_start = output_cursor
        if item["type"] == "source_clip":
            item_duration_frames = _frame_for_pts(
                item["video_out_pts"],
                item["video_in_pts"],
                time_base=source["time_base"],
                fps=source["fps"],
            )
        else:
            item_duration_frames = int(item["duration_frames"])
        item_end = item_start + item_duration_frames
        item_spans[item["id"]] = (item_start, item_end)
        if item["type"] == "generated_card":
            raw_segments = [
                {
                    "source_in_pts": None,
                    "source_out_pts": None,
                    "local_in_frame": 0,
                    "local_out_frame": item_duration_frames,
                    "layout": "generated_card",
                }
            ]
        else:
            raw_segments = []
            for event in events_by_item[item["id"]]:
                local_start = _frame_for_pts(
                    event["source_in_pts"],
                    item["video_in_pts"],
                    time_base=source["time_base"],
                    fps=source["fps"],
                )
                local_end = _frame_for_pts(
                    event["source_out_pts"],
                    item["video_in_pts"],
                    time_base=source["time_base"],
                    fps=source["fps"],
                )
                if local_end <= local_start:
                    raise ValidationError(f"{event['id']} compiles to zero frames")
                raw_segments.append(
                    {
                        "source_in_pts": event["source_in_pts"],
                        "source_out_pts": event["source_out_pts"],
                        "local_in_frame": local_start,
                        "local_out_frame": local_end,
                        "layout": event["layout"],
                    }
                )
        for raw_segment in raw_segments:
            segment_ordinal += 1
            local_start = int(raw_segment["local_in_frame"])
            local_end = int(raw_segment["local_out_frame"])
            output_start = item_start + local_start
            output_end = item_start + local_end
            segment_id = f"segment-{segment_ordinal:04d}"
            video_segment = {
                "id": segment_id,
                "timeline_item_id": item["id"],
                "item_type": item["type"],
                "output_start_frame": output_start,
                "output_end_frame": output_end,
                "source_in_pts": raw_segment["source_in_pts"],
                "source_out_pts": raw_segment["source_out_pts"],
                "layout": raw_segment["layout"],
            }
            if item["type"] == "generated_card":
                video_segment["card_text"] = item["text"]
                audio_in = None
                audio_out = None
            else:
                audio_span = item["audio_out_sample"] - item["audio_in_sample"]
                audio_in = item["audio_in_sample"] + _round_fraction(
                    Fraction(audio_span * local_start, item_duration_frames)
                )
                audio_out = item["audio_in_sample"] + _round_fraction(
                    Fraction(audio_span * local_end, item_duration_frames)
                )
            output_audio_start = _output_sample_for_frame(
                output_start,
                fps=source["fps"],
                sample_rate=source["output_sample_rate"],
            )
            output_audio_end = _output_sample_for_frame(
                output_end,
                fps=source["fps"],
                sample_rate=source["output_sample_rate"],
            )
            fade_in = (
                local_start == 0
                and item["id"] in edge_by_to
                and edge_by_to[item["id"]]["audio_transition"] == "micro_fade"
            )
            fade_out = (
                local_end == item_duration_frames
                and item["id"] in edge_by_from
                and edge_by_from[item["id"]]["audio_transition"] == "micro_fade"
            )
            audio_segment = {
                "id": segment_id,
                "timeline_item_id": item["id"],
                "item_type": item["type"],
                "output_start_sample": output_audio_start,
                "output_end_sample": output_audio_end,
                "source_in_sample": audio_in,
                "source_out_sample": audio_out,
                "fade_in": fade_in,
                "fade_out": fade_out,
            }
            video_segments.append(video_segment)
            audio_segments.append(audio_segment)
        output_cursor = item_end

    compiled_captions: list[dict[str, Any]] = []
    for caption in normalized["speech_captions"]:
        item = item_by_id[caption["timeline_item_id"]]
        item_start, _ = item_spans[item["id"]]
        start_frame = item_start + _frame_for_pts(
            caption["source_in_pts"],
            item["video_in_pts"],
            time_base=source["time_base"],
            fps=source["fps"],
        )
        end_frame = item_start + _frame_for_pts(
            caption["source_out_pts"],
            item["video_in_pts"],
            time_base=source["time_base"],
            fps=source["fps"],
        )
        if end_frame <= start_frame:
            raise ValidationError(f"{caption['id']} compiles to zero frames")
        compiled_captions.append(
            {
                "id": caption["id"],
                "timeline_item_id": item["id"],
                "output_start_frame": start_frame,
                "output_end_frame": end_frame,
                "text": caption["text"],
                "role": caption["role"],
                "token_ids": caption["token_ids"],
            }
        )

    compiled_overlays: list[dict[str, Any]] = []
    for overlay in normalized["editorial_overlays"]:
        item_start, _ = item_spans[overlay["timeline_item_id"]]
        compiled_overlays.append(
            {
                "id": overlay["id"],
                "timeline_item_id": overlay["timeline_item_id"],
                "output_start_frame": item_start + overlay["local_in_frame"],
                "output_end_frame": item_start + overlay["local_out_frame"],
                "text": overlay["text"],
                "kind": overlay["kind"],
            }
        )
    for item in normalized["timeline_items"]:
        if item["type"] != "generated_card":
            continue
        item_start, item_end = item_spans[item["id"]]
        compiled_overlays.append(
            {
                "id": f"generated-{item['id']}",
                "timeline_item_id": item["id"],
                "output_start_frame": item_start,
                "output_end_frame": item_end,
                "text": item["text"],
                "kind": "chapter_card",
            }
        )
    compiled_overlays.sort(
        key=lambda value: (value["output_start_frame"], value["id"])
    )

    compiled_beats: list[dict[str, Any]] = []
    for beat in normalized["story_beats"]:
        first_item = beat["timeline_item_ids"][0]
        last_item = beat["timeline_item_ids"][-1]
        compiled_beats.append(
            {
                "id": beat["id"],
                "role": beat["role"],
                "output_start_frame": item_spans[first_item][0],
                "output_end_frame": item_spans[last_item][1],
                "timeline_item_ids": beat["timeline_item_ids"],
            }
        )

    compiled_edges: list[dict[str, Any]] = []
    for edge in normalized["join_edges"]:
        boundary = item_spans[edge["from_item_id"]][1]
        compiled_edges.append(
            {
                **edge,
                "output_frame": boundary,
                "output_sample": _output_sample_for_frame(
                    boundary,
                    fps=source["fps"],
                    sample_rate=source["output_sample_rate"],
                ),
            }
        )

    total_samples = _output_sample_for_frame(
        output_cursor,
        fps=source["fps"],
        sample_rate=source["output_sample_rate"],
    )
    return {
        "schema_version": COMPILED_TIMELINE_SCHEMA_VERSION,
        "compiler_version": COMPILER_VERSION,
        "project_id": normalized["project_id"],
        "source_id": normalized["source_id"],
        "edit_plan_hash": content_hash(normalized),
        "output": {
            "fps_num": source["fps_integer"],
            "fps_den": 1,
            "audio_sample_rate": source["output_sample_rate"],
            "total_frames": output_cursor,
            "total_samples": total_samples,
        },
        "story_beats": compiled_beats,
        "video_segments": video_segments,
        "audio_segments": audio_segments,
        "captions": compiled_captions,
        "overlays": compiled_overlays,
        "join_edges": compiled_edges,
        "source_regions": normalized["source_regions"],
    }


def assert_compiled_timeline(value: Mapping[str, Any]) -> dict[str, Any]:
    value = _object(value, "compiled timeline")
    if value.get("schema_version") != COMPILED_TIMELINE_SCHEMA_VERSION:
        raise ValidationError("unsupported compiled timeline schema version")
    if value.get("compiler_version") != COMPILER_VERSION:
        raise ValidationError("compiled timeline compiler version mismatch")
    required_lists: Iterable[str] = (
        "story_beats",
        "video_segments",
        "audio_segments",
        "captions",
        "overlays",
        "join_edges",
    )
    if any(not isinstance(value.get(name), list) for name in required_lists):
        raise ValidationError("compiled timeline is incomplete")
    output = _object(value.get("output"), "compiled output")
    if _integer(output.get("total_frames"), "compiled total frames", minimum=1) < 1:
        raise ValidationError("compiled timeline is empty")
    _integer(output.get("total_samples"), "compiled total samples", minimum=1)
    return dict(value)
