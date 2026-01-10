# Auto-transfer (Pi -> Mac) + Auto-processing (Mac)

This repo includes the same two-part automation as `eyeSSEF_modified-main`:

1) **Pi autosend**: `plr_autosend.sh` watches the Pi recording folder and pushes new videos to your Mac inbox.
2) **Mac watcher**: `watch_inbox.py` watches the inbox and runs the EyeSSEF pipeline in **session mode**.

---

## Part A — Raspberry Pi (autosend)

### 1) Install dependencies on Pi
```bash
sudo apt-get update
sudo apt-get install -y inotify-tools rsync openssh-client
```

### 2) Edit `plr_autosend.sh` ONLY if needed
Open the script and check these three lines:
- `SRC_DIR=...`  (your Pi recording directory, e.g. `/home/<pi_user>/PLR_Video`)
- `MAC_USER=...`
- `MAC_HOST=...` (your Mac IP on the same network, e.g. `172.20.10.4`)
- `MAC_INBOX=...` (your Mac inbox folder, e.g. `/Users/<mac_user>/plr_inbox`)

> If your existing Pi already has the correct `plr_autosend.sh`, you can keep using it as-is.
> This copy is provided mainly so the Mac-side repo contains the full setup.

### 3) Run autosend on Pi
```bash
chmod +x plr_autosend.sh
./plr_autosend.sh
```

---

## Part B — Mac (session mode processing)

### 1) Create inbox folder
```bash
mkdir -p ~/plr_inbox
mkdir -p ~/plr_inbox/_processing
mkdir -p ~/plr_inbox/_archive
```

### 2) Install watcher dependency (recommended)
```bash
python3 -m pip install -r requirements_inbox.txt
```

> `watch_inbox.py` uses a simple polling loop, so `watchdog` is optional.

### 3) Run the Mac watcher (from repo root)
```bash
python3 watch_inbox.py --inbox ~/plr_inbox --repo .
```

What happens in **session mode**:
- Pi uploads `*.part` then renames to the final `*.mp4`
- watcher ignores `.part`, waits until file size is stable
- for every new video in the inbox root, watcher:
  - moves the video into `~/plr_inbox/_processing/`
  - runs **raw extraction only**:
    - `videoImplement/main.py --input <video> --no_raw_plot --no_preprocess`
  - archives the source video into `~/plr_inbox/_archive/`
  - saves the raw trial folder into:
    - `videoImplement/sessions/session_<timestamp>/trial/<video_stem>/`

When you are done collecting videos for that session, type this **in the same Terminal**:

```
process
```

Then the watcher will:
- run `videoImplement/process.py` on **every** trial folder in `trial/` (no plot windows)
- create exactly **one** averaged signal across **all** trials in:
  - `videoImplement/sessions/session_<timestamp>/average/raw.csv`
- run `videoImplement/process.py` on `average/` and **show** the interactive matplotlib plots
- exit (start a new session by running `watch_inbox.py` again)

---

## Troubleshooting

### The Pi keeps asking for password
Set up SSH keys (recommended):

On Pi:
```bash
ssh-keygen -t ed25519
ssh-copy-id <MAC_USER>@<MAC_HOST>
```

### Watcher keeps reprocessing old files
- Clear the inbox (leave only new incoming videos), or
- Put processed videos in `_archive` (default behaviour already)

### It opens plot windows during `process`
This is expected: the session-average `process.py` run opens interactive plot windows.
Close the plot windows to let the script finish and exit.

