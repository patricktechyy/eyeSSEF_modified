# Usage

This repo has two main ways to run:

1) **Manual / batch**: you run `videoImplement/main.py` and `videoImplement/process.py` yourself.
2) **Inbox watcher**: `watch_inbox.py` monitors an “inbox” folder and builds a session automatically.

---

## A. Manual processing

### 1) Process one video (raw + processed)

From the repo root:

```bash
python videoImplement/main.py --input path/to/video.mp4 --no_raw_plot
```

This will:
- extract frames
- run pupil detection
- write `raw.csv` + `rawPlot.png`
- run preprocessing and write `processed.csv` + `processedPlot.png`

Output folder:

```
videoImplement/data/<video_stem>/
  raw.csv
  rawPlot.png
  processed_interpolated.csv
  processed.csv
  processedPlot.png
```

### 2) Process a whole folder of videos

```bash
python videoImplement/main.py --input path/to/folder --recursive --no_raw_plot
```

### 3) Only generate raw.csv (skip preprocessing)

```bash
python videoImplement/main.py --input path/to/video.mp4 --no_raw_plot --no_preprocess
```

---

## B. Running `process.py` directly

### 1) Single-trial mode (folder that already contains raw.csv)

```bash
python videoImplement/process.py --data videoImplement/data/PLR_Patrick_R_1920x1080_30_2 --resolution 1920x1080 --fps 30
```

Notes:
- If the trial folder name follows the `PLR_...` convention, you often do **not** need to supply `--fps`.
- If `diameter_mm` is missing or you changed your px/mm calibration, add `--recompute_mm`.

### 2) Batch mode (parent folder containing many PLR_* trial folders)

```bash
python videoImplement/process.py --data videoImplement/data
```

Batch mode will:
- process each trial folder
- create one averaged output folder per group:
  `PLR_<user>_<eye>_<res>_<fps>_AVG/`

---

## C. Video naming convention (recommended)

Name trial videos like:

```
PLR_<User>_<EyeSide L/R>_<Resolution>_<FPS>_<TrialIndex>.mp4

Example:
PLR_Patrick_R_1920x1080_30_2.mp4
```

Why this matters:
- `main.py` can reliably infer fps/res without guessing.
- `process.py` can group and average trials correctly.

---

## D. Inbox watcher (session mode)

### 1) Create the inbox folders

```bash
mkdir -p ~/plr_inbox
mkdir -p ~/plr_inbox/_processing
mkdir -p ~/plr_inbox/_archive
```

### 2) Run the watcher

From the repo root:

```bash
python watch_inbox.py --inbox ~/plr_inbox
```

### 3) Collect trial videos

Copy/upload videos into `~/plr_inbox/`.

The watcher will automatically:
- wait until file size is stable
- run `main.py` raw extraction
- move trial results into `videoImplement/sessions/session_<timestamp>/trial/`
- archive source videos into `~/plr_inbox/_archive/`

### 4) Process the session

In the same terminal where the watcher is running, type:

```
process
```

This will:
- process all trials (no pop-up plots)
- build exactly **one** session average in:
  `videoImplement/sessions/session_<timestamp>/average/raw.csv`
- process the average (and show the plots)

If you do **not** want interactive plots, see `docs/TROUBLESHOOTING.md`.
