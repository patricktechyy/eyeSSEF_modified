<<<<<<< Updated upstream
"""Watch an inbox folder for new .mp4 files and automatically run the pipeline.

Why:
- You run the algorithm on the laptop (not on the Pi)
- The Pi drops .mp4 recordings into the inbox (via rsync)
- We process one file at a time (simple)

This script calls:
  videoImplement/main.py       -> creates data/<session>/raw.csv + meta.json
  videoImplement/process_one.py -> creates data/<session>/processed.csv
=======
"""Watch a Mac inbox folder for new video files and automatically run EyeSSEF 15 pipeline.

Intended workflow (same as the original EyeSSEF_modified autosend):
1) Raspberry Pi records videos into /home/<pi_user>/PLR_Video
2) Pi runs plr_autosend.sh which rsync's videos into your Mac inbox as:
      <video>.part  -> then renames to <video> when upload completes
3) This watcher ignores *.part, waits until the final file is stable,
   then runs the pipeline locally (Mac), and finally archives the video.

Pipeline (EyeSSEF 15) (what this watcher enforces):
  1) Detect a *new* video in the inbox root (ignores subfolders like _archive/)
  2) Move it into inbox/_processing/ to prevent repeated triggers
  3) Run raw extraction only:
        videoImplement/main.py --input <video> --no_raw_plot --no_preprocess
     -> writes videoImplement/data/<stem>/raw.csv (+ meta.json)
  4) Move the video into inbox/_archive/ (so inbox stays clean)
  5) Run preprocessing ONLY for that one trial folder and SHOW plots:
        videoImplement/process.py --data videoImplement/data/<stem>
     -> writes processed.csv + saves PNGs + opens interactive plot windows

Notes:
- By default, this processes ONE file at a time (simple + avoids GPU/CPU overload).
- If watchdog is installed, it uses filesystem events; otherwise it falls back to polling.
>>>>>>> Stashed changes
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
<<<<<<< Updated upstream
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".avi"}


def wait_until_stable(path: Path, stable_for_s: float = 3.0, timeout_s: float = 600.0) -> bool:
    """Wait until file size doesn't change for `stable_for_s` seconds."""
=======
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Set


VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi"}
RESERVED_SUBDIRS = {"_archive", "_processing"}


def wait_until_stable(path: Path, stable_secs: float = 1.0, timeout_secs: float = 300.0) -> bool:
    """Return True when file size has been unchanged for `stable_secs` seconds."""
>>>>>>> Stashed changes
    start = time.time()
    last_size = -1
    stable_since = None

    while True:
        if not path.exists():
            return False

        try:
            size = path.stat().st_size
        except OSError:
            size = -1

        now = time.time()

        if size == last_size and size > 0:
            if stable_since is None:
                stable_since = now
<<<<<<< Updated upstream
            elif (now - stable_since) >= stable_for_s:
                # Extra check: can we open it for reading?
                try:
                    with open(path, "rb"):
                        return True
                except OSError:
                    pass
=======
            if (now - stable_since) >= stable_secs:
                return True
>>>>>>> Stashed changes
        else:
            stable_since = None
            last_size = size

<<<<<<< Updated upstream
        if (now - start) > timeout_s:
            return False

        time.sleep(0.5)


def run_pipeline(python_exe: Path, repo_dir: Path, video_path: Path, out_root: Path) -> None:
    """Run main.py then process_one.py."""
    vi_dir = repo_dir / "videoImplement"

    # 1) raw extraction
    subprocess.run(
        [
            str(python_exe),
            "main.py",
            "--video",
            str(video_path),
            "--out-root",
            str(out_root),
        ],
        cwd=str(vi_dir),
        check=True,
    )

    # Data folder name is video basename
    data_dir = (vi_dir / out_root / video_path.stem).resolve()

    # 2) preprocessing
    subprocess.run(
        [
            str(python_exe),
            "process_one.py",
            "--data-dir",
            str(data_dir),
        ],
=======
        if (now - start) > timeout_secs:
            return False

        time.sleep(0.2)


def _run_main_raw_only(python_exe: Path, repo_dir: Path, video_path: Path) -> None:
    """Run only the raw extraction step (main.py) for ONE video."""
    vi_dir = repo_dir / "videoImplement"
    subprocess.run(
        [str(python_exe), "main.py", "--input", str(video_path), "--no_raw_plot", "--no_preprocess"],
>>>>>>> Stashed changes
        cwd=str(vi_dir),
        check=True,
    )


<<<<<<< Updated upstream
class Handler(FileSystemEventHandler):
    def __init__(self, cfg):
        self.cfg = cfg
        self._busy = False

    def _maybe_process(self, path: Path):
        if self._busy:
            return
        if path.suffix.lower() not in VIDEO_EXTS:
            return

        self._busy = True
        try:
            print(f"[watch] detected: {path}")
            ok = wait_until_stable(path)
            if not ok:
                print(f"[watch] file never stabilized, skipping: {path}")
                return

            # Optional: move into a 'processing' folder to avoid duplicate triggers
            processing_dir = self.cfg.processing
            processing_dir.mkdir(parents=True, exist_ok=True)
            moved_path = processing_dir / path.name
            try:
                shutil.move(str(path), str(moved_path))
                path = moved_path
            except Exception:
                # If move fails (e.g. permissions), just process in place
                pass

            print(f"[watch] running pipeline on: {path}")
            run_pipeline(self.cfg.python, self.cfg.repo, path, self.cfg.out_root)
            print(f"[watch] done: {path}")

            # Archive
            if self.cfg.archive is not None:
                self.cfg.archive.mkdir(parents=True, exist_ok=True)
                shutil.move(str(path), str(self.cfg.archive / path.name))

        except subprocess.CalledProcessError as e:
            print(f"[watch] pipeline failed: {e}")
        finally:
            self._busy = False

    def on_created(self, event):
        if event.is_directory:
            return
        self._maybe_process(Path(event.src_path))

    def on_moved(self, event):
        if event.is_directory:
            return
        self._maybe_process(Path(event.dest_path))


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--inbox", required=True, help="Folder where videos arrive")
    p.add_argument("--repo", required=True, help="Path to eyeSSEF-main repo")
    p.add_argument("--python", default=None, help="Python executable (default: current)")
    p.add_argument("--out-root", default="data", help="Output root under videoImplement (default: data)")
    p.add_argument("--processing", default=None, help="Move incoming files here before processing")
    p.add_argument("--archive", default=None, help="Move processed files here")
    return p.parse_args()


def main():
    args = parse_args()

    class Cfg:
        pass

    cfg = Cfg()
    cfg.inbox = Path(args.inbox).expanduser().resolve()
    cfg.repo = Path(args.repo).expanduser().resolve()
    cfg.out_root = Path(args.out_root)
    cfg.python = Path(args.python).expanduser().resolve() if args.python else Path(os.sys.executable)
    cfg.processing = Path(args.processing).expanduser().resolve() if args.processing else (cfg.inbox / "_processing")
    cfg.archive = Path(args.archive).expanduser().resolve() if args.archive else (cfg.inbox / "_archive")

    if not cfg.inbox.exists():
        raise FileNotFoundError(f"Inbox folder does not exist: {cfg.inbox}")

    print(f"[watch] inbox: {cfg.inbox}")
    print(f"[watch] repo:  {cfg.repo}")

    event_handler = Handler(cfg)
    observer = Observer()
    observer.schedule(event_handler, str(cfg.inbox), recursive=False)
    observer.start()

=======
def _run_process_single_trial_show_plots(python_exe: Path, repo_dir: Path, trial_dir: Path) -> None:
    """Run process.py ONLY on one trial folder (contains raw.csv) and show plots."""
    vi_dir = repo_dir / "videoImplement"
    subprocess.run(
        [str(python_exe), "process.py", "--data", str(trial_dir)],
        cwd=str(vi_dir),
        check=True,
    )


def run_inbox_pipeline(cfg: "Config", inbox_video: Path) -> None:
    """End-to-end inbox workflow for ONE video.

    Implements exactly what you described:
    - take new video from inbox root
    - run main.py (raw only)
    - archive the video
    - run process.py only for that trial (and show plots)
    """
    processing_dir = (cfg.inbox / "_processing")
    processing_dir.mkdir(parents=True, exist_ok=True)

    # Move into _processing immediately to avoid re-triggering while we work
    processing_video = processing_dir / inbox_video.name
    shutil.move(str(inbox_video), str(processing_video))

    # 1) main.py raw extraction (only this file)
    _run_main_raw_only(cfg.python, cfg.repo, processing_video)

    # Determine the trial folder that main.py wrote into
    vi_dir = cfg.repo / "videoImplement"
    trial_dir = (vi_dir / "data" / processing_video.stem).resolve()
    if not trial_dir.exists():
        raise FileNotFoundError(f"Expected trial folder not found: {trial_dir}")

    # 2) archive the video BEFORE running process.py (as requested)
    if cfg.archive is not None:
        cfg.archive.mkdir(parents=True, exist_ok=True)
        shutil.move(str(processing_video), str(cfg.archive / processing_video.name))
    else:
        # If archive disabled, move back to inbox root to avoid leaving clutter in _processing
        shutil.move(str(processing_video), str(cfg.inbox / processing_video.name))

    # 3) process.py only for THIS trial dir; show interactive plots
    _run_process_single_trial_show_plots(cfg.python, cfg.repo, trial_dir)


@dataclass
class Config:
    inbox: Path
    archive: Optional[Path]
    repo: Path
    python: Path
    poll_interval: float = 1.0


def iter_ready_videos(inbox: Path) -> Iterable[Path]:
    """List candidate videos in inbox (excluding .part)."""
    for p in sorted(inbox.iterdir()):
        if not p.is_file():
            continue
        # only the inbox root; ignore reserved subfolders entirely
        if p.parent != inbox:
            continue
        if p.suffix.lower() not in VIDEO_EXTS:
            continue
        if p.name.endswith(".part"):
            continue
        yield p


def poll_loop(cfg: Config) -> None:
    print(f"[watch] Polling mode. Watching: {cfg.inbox}")
    busy = False
    while True:
        try:
            if not busy:
                for vid in iter_ready_videos(cfg.inbox):
                    # only process if stable (upload completed + flushed)
                    if not wait_until_stable(vid):
                        continue

                    busy = True
                    try:
                        print(f"[watch] running pipeline on: {vid.name}")
                        run_inbox_pipeline(cfg, vid)
                        print(f"[watch] done: {vid.name}")
                    except subprocess.CalledProcessError as e:
                        print(f"[watch] pipeline failed ({vid.name}): {e}")
                    finally:
                        busy = False
                    break
            time.sleep(cfg.poll_interval)
        except KeyboardInterrupt:
            print("\n[watch] stopped.")
            return


def watchdog_loop(cfg: Config) -> None:
    """Filesystem-event watcher. Falls back to polling if watchdog is unavailable."""
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except Exception:
        poll_loop(cfg)
        return

    class Handler(FileSystemEventHandler):
        def __init__(self) -> None:
            super().__init__()
            self.busy = False
            self.seen: Set[str] = set()

        def on_created(self, event):
            self._maybe_handle(event)

        def on_moved(self, event):
            self._maybe_handle(event)

        def _maybe_handle(self, event):
            if event.is_directory:
                return
            p = Path(getattr(event, "dest_path", None) or event.src_path)

            # Critical: only process files that are DIRECT children of the inbox root.
            # When we move a file into _archive/ or _processing/, watchdog will emit a move event.
            # Without this check, we'd re-trigger and loop on archived files.
            try:
                p = p.resolve()
            except Exception:
                pass
            if p.parent != cfg.inbox:
                return
            if p.name in RESERVED_SUBDIRS or p.parts and any(part in RESERVED_SUBDIRS for part in p.parts):
                return

            if p.suffix.lower() not in VIDEO_EXTS:
                return
            if p.name.endswith(".part"):
                return
            if p.name in self.seen:
                return

            # do not re-enter
            if self.busy:
                return

            # Wait for stability then run
            self.busy = True
            try:
                print(f"[watch] detected: {p.name}")
                ok = wait_until_stable(p)
                if not ok:
                    print(f"[watch] not stable / timeout: {p.name}")
                    return

                print(f"[watch] running pipeline on: {p.name}")
                run_inbox_pipeline(cfg, p)
                print(f"[watch] done: {p.name}")

                # Mark as processed (use filename key; the file itself may be moved)
                self.seen.add(p.name)
            except subprocess.CalledProcessError as e:
                print(f"[watch] pipeline failed ({p.name}): {e}")
            finally:
                self.busy = False

    print(f"[watch] watchdog mode. Watching: {cfg.inbox}")
    event_handler = Handler()
    observer = Observer()
    observer.schedule(event_handler, str(cfg.inbox), recursive=False)
    observer.start()
>>>>>>> Stashed changes
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
<<<<<<< Updated upstream
        observer.stop()
    observer.join()
=======
        print("\n[watch] stopped.")
    finally:
        observer.stop()
        observer.join()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inbox", default=os.path.expanduser("~/plr_inbox"),
                        help="Mac folder where Pi uploads videos (default: ~/plr_inbox)")
    parser.add_argument("--archive", default=os.path.expanduser("~/plr_inbox/_archive"),
                        help="Where to move processed videos. Set to '' to disable.")
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parent),
                        help="Path to the EyeSSEF repo root (default: this script's folder).")
    parser.add_argument("--python", default=sys.executable,
                        help="Python executable to run the pipeline (default: current python).")
    parser.add_argument("--mode", choices=["watchdog", "poll"], default="watchdog",
                        help="watchdog uses filesystem events if installed; poll uses periodic scanning.")
    parser.add_argument("--poll_interval", type=float, default=1.0,
                        help="Polling interval (seconds) when --mode poll or watchdog not installed.")
    args = parser.parse_args()

    inbox = Path(args.inbox).expanduser().resolve()
    repo = Path(args.repo).expanduser().resolve()
    py = Path(args.python).expanduser().resolve()

    if args.archive == "":
        archive = None
    else:
        archive = Path(args.archive).expanduser().resolve()

    if not inbox.exists():
        raise FileNotFoundError(f"Inbox folder not found: {inbox}")

    cfg = Config(inbox=inbox, archive=archive, repo=repo, python=py, poll_interval=args.poll_interval)

    if args.mode == "poll":
        poll_loop(cfg)
    else:
        watchdog_loop(cfg)
>>>>>>> Stashed changes


if __name__ == "__main__":
    main()
