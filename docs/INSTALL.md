# Installation

This guide is written for someone starting from **zero** (no Python, no pupillometry libraries).

## Supported platforms

- **Windows 10/11** (recommended for easiest setup)
- **macOS** (Intel or Apple Silicon)
- **Linux** (Ubuntu/Debian recommended)
- **Raspberry Pi OS** (works, but PyPupilEXT wheels may not be available; see notes below)

## 0) Install Python

EyeSSEF is tested best with **Python 3.10** because PyPupilEXT primarily ships wheels for specific Python versions.

### Windows
1. Download Python 3.10 from python.org.
2. During install, tick **“Add Python to PATH”**.
3. Open *Command Prompt* and verify:
   ```bash
   python --version
   ```

### macOS
- Install with Homebrew:
  ```bash
  brew install python@3.10
  python3.10 --version
  ```

### Ubuntu / Debian
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip
python3 --version
```

---

## 1) Get this repository

```bash
git clone <YOUR_REPO_URL>
cd EyeSSEF
```

If you downloaded a ZIP instead, unzip it and `cd` into the folder.

---

## 2) Create a virtual environment

### Windows (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

---

## 3) Install base Python dependencies

From the repo root:

```bash
pip install -r requirements.txt
```

This installs:
- OpenCV (`opencv-python`) for video/frame handling
- NumPy / Pandas for data work
- SciPy for Savitzky–Golay smoothing
- Matplotlib for plots

---

## 4) Install PyPupilEXT (required)

EyeSSEF uses **PyPupilEXT** (`pypupilext`) to fit an ellipse and estimate pupil diameter (PuReST).

### Option A (recommended): install a wheel from PyPupilEXT releases
1. Go to the **PyPupilEXT GitHub Releases** page.
2. Download the correct `.whl` file for your:
   - operating system
   - CPU architecture
   - Python version (recommended: **cp310**)
3. Install it:
   ```bash
   pip install /path/to/PyPupilEXT-*.whl
   ```

### Option B: build PyPupilEXT from source
If there is no wheel for your platform, follow the “Build and install from source” instructions in the PyPupilEXT repository.

---

## 5) Quick installation test

Run:

```bash
python -c "import cv2, numpy, pandas, scipy, matplotlib; import pypupilext; print('OK')"
```

If this prints `OK`, you’re ready.

---

## Raspberry Pi notes

- Installing **OpenCV + SciPy** via pip on Raspberry Pi can be slow and sometimes fails (native build).
- If you want to run processing on the Pi, prefer system packages:
  ```bash
  sudo apt-get install -y python3-opencv python3-numpy python3-pandas python3-scipy python3-matplotlib
  ```
- PyPupilEXT may not have a ready-made Raspberry Pi wheel. In that case you must build it from source (and that can take a long time).

For most teams, the easiest approach is:
1) record on the Pi
2) transfer videos to a laptop/desktop
3) process on the laptop/desktop
