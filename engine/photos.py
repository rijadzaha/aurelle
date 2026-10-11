"""
Finds the photos in a folder and makes two copies of each with FFmpeg:
  - a smaller copy to show Claude (cheaper and faster to send)
  - a 16:9 copy (cropped from the center) to turn into a video clip
"""

import shutil
import subprocess
from pathlib import Path

PHOTO_TYPES = {".jpg", ".jpeg", ".png", ".webp"}
MIN_PHOTOS = 5
MAX_PHOTOS = 20


class PhotoError(Exception):
    pass


def check_ffmpeg():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise PhotoError(
            "FFmpeg is not installed (or not found). See the README section "
            "'Install FFmpeg', then try again."
        )


def find_photos(folder):
    folder = Path(folder)
    if not folder.is_dir():
        raise PhotoError(f"The folder '{folder}' does not exist.")
    photos = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in PHOTO_TYPES)
    if len(photos) < MIN_PHOTOS or len(photos) > MAX_PHOTOS:
        raise PhotoError(
            f"Found {len(photos)} photos in '{folder}'. Please use between "
            f"{MIN_PHOTOS} and {MAX_PHOTOS} photos (.jpg, .jpeg, .png or .webp)."
        )
    return photos


def _run_ffmpeg(args, what):
    result = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise PhotoError(f"FFmpeg could not {what}:\n{result.stderr.strip()}")


def make_preview(photo, out_path):
    """Shrink so the longest side is at most 1568 pixels (Claude's sweet spot)."""
    scale = "scale='if(gt(iw,ih),min(1568,iw),-2)':'if(gt(iw,ih),-2,min(1568,ih))'"
    _run_ffmpeg(["-i", str(photo), "-vf", scale, "-frames:v", "1", "-q:v", "3", str(out_path)],
                f"prepare '{photo.name}' for Claude")
    return out_path


def make_widescreen(photo, out_path):
    """Crop the center to 16:9 and size it to 1920x1080."""
    vf = "crop='min(iw,ih*16/9)':'min(ih,iw*9/16)',scale=1920:1080,setsar=1"
    _run_ffmpeg(["-i", str(photo), "-vf", vf, "-frames:v", "1", "-q:v", "2", str(out_path)],
                f"crop '{photo.name}' to 16:9")
    return out_path
