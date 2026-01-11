# Outputs and folder structure

## 1) Manual mode (`videoImplement/main.py`)

When you run:

```bash
python videoImplement/main.py --input <video>
```

EyeSSEF creates one folder per video under:

```
videoImplement/data/<video_stem>/
```

Inside that folder:

| File | What it is |
|---|---|
| `raw.csv` | Frame-by-frame pupil estimate (pixels + mm), timestamps, and confidence |
| `rawPlot.png` | Plot of the raw pupil diameter trace |
| `processed_interpolated.csv` | Output after Pass 1–4 (flagging + interpolation) |
| `processed.csv` | Final signal after Pass 6 (Savitzky–Golay smoothing) |
| `processedPlot.png` | Plot of the final processed trace |

### `raw.csv` columns

- `frame_id` — integer frame index
- `timestamp` — seconds from start (derived from fps)
- `diameter` — pupil diameter estimate in **pixels**
- `confidence` — ellipse/outline confidence (0–1)
- `is_bad_data` — `True` if confidence < threshold (default 0.75) or missing value
- `diameter_mm` — diameter converted to **mm** (using px/mm calibration)

---

## 2) Batch averaging (`videoImplement/process.py` in batch mode)

When you run:

```bash
python videoImplement/process.py --data videoImplement/data
```

`process.py` groups trials by:

- user
- eye side (L/R)
- resolution
- fps

Then it processes the **latest two** trials in each group and produces an averaged output folder:

```
videoImplement/data/PLR_<user>_<eye>_<res>_<fps>_AVG/
  processed_avg_interpolated.csv
  processed_avg.csv
  processedAvgPlot.png
```

---

## 3) Inbox watcher sessions (`watch_inbox.py`)

Session mode outputs go under:

```
videoImplement/sessions/session_<YYYYMMDD_HHMMSS>/
  trial/
    <video_stem_1>/...
    <video_stem_2>/...
    ...
  average/
    raw.csv
    processed_interpolated.csv
    processed.csv
    processedPlot.png
```

Key idea:
- `trial/` contains per-trial results
- `average/` contains **one** averaged result across *all* trials in that session
