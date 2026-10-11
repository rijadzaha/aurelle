"""
Step 4: join the clips into one 16:9 video (1920x1080) with FFmpeg.

Each clip fades into the next (a "crossfade"). The music is looped if it is
shorter than the video, cut if it is longer, and faded out at the end.
"""

import subprocess

CROSSFADE_SECONDS = 0.6
WIDTH, HEIGHT, FPS = 1920, 1080, 30


class AssembleError(Exception):
    pass


def clip_length(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        raise AssembleError(f"Could not read the clip '{path.name}'. It may be damaged; delete it and run again.")


def build_video(clips, output_path, music_path=None, music_volume=0.6):
    if not clips:
        raise AssembleError("There are no clips to join.")

    lengths = [clip_length(c) for c in clips]
    fade = min(CROSSFADE_SECONDS, min(lengths) / 3)

    inputs = []
    for clip in clips:
        inputs += ["-i", str(clip)]

    # Make every clip the same size, frame rate and format so they can be joined.
    parts = []
    for i in range(len(clips)):
        parts.append(
            f"[{i}:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},setsar=1,fps={FPS},format=yuv420p,settb=AVTB[v{i}]"
        )

    # Chain the crossfades: clip 0 fades into clip 1, that result fades into clip 2, and so on.
    current, total = "[v0]", lengths[0]
    for i in range(1, len(clips)):
        out = f"[x{i}]"
        parts.append(f"{current}[v{i}]xfade=transition=fade:duration={fade:.3f}:offset={total - fade:.3f}{out}")
        current, total = out, total + lengths[i] - fade

    # Gentle fade from black at the start and to black at the end.
    parts.append(f"{current}fade=t=in:st=0:d=0.5,fade=t=out:st={total - 0.8:.3f}:d=0.8[vout]")

    maps = ["-map", "[vout]"]
    if music_path:
        inputs += ["-stream_loop", "-1", "-i", str(music_path)]
        m = len(clips)
        parts.append(
            f"[{m}:a]atrim=0:{total:.3f},asetpts=PTS-STARTPTS,volume={music_volume},"
            f"afade=t=in:st=0:d=1,afade=t=out:st={max(total - 2.5, 0):.3f}:d=2.5[aout]"
        )
        maps += ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"]

    command = [
        "ffmpeg", "-y", "-loglevel", "error", *inputs,
        "-filter_complex", ";".join(parts), *maps,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-t", f"{total:.3f}", "-movflags", "+faststart", str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise AssembleError(f"FFmpeg could not build the video:\n{result.stderr.strip()[-2000:]}")
    return total
