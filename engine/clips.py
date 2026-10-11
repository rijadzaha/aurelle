"""
Step 3: turn each photo into a 5-second clip with fal.ai.

Clips are made a few at a time. Any clip that fails is written to the failure
log, and after the first round every failed clip is tried once more. Clips that
already exist from an earlier run are reused, so you are not charged twice.
"""

import datetime
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import fal_client

from .video_models import CLIP_PROMPT, NEGATIVE_PROMPT


def _log_failure(log_path, photo_name, attempt, error):
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(f"{stamp}  attempt {attempt}  {photo_name}  FAILED: {error}\n")


def _make_one_clip(model, image_path, clip_path):
    image_url = fal_client.upload_file(str(image_path))
    arguments = {"prompt": CLIP_PROMPT, "image_url": image_url, **model["extra_args"]}
    if model.get("supports_negative_prompt"):
        arguments["negative_prompt"] = NEGATIVE_PROMPT
    result = fal_client.subscribe(model["endpoint"], arguments=arguments)
    video_url = result["video"]["url"]

    partial = clip_path.with_suffix(".part")
    urllib.request.urlretrieve(video_url, partial)
    partial.rename(clip_path)


def make_clips(jobs, model, costs, log_path, max_parallel):
    """
    jobs: list of (photo_name, widescreen_image_path, clip_path) in tour order.
    Returns the list of clip paths that exist at the end, in tour order.
    """
    todo = []
    for job in jobs:
        if job[2].exists():
            costs.clips_reused += 1
            print(f"  - {job[0]}: reusing clip from an earlier run")
        else:
            todo.append(job)

    for attempt in (1, 2):
        if not todo:
            break
        if attempt == 2:
            print(f"\n  Retrying {len(todo)} failed clip(s) once...")

        def run(job):
            name, image_path, clip_path = job
            try:
                _make_one_clip(model, image_path, clip_path)
                return job, None
            except Exception as e:  # any failure (network, fal.ai error, bad photo) is logged, not fatal
                return job, f"{type(e).__name__}: {e}"

        failed = []
        with ThreadPoolExecutor(max_workers=max_parallel) as pool:
            for job, error in pool.map(run, todo):
                if error is None:
                    costs.add_clip(model["price_per_clip"])
                    print(f"  - {job[0]}: done")
                else:
                    _log_failure(log_path, job[0], attempt, error)
                    print(f"  - {job[0]}: FAILED ({error})")
                    failed.append(job)
        todo = failed

    if todo:
        names = ", ".join(job[0] for job in todo)
        _log_failure(log_path, names, "final", "gave up after one retry; left out of the video")
        print(f"\n  These photos still failed after a retry and are left out: {names}")
        print(f"  Details are in {log_path}")

    return [job[2] for job in jobs if job[2].exists()]
