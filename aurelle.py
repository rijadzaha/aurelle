"""
Aurelle video engine: turns a folder of property photos into one walkthrough video.

How to run (see README.md for full instructions):
    python aurelle.py path/to/photos --music path/to/music.mp3
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    from engine import assemble, clips, labeling, photos, smooth
except ImportError as e:
    sys.exit(
        f"A required add-on is missing ({e.name}).\n"
        "Install the add-ons first:  pip install -r requirements.txt"
    )
from engine.costs import CostTracker
from engine.video_models import DEFAULT_VIDEO_MODEL, VIDEO_MODELS


def parse_args():
    parser = argparse.ArgumentParser(description="Turn property photos into a walkthrough video.")
    parser.add_argument("photos", help="folder with 5 to 20 property photos")
    parser.add_argument("--music", help="music file to play under the video (mp3, wav, m4a...)")
    parser.add_argument("--out", help="folder for the results (default: output/<photo folder name>)")
    parser.add_argument("--model", help=f"video model to use, one of: {', '.join(VIDEO_MODELS)}")
    parser.add_argument("--plan-only", action="store_true",
                        help="only label and order the photos (costs a few cents); make no video")
    parser.add_argument("--relabel", action="store_true",
                        help="ask Claude again even if the photos were labeled in an earlier run")
    parser.add_argument("--walkthrough", action="store_true",
                        help="camera travels from each photo to the next (needs a model that takes an end photo)")
    parser.add_argument("--only", type=int, metavar="N",
                        help="with --walkthrough: make only move N (1 = photo 1 to 2), as a cheap test; no final video")
    parser.add_argument("--yes", action="store_true", help="do not ask for confirmation before spending")
    return parser.parse_args()


def fail(message):
    print(f"\nSTOPPED: {message}")
    sys.exit(1)


def main():
    args = parse_args()
    load_dotenv()  # reads the keys from the .env file

    # Claude Code cloud environments hide ANTHROPIC_API_KEY, so AURELLE_ANTHROPIC_KEY also works.
    anthropic_key = os.environ.get("AURELLE_ANTHROPIC_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")
    if not anthropic_key or anthropic_key.startswith("paste-"):
        fail("ANTHROPIC_API_KEY is missing. Put it in your .env file (see .env.example).\n"
             "  In a Claude Code cloud environment, name it AURELLE_ANTHROPIC_KEY instead.")
    fal_key = os.environ.get("FAL_KEY", "")
    if not fal_key or fal_key.startswith("paste-"):
        fail("FAL_KEY is missing. Put it in your .env file (see .env.example).")

    model_name = args.model or os.environ.get("VIDEO_MODEL") or DEFAULT_VIDEO_MODEL
    if model_name not in VIDEO_MODELS:
        fail(f"Unknown video model '{model_name}'. Choose one of: {', '.join(VIDEO_MODELS)}")
    video_model = VIDEO_MODELS[model_name]
    claude_model = os.environ.get("CLAUDE_MODEL") or "claude-opus-5-5"
    max_parallel = int(os.environ.get("MAX_PARALLEL_CLIPS") or 4)
    music_volume = float(os.environ.get("MUSIC_VOLUME") or 0.6)

    if args.walkthrough and not video_model.get("supports_end_image"):
        able = ", ".join(n for n, m in VIDEO_MODELS.items() if m.get("supports_end_image"))
        fail(f"The model '{model_name}' can't do --walkthrough. Use one of: {able}")
    if args.only is not None and not args.walkthrough:
        fail("--only works together with --walkthrough.")

    music = Path(args.music) if args.music else None
    if music and not music.is_file():
        fail(f"The music file '{music}' does not exist.")

    costs = CostTracker()

    try:
        photos.check_ffmpeg()
        photo_files = photos.find_photos(args.photos)
    except photos.PhotoError as e:
        fail(str(e))

    out_dir = Path(args.out) if args.out else Path("output") / Path(args.photos).resolve().name
    prepared_dir = out_dir / "prepared"
    clips_dir = out_dir / "clips" / model_name
    prepared_dir.mkdir(parents=True, exist_ok=True)
    clips_dir.mkdir(parents=True, exist_ok=True)
    plan_path = out_dir / "plan.json"
    log_path = out_dir / "failed_clips.log"

    print(f"\nFound {len(photo_files)} photos. Results will go in: {out_dir}")

    # --- Prepare the photos ---------------------------------------------------
    print("\nPreparing photos...")
    previews, widescreens = {}, {}
    try:
        for p in photo_files:
            previews[p.name] = photos.make_preview(p, prepared_dir / f"{p.stem}_preview.jpg")
            widescreens[p.name] = photos.make_widescreen(p, prepared_dir / f"{p.stem}_16x9.jpg")
    except photos.PhotoError as e:
        fail(str(e))

    # --- Steps 1 and 2: label and order with Claude ---------------------------
    names = sorted(p.name for p in photo_files)
    plan = None
    if plan_path.exists() and not args.relabel:
        saved = json.loads(plan_path.read_text())
        if sorted(item["file"] for item in saved) == names:
            plan = saved
            print("\nUsing the labels and order from an earlier run (no Claude cost).")
            print("  To ask Claude again, add --relabel")
    if plan is None:
        print(f"\nAsking Claude ({claude_model}) to label and order the photos...")
        try:
            plan = labeling.label_and_order(photo_files, [previews[p.name] for p in photo_files],
                                            claude_model, costs, anthropic_key)
        except labeling.LabelingError as e:
            print(costs.report())
            fail(str(e))
        plan_path.write_text(json.dumps(plan, indent=2))

    print("\nTour order:")
    for i, item in enumerate(plan, start=1):
        print(f"  {i:2}. {item['room']:<12} {item['file']:<28} {item['description']}")
    print(f"  (Saved to {plan_path}. You can edit that file to change the order, then run again.)")

    if args.plan_only:
        print(costs.report())
        return

    # --- Step 3: make the clips with fal.ai -----------------------------------
    if args.walkthrough:
        # One clip per move: it starts on one photo and ends on the next.
        jobs = []
        for a, b in zip(plan, plan[1:]):
            name = f"{Path(a['file']).stem}_to_{Path(b['file']).stem}"
            jobs.append((name, widescreens[a["file"]], clips_dir / f"{name}.mp4", widescreens[b["file"]]))
        if args.only is not None:
            if not 1 <= args.only <= len(jobs):
                fail(f"--only must be between 1 and {len(jobs)} (there are {len(jobs)} moves).")
            jobs = [jobs[args.only - 1]]
        print("\nWalkthrough moves:")
        for job in jobs:
            print(f"  - {job[0]}")
    else:
        jobs = [(item["file"], widescreens[item["file"]], clips_dir / f"{Path(item['file']).stem}.mp4", None)
                for item in plan]
    new_clips = sum(1 for job in jobs if not job[2].exists())
    estimate = new_clips * video_model["price_per_clip"]
    print(f"\nVideo model: {model_name}  ({video_model['endpoint']})")
    print(f"About to make {new_clips} new clip(s), estimated fal.ai cost ${estimate:.2f}.")
    if new_clips and not args.yes:
        answer = input("Type y and press Enter to continue (anything else cancels): ").strip().lower()
        if answer != "y":
            print("Cancelled. Nothing was spent on video clips.")
            print(costs.report())
            return

    print("\nMaking clips (each takes a few minutes)...")
    finished = clips.make_clips(jobs, video_model, costs, log_path, max_parallel)

    # --- Step 4: join everything ----------------------------------------------
    if not finished:
        print(costs.report())
        fail(f"No clips were made, so there is no video. See {log_path}")
    if args.only is not None:
        print(f"\nTest clip ready: {finished[0]}  (no final video is made with --only)")
        print(costs.report())
        return
    if not music:
        print("\nNo music file given (--music), so the video will be silent.")
    output_path = out_dir / "output.mp4"
    print(f"\nJoining {len(finished)} clips into {output_path}...")
    try:
        crossfade = assemble.CROSSFADE_SECONDS
        if args.walkthrough:
            # Even out the camera speed so it doesn't slow down at every photo (free, done on this computer).
            print("Evening out the camera speed...")
            finished = smooth.smooth_clips(finished, out_dir / "smoothed")
            # Each clip ends where the next begins, so only a very short blend is needed.
            crossfade = 0.1
        seconds = assemble.build_video(finished, output_path, music, music_volume, crossfade)
    except assemble.AssembleError as e:
        print(costs.report())
        fail(str(e))

    # --- Step 5: cost report --------------------------------------------------
    report = costs.report()
    print(f"\nDONE! Your video is ready: {output_path}  ({seconds:.0f} seconds)")
    print(report)
    (out_dir / "cost.txt").write_text(report.strip() + "\n")


if __name__ == "__main__":
    main()
