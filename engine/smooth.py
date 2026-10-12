"""
Evens out the camera speed of a walkthrough clip (free: no new clips are made).

Video models slow the camera down near the start and end photo, so a walkthrough
made of several clips goes go-stop-go-stop. This measures how much the picture
changes in each short piece of the clip, then speeds up the slow pieces and
slows down the fast ones, so the camera glides at one steady speed. All clips
get the same speed, so the whole walkthrough keeps its original total length.
"""

import subprocess

from .assemble import AssembleError, clip_length

PIECE_SECONDS = 0.25   # the clip is retimed in pieces this long
MIN_SPEED, MAX_SPEED = 0.6, 3.0   # never slower than 0.6x or faster than 3x


def _motion_per_frame(path):
    """How much the picture changes from each frame to the next (bigger = faster camera)."""
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-vf",
         "scale=320:-1,tblend=all_mode=difference,signalstats,"
         "metadata=print:key=lavfi.signalstats.YAVG:file=-",
         "-f", "null", "-"],
        capture_output=True, text=True,
    )
    values = [float(line.split("=")[1]) for line in result.stdout.splitlines() if "YAVG=" in line]
    if not values:
        raise AssembleError(f"Could not measure the camera speed in '{path.name}'.")
    return values


def _pieces(path):
    """Split a clip into short pieces: (start second, end second, how much it moves)."""
    length = clip_length(path)
    motion = _motion_per_frame(path)
    fps = len(motion) / length
    per_piece = max(1, round(PIECE_SECONDS * fps))
    pieces = []
    for start in range(0, len(motion), per_piece):
        chunk = motion[start:start + per_piece]
        pieces.append((start / fps, (start + len(chunk)) / fps, sum(chunk)))
    return pieces


def smooth_clips(paths, out_dir):
    """Smooth every clip to one shared steady speed. Returns the new clip paths."""
    all_pieces = [_pieces(p) for p in paths]
    total_length = sum(clip_length(p) for p in paths)
    average = sum(m for pieces in all_pieces for _, _, m in pieces) / total_length

    # First pass: how long everything would be; then stretch so the total length stays the same.
    plans = []
    for pieces in all_pieces:
        speeds = []
        for a, b, moved in pieces:
            rate = moved / (b - a)
            speeds.append(MAX_SPEED if rate == 0 else min(MAX_SPEED, max(MIN_SPEED, average / rate)))
        plans.append(speeds)
    new_total = sum((b - a) / s for pieces, speeds in zip(all_pieces, plans)
                    for (a, b, _), s in zip(pieces, speeds))
    stretch = total_length / new_total

    out_dir.mkdir(parents=True, exist_ok=True)
    return [_retime(path, out_dir / path.name, pieces, speeds, stretch)
            for path, pieces, speeds in zip(paths, all_pieces, plans)]


def _retime(path, out_path, pieces, speeds, stretch):
    parts, labels = [], []
    for i, ((a, b, _), s) in enumerate(zip(pieces, speeds)):
        factor = stretch / s
        parts.append(f"[0:v]trim=start={a:.4f}:end={b:.4f},setpts=(PTS-STARTPTS)*{factor:.4f}[p{i}]")
        labels.append(f"[p{i}]")
    parts.append(f"{''.join(labels)}concat=n={len(labels)}:v=1:a=0,fps=30[out]")

    result = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(path), "-filter_complex", ";".join(parts),
         "-map", "[out]", "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p",
         str(out_path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise AssembleError(f"Could not smooth '{path.name}':\n{result.stderr.strip()[-1500:]}")
    return out_path
