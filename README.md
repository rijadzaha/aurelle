# Aurelle: video engine

You give it a folder of 5 to 20 property photos. It gives you back one finished walkthrough video, `output.mp4`, in widescreen (16:9, 1920×1080), with crossfades and music.

## What happens when you run it

1. **Preparing.** FFmpeg makes two copies of each photo: a smaller one for Claude to look at, and a 16:9 one, cropped from the centre, to turn into video.
2. **Labelling.** Claude looks at all the photos together and labels each one: exterior, entrance, living room, kitchen, bedroom, bathroom, outdoor, or other.
3. **Ordering.** Claude puts the photos in walkthrough order: outside → front door → living spaces → kitchen → bedrooms → bathrooms → garden.
4. **Making clips.** Each photo is sent to fal.ai (Kling) to become a 5-second clip with a slow, smooth camera push-in. The prompt asks it to keep the room exactly as shown, with no people and no new objects.
5. **Retrying.** If a clip fails, it is written to `failed_clips.log` and tried **once** more. If it fails again, that photo is left out and the video is made without it.
6. **Joining.** FFmpeg joins the clips with short crossfades, adds your music (looped or cut to fit, fading out at the end) and saves `output.mp4`.
7. **Cost.** It prints what the run cost: Claude plus fal.ai.

Before it spends money on clips, it tells you the estimated cost and waits for you to type `y`.

---

## One-time setup

### 1. Install Python
- **Mac:** download it from https://www.python.org/downloads/ and run the installer.
- **Windows:** same page. In the installer, **tick "Add Python to PATH"** before clicking Install.

### 2. Install FFmpeg (the video-joining program)
- **Mac:** first install Homebrew from https://brew.sh (copy the command on that page into **Terminal**). Then type `brew install ffmpeg` and press Enter.
- **Windows:** open **PowerShell** and type `winget install ffmpeg`, then press Enter. Close PowerShell and open it again afterwards.

To check it worked, type `ffmpeg -version`. Some text should appear.

### 3. Get the code onto your computer
On GitHub, open the repository, switch to the branch `claude/aurelle-video-engine-yzdiar`, click the green **Code** button, then **Download ZIP**. Unzip it somewhere easy, such as your Desktop.

### 4. Open a terminal inside that folder
- **Mac:** open **Terminal**, type `cd ` (with a space after it), drag the unzipped folder into the window, and press Enter.
- **Windows:** open the unzipped folder, click the address bar at the top, type `powershell` and press Enter.

### 5. Install the three add-ons the tool needs
This installs `anthropic` (talks to Claude), `fal-client` (talks to fal.ai) and `python-dotenv` (reads your keys file). Type:

- **Mac:** `python3 -m pip install -r requirements.txt`
- **Windows:** `python -m pip install -r requirements.txt`

### 6. Add your keys
1. Get an Anthropic key at https://console.anthropic.com, under **API Keys**.
2. Get a fal.ai key at https://fal.ai/dashboard/keys.
3. In the folder, make a copy of `.env.example` and name the copy exactly `.env`.
4. Open `.env` in a text editor (TextEdit or Notepad), paste your two keys in place of the `paste-...` text, and save.

`.env` is listed in `.gitignore`, so git never uploads it. Don't email it or paste it anywhere.

---

## Making a video

Put your photos in a folder, for example `photos/12-oak-street`, and your music file somewhere, for example `music/calm.mp3`. Then type:

- **Mac:** `python3 aurelle.py photos/12-oak-street --music music/calm.mp3`
- **Windows:** `python aurelle.py photos\12-oak-street --music music\calm.mp3`

The tool shows the tour order and the estimated clip cost, then asks you to confirm. Type `y` and press Enter. Clips take a few minutes each, and 4 are made at a time.

Your video ends up in `output/12-oak-street/output.mp4`.

### Useful extras
| Add this | What it does |
|---|---|
| `--plan-only` | Only labels and orders the photos (a few cents). No video and no fal.ai cost. Good for a first check. |
| `--relabel` | Asks Claude again, even if these photos were already labelled. |
| `--model kling-2.1-standard` | Uses a different video model for this run. |
| `--yes` | Skips the "type y to continue" question. |

### Changing the order yourself
After a run, open `output/<folder>/plan.json` in a text editor and move the entries around. Run the same command again. It uses your order and doesn't charge for Claude.

### Running again is cheap
Finished clips are kept in `output/<folder>/clips/`. If you run again, for example to try different music, they are reused and you aren't charged for them again. To remake one clip, delete its `.mp4` file from that folder.

---

## Cost per video

At the end of each run you'll see something like:

```
  Claude (photo labeling):  $  0.0900
  fal.ai (video clips):     $  4.2000   (12 new clips)
  TOTAL:                    $  4.2900
```

A copy is saved as `output/<folder>/cost.txt`. The Claude cost is worked out from the exact usage Claude reports. The fal.ai cost is **number of clips × the price per clip** written in `engine/video_models.py`. fal.ai doesn't report prices back, so if fal.ai changes its prices, update that number. Your fal.ai dashboard shows what you were actually billed.

Rough guide with the default model (Kling 2.5 Turbo Pro at $0.35 per clip): about **$2 for 5 photos** and **$7 for 20 photos**.

## Switching the video model

Open `.env` and change `VIDEO_MODEL=` to one of these names:

| Name | Price per 5-second clip |
|---|---|
| `kling-2.5-turbo-pro` (default) | $0.35 |
| `kling-2.1-standard` | $0.25 |

To add another fal.ai model, open `engine/video_models.py` and follow the note at the top of that file.

The photo-labelling model is set by `CLAUDE_MODEL` in `.env`. The default is `claude-opus-5-5`. `claude-haiku-5-5` is much cheaper if you want to try it.

## If something goes wrong

The tool explains problems in plain words and stops before spending money it doesn't need to. Common ones:
- **"ANTHROPIC_API_KEY is missing"**: check your `.env` file (step 6). In a Claude Code cloud environment, that name is hidden. Save the key as `AURELLE_ANTHROPIC_KEY` instead.
- **"FFmpeg is not installed"**: redo step 2, then close and reopen the terminal.
- **"A required add-on is missing"**: redo step 5.
- **A clip failed**: see `output/<folder>/failed_clips.log`. Running the same command again only remakes the missing clips.

## Files in this project

| File | What it is |
|---|---|
| `aurelle.py` | The command you run. Runs the steps in order. |
| `engine/photos.py` | Finds and prepares the photos. |
| `engine/labeling.py` | Asks Claude to label and order the photos. |
| `engine/clips.py` | Makes the clips on fal.ai, logs failures and retries once. |
| `engine/assemble.py` | Joins clips and music with FFmpeg. |
| `engine/video_models.py` | The list of video models, their prices and the camera prompt. |
| `engine/costs.py` | Adds up the cost. |
