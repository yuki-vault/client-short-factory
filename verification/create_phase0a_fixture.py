from __future__ import annotations

import subprocess
from pathlib import Path

from short_factory.artifacts import initialize_machine_revision
from short_factory.settings import PROJECT_ROOT, load_config, resolve_tools
from short_factory.utils import atomic_write_json


JOBS_ROOT = PROJECT_ROOT / "scratch" / "phase-0a-webui" / "jobs"
JOB_ID = "phase0a-synthetic"


def main() -> int:
    job_dir = JOBS_ROOT / JOB_ID
    if job_dir.exists():
        raise RuntimeError(f"fixture already exists; refusing to overwrite: {job_dir}")
    source_dir = job_dir / "source"
    source_dir.mkdir(parents=True)
    acquired = source_dir / "acquired.mp4"
    tools = resolve_tools()
    subprocess.run(
        [
            str(tools["ffmpeg"]),
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=640x360:rate=30",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000",
            "-t",
            "8",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-shortest",
            str(acquired),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    config, _ = load_config("default", "default")
    config["render"]["encoder"] = "libx264"
    config["render"]["x264_preset"] = "veryfast"
    stat = acquired.stat()
    manifest = {
        "version": 3,
        "job_id": JOB_ID,
        "signature": "synthetic-phase0a-fixture",
        "source": str(acquired),
        "source_type": "synthetic",
        "start_seconds": 0.0,
        "end_seconds": 8.0,
        "duration_seconds": 8.0,
        "download_window": {
            "start_seconds": 0.0,
            "end_seconds": 8.0,
            "local_target_offset_seconds": 0.0,
        },
        "template": "default",
        "dictionary": "default",
        "config": config,
        "rights": {
            "confirmed": True,
            "authorization_note": "Programmatically generated synthetic fixture.",
        },
        "privacy": {"local_processing_only": True, "automatic_upload": False},
        "tools": {name: str(path) for name, path in tools.items()},
        "input_files": {
            "source": {
                "path": str(acquired),
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
            }
        },
        "created_at": "2026-08-12T00:00:00+00:00",
    }
    atomic_write_json(job_dir / "job.json", manifest)
    initialize_machine_revision(
        job_dir,
        [
            {"start": 0.0, "end": 2.4, "text": "合成テストです。"},
            {"start": 2.4, "end": 5.2, "text": "字幕を直します。"},
            {"start": 5.2, "end": 8.0, "text": "固定して出力。"},
        ],
    )
    print(JOBS_ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
