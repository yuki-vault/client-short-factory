from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .mutations import (
    BUSY_EXIT_CODE,
    GlobalMutationLock,
    LockBusyError,
    run_adopt_candidate_worker,
    run_render_worker,
    run_save_worker,
)
from .pipeline import Pipeline, RunOptions
from .settings import PROJECT_ROOT, load_config, resolve_media_tools


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="client-short-factory",
        description="Create a local captioned 9:16 short from an authorized URL or file.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="run or resume one video job")
    run.add_argument("--input", required=True, help="authorized URL or local file")
    run.add_argument("--start", required=True, help="SS, MM:SS, or HH:MM:SS")
    run.add_argument("--end", required=True, help="SS, MM:SS, or HH:MM:SS")
    run.add_argument("--job-id")
    run.add_argument("--jobs-root", type=Path, default=PROJECT_ROOT / "jobs")
    run.add_argument("--template", default="default")
    run.add_argument("--dictionary", default="default")
    run.add_argument("--bgm", type=Path)
    run.add_argument("--rights-confirmed", action="store_true")
    run.add_argument("--authorization-note", default="")
    run.add_argument("--model")
    run.add_argument("--device", choices=("cpu", "cuda", "auto"))
    run.add_argument("--compute-type")
    run.add_argument("--encoder", choices=("auto", "h264_nvenc", "libx264"))
    run.add_argument("--vad-filter", action=argparse.BooleanOptionalAction)
    run.add_argument("--keep-fillers", action="store_true")
    run.add_argument("--yt-dlp")
    run.add_argument("--ffmpeg")
    run.add_argument("--ffprobe")
    run.add_argument(
        "--acquire-mode",
        choices=("auto", "partial", "full"),
        default="auto",
        help="partial first, full cache only, or automatic fallback",
    )
    run.add_argument(
        "--fallback-height",
        type=int,
        choices=(144, 240, 360, 480, 720, 1080),
        help="maximum height for the full-source cache fallback",
    )
    run.add_argument(
        "--rerun-from",
        choices=("acquire", "audio", "transcribe", "subtitles", "render", "qc"),
        help="explicitly rerun this stage and all later stages",
    )

    save = subparsers.add_parser(
        "save-captions",
        help="save an immutable caption revision with text and timing edits",
    )
    save.add_argument("--job-id", required=True)
    save.add_argument("--jobs-root", type=Path, default=PROJECT_ROOT / "jobs")
    save_input = save.add_mutually_exclusive_group(required=True)
    save_input.add_argument("--captions-file", type=Path)
    save_input.add_argument("--stdin-json", action="store_true")

    render = subparsers.add_parser(
        "render-job",
        help="render one explicit immutable caption revision",
    )
    render.add_argument("--job-id", required=True)
    render.add_argument("--jobs-root", type=Path, default=PROJECT_ROOT / "jobs")
    render.add_argument("--caption-revision", type=int, required=True)

    review = subparsers.add_parser(
        "review-ui",
        help="start the standalone localhost caption review prototype",
    )
    review.add_argument("--jobs-root", type=Path, default=PROJECT_ROOT / "jobs")
    review.add_argument(
        "--composition-projects-root",
        type=Path,
        default=PROJECT_ROOT / "composition-projects",
    )
    review.add_argument("--port", type=int, default=0)
    review.add_argument("--no-browser", action="store_true")

    composition_save_worker = subparsers.add_parser(
        "composition-save-worker", help=argparse.SUPPRESS
    )
    composition_save_worker.add_argument("--projects-root", type=Path, required=True)
    composition_save_worker.add_argument("--project-id", required=True)

    composition_render_worker = subparsers.add_parser(
        "composition-render-worker", help=argparse.SUPPRESS
    )
    composition_render_worker.add_argument("--projects-root", type=Path, required=True)
    composition_render_worker.add_argument("--project-id", required=True)
    composition_render_worker.add_argument("--edit-revision", type=int, required=True)
    composition_render_worker.add_argument(
        "--profile", choices=("proxy", "final"), default="proxy"
    )

    candidate_worker = subparsers.add_parser(
        "candidate-worker", help=argparse.SUPPRESS
    )
    candidate_worker.add_argument("--candidate-root", type=Path, required=True)
    candidate_worker.add_argument("--run-id", required=True)
    candidate_worker.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "config" / "candidates" / "default.json",
    )
    authorize_codex = subparsers.add_parser(
        "authorize-candidate-codex", help=argparse.SUPPRESS
    )
    authorize_codex.add_argument("--candidate-root", type=Path, required=True)
    authorize_codex.add_argument("--run-id", required=True)
    authorize_codex.add_argument("--approval-note", required=True)
    authorize_codex.add_argument("--rights-record", required=True)
    adopt_candidate = subparsers.add_parser(
        "adopt-candidate-range", help=argparse.SUPPRESS
    )
    adopt_candidate.add_argument("--jobs-root", type=Path, required=True)
    adopt_candidate.add_argument("--candidate-root", type=Path, required=True)
    adopt_candidate.add_argument("--composition-projects-root", type=Path, required=True)
    adopt_candidate.add_argument("--run-id", required=True)
    adopt_candidate.add_argument("--candidate-id", required=True)
    adopt_candidate.add_argument("--start", type=float, required=True)
    adopt_candidate.add_argument("--end", type=float, required=True)

    composition_init = subparsers.add_parser(
        "composition-init",
        help="create one immutable-source C0 composition project",
    )
    composition_init.add_argument("--project-id", required=True)
    composition_init.add_argument("--source", type=Path, required=True)
    composition_init.add_argument(
        "--projects-root",
        type=Path,
        default=PROJECT_ROOT / "composition-projects",
    )
    composition_init.add_argument("--template", default="default")
    composition_init.add_argument("--rights-confirmed", action="store_true")
    composition_init.add_argument("--authorization-note", required=True)
    composition_init.add_argument("--ffmpeg")
    composition_init.add_argument("--ffprobe")

    composition_publish = subparsers.add_parser(
        "composition-publish-edit",
        help="validate and publish one immutable C0 EditPlan revision",
    )
    composition_publish.add_argument("--project-id", required=True)
    composition_publish.add_argument("--edit-file", type=Path, required=True)
    composition_publish.add_argument("--base-revision", type=int)
    composition_publish.add_argument(
        "--projects-root",
        type=Path,
        default=PROJECT_ROOT / "composition-projects",
    )

    composition_compile = subparsers.add_parser(
        "composition-compile",
        help="verify and print one explicit C0 compiled timeline",
    )
    composition_compile.add_argument("--project-id", required=True)
    composition_compile.add_argument("--edit-revision", type=int, required=True)
    composition_compile.add_argument(
        "--projects-root",
        type=Path,
        default=PROJECT_ROOT / "composition-projects",
    )

    composition_render = subparsers.add_parser(
        "composition-render",
        help="render one explicit immutable C0 EditPlan revision",
    )
    composition_render.add_argument("--project-id", required=True)
    composition_render.add_argument("--edit-revision", type=int, required=True)
    composition_render.add_argument(
        "--profile", choices=("proxy", "final"), default="final"
    )
    composition_render.add_argument(
        "--projects-root",
        type=Path,
        default=PROJECT_ROOT / "composition-projects",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "composition-init":
        from .composition_artifacts import create_composition_project

        try:
            config, _ = load_config(args.template, "default")
            tools = resolve_media_tools(ffmpeg=args.ffmpeg, ffprobe=args.ffprobe)
            with GlobalMutationLock(args.projects_root):
                result = create_composition_project(
                    args.projects_root,
                    args.project_id,
                    source_path=args.source,
                    rights_confirmed=args.rights_confirmed,
                    authorization_note=args.authorization_note,
                    config=config,
                    ffmpeg=tools["ffmpeg"],
                    ffprobe=tools["ffprobe"],
                )
        except LockBusyError:
            print("BUSY: another mutation is already running", file=sys.stderr)
            return BUSY_EXIT_CODE
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(
            json.dumps(
                {
                    "ok": True,
                    "project_id": result["project_id"],
                    "source_sha256": result["source"]["sha256"],
                },
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "composition-publish-edit":
        from .composition_artifacts import (
            publish_edit_revision,
            safe_composition_project_dir,
        )

        try:
            payload = json.loads(args.edit_file.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("edit file must contain a JSON object")
            with GlobalMutationLock(args.projects_root):
                project_dir = safe_composition_project_dir(
                    args.projects_root, args.project_id
                )
                result = publish_edit_revision(
                    project_dir,
                    payload,
                    base_revision=args.base_revision,
                )
        except LockBusyError:
            print("BUSY: another mutation is already running", file=sys.stderr)
            return BUSY_EXIT_CODE
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(
            json.dumps(
                {
                    "ok": True,
                    "project_id": result["project_id"],
                    "edit_revision": result["revision"],
                    "edit_plan_hash": result["plan_hash"],
                    "compiled_timeline_hash": result["compiled_timeline_hash"],
                },
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "composition-compile":
        from .composition_artifacts import (
            load_compiled_timeline,
            safe_composition_project_dir,
        )

        try:
            project_dir = safe_composition_project_dir(
                args.projects_root, args.project_id
            )
            result = load_compiled_timeline(project_dir, args.edit_revision)
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "composition-render":
        from .composition_artifacts import safe_composition_project_dir
        from .composition_rendering import render_composition_revision

        try:
            with GlobalMutationLock(args.projects_root):
                project_dir = safe_composition_project_dir(
                    args.projects_root, args.project_id
                )
                result = render_composition_revision(
                    project_dir,
                    args.edit_revision,
                    render_profile=args.profile,
                )
        except LockBusyError:
            print("BUSY: another mutation is already running", file=sys.stderr)
            return BUSY_EXIT_CODE
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=False))
        return 0
    if args.command == "save-captions":
        return run_save_worker(
            jobs_root=args.jobs_root,
            job_id=args.job_id,
            stdin_json=args.stdin_json,
            captions_file=args.captions_file,
        )
    if args.command == "render-job":
        return run_render_worker(
            jobs_root=args.jobs_root,
            job_id=args.job_id,
            caption_revision=args.caption_revision,
        )
    if args.command == "review-ui":
        from .review_server import serve

        return serve(
            jobs_root=args.jobs_root,
            composition_projects_root=args.composition_projects_root,
            port=args.port,
            open_browser=not args.no_browser,
        )
    if args.command == "composition-save-worker":
        from .mutations import run_composition_save_worker

        return run_composition_save_worker(
            projects_root=args.projects_root,
            project_id=args.project_id,
        )
    if args.command == "composition-render-worker":
        from .mutations import run_composition_render_worker

        return run_composition_render_worker(
            projects_root=args.projects_root,
            project_id=args.project_id,
            edit_revision=args.edit_revision,
            render_profile=args.profile,
        )
    if args.command == "candidate-worker":
        from .candidate_artifacts import CandidateBusyError
        from .candidate_worker import run_candidate_worker

        try:
            result = run_candidate_worker(
                args.candidate_root, args.run_id, args.config
            )
        except CandidateBusyError:
            return BUSY_EXIT_CODE
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=False))
        return 0
    if args.command == "adopt-candidate-range":
        return run_adopt_candidate_worker(
            jobs_root=args.jobs_root,
            candidate_root=args.candidate_root,
            composition_projects_root=args.composition_projects_root,
            run_id=args.run_id,
            candidate_id=args.candidate_id,
            start=args.start,
            end=args.end,
        )
    if args.command == "authorize-candidate-codex":
        from .candidate_artifacts import record_codex_selection_authorization

        try:
            result = record_codex_selection_authorization(
                args.candidate_root,
                args.run_id,
                approval_note=args.approval_note,
                rights_record=args.rights_record,
            )
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(
            json.dumps(
                {
                    "ok": True,
                    "run_id": result["run_id"],
                    "provider": result["provider"],
                    "model": result["model"],
                    "content_sha256": result["content_sha256"],
                },
                ensure_ascii=False,
            )
        )
        return 0
    if args.command != "run":
        return 2
    try:
        with GlobalMutationLock(args.jobs_root):
            pipeline = Pipeline(
                RunOptions(
                    source=args.input,
                    start=args.start,
                    end=args.end,
                    job_id=args.job_id,
                    jobs_root=args.jobs_root,
                    template=args.template,
                    dictionary=args.dictionary,
                    bgm=args.bgm,
                    rights_confirmed=args.rights_confirmed,
                    authorization_note=args.authorization_note,
                    model=args.model,
                    device=args.device,
                    compute_type=args.compute_type,
                    encoder=args.encoder,
                    vad_filter=args.vad_filter,
                    keep_fillers=args.keep_fillers,
                    yt_dlp=args.yt_dlp,
                    ffmpeg=args.ffmpeg,
                    ffprobe=args.ffprobe,
                    acquire_mode=args.acquire_mode,
                    fallback_height=args.fallback_height,
                    rerun_from=args.rerun_from,
                )
            )
            output = pipeline.run()
    except LockBusyError:
        print("BUSY: another mutation is already running", file=sys.stderr)
        return BUSY_EXIT_CODE
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
