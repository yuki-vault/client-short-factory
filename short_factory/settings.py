from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _resolve_executable(
    explicit: str | None,
    env_name: str,
    command_name: str,
    candidates: list[Path],
) -> Path:
    requested = explicit or os.environ.get(env_name)
    if requested:
        path = Path(requested).expanduser().resolve()
        if path.is_file():
            return path
        raise FileNotFoundError(f"{env_name} points to a missing file: {path}")

    found = shutil.which(command_name)
    if found:
        return Path(found).resolve()

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()

    raise FileNotFoundError(
        f"Could not find {command_name}. Set {env_name} to its full path."
    )


def resolve_tools(
    yt_dlp: str | None = None,
    ffmpeg: str | None = None,
    ffprobe: str | None = None,
) -> dict[str, Path]:
    media = resolve_media_tools(ffmpeg=ffmpeg, ffprobe=ffprobe)
    local_app = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    winget = local_app / "Microsoft/WinGet/Packages"

    yt_candidates = [
        winget
        / "yt-dlp.yt-dlp_Microsoft.Winget.Source_8wekyb3d8bbwe"
        / "yt-dlp.exe"
    ]
    return {
        "yt_dlp": _resolve_executable(
            yt_dlp, "SHORT_FACTORY_YTDLP", "yt-dlp", yt_candidates
        ),
        **media,
    }


def resolve_media_tools(
    ffmpeg: str | None = None,
    ffprobe: str | None = None,
) -> dict[str, Path]:
    local_app = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    winget = local_app / "Microsoft/WinGet/Packages"
    ffmpeg_candidates = sorted(
        winget.glob(
            "Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-*/bin/ffmpeg.exe"
        ),
        reverse=True,
    )
    ffprobe_candidates = [path.with_name("ffprobe.exe") for path in ffmpeg_candidates]
    return {
        "ffmpeg": _resolve_executable(
            ffmpeg, "SHORT_FACTORY_FFMPEG", "ffmpeg", ffmpeg_candidates
        ),
        "ffprobe": _resolve_executable(
            ffprobe, "SHORT_FACTORY_FFPROBE", "ffprobe", ffprobe_candidates
        ),
    }


def load_config(template: str, dictionary: str) -> tuple[dict[str, Any], dict[str, Any]]:
    template_path = Path(template)
    if not template_path.is_file():
        template_path = PROJECT_ROOT / "config" / "templates" / f"{template}.json"
    dictionary_path = Path(dictionary)
    if not dictionary_path.is_file():
        dictionary_path = PROJECT_ROOT / "config" / "dictionaries" / f"{dictionary}.json"

    if not template_path.is_file():
        raise FileNotFoundError(f"subtitle template not found: {template}")
    if not dictionary_path.is_file():
        raise FileNotFoundError(f"dictionary not found: {dictionary}")

    return (
        json.loads(template_path.read_text(encoding="utf-8")),
        json.loads(dictionary_path.read_text(encoding="utf-8")),
    )
