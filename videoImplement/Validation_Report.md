# PLR Waveform Validity and “Non‑Artificiality” Verification

This project produces a pupillary light reflex (PLR) waveform from **video recordings of the eye**. Because a visually “reasonable” curve is *not* sufficient scientifically, we add quantitative checks that verify:

1. **Data provenance:** the waveform is based on frame‑wise measurements extracted from the eye video (not hand‑drawn or post‑hoc shaped).
2. **Processing conservatism:** the preprocessing pipeline removes noise/outliers without creating artificial physiology.
3. **Physiological plausibility:** the waveform dynamics are consistent with expected PLR time scales when stimulus timing is known.

This repository contains an automated validator (`scripts/validation/validity.py`) that computes these checks and saves report artifacts (CSV/JSON/plots) into every trial folder.

---

## 1) What the pipeline outputs (and why)

For each recording trial folder (e.g., `PLR_<User>_<Eye>_<Res>_<FPS>_<Trial>/`), the pipeline produces:

- `raw.csv` – **direct frame‑wise outputs from pupil detection** (timestamp, pupil diameter, confidence, and flags).
- `processed_interpolated.csv` – result after **Pass 1–4** (filtering + short‑gap interpolation) but **before smoothing**.
- `processed.csv` – final result after **Pass 6** (mild Savitzky–Golay smoothing).

The validator additionally writes:

- `validity_report.csv`, `validity_report.json`
- `validity_overlay.png` (raw vs interpolated vs smoothed)
- `validity_residuals.png` (smoothing distortion)
- `validity_psd.png` (frequency‑domain comparison)

---

## 2) Statistical evidence the waveform is grounded in real measurements

### 2.1 “Measurement preservation” check (raw → Pass 4)
**Claim:** Pass 1–4 should not change “good” measurements; it should mainly **remove** unreliable points and **fill short gaps**.

**How we test it:**
- Define “measured” frames as those with:
  - `diameter_mm` finite,
  - `confidence ≥ threshold` (default 0.75),
  - `is_bad_data == False`.
- Compute the correlation and RMSE between `raw.csv` and `processed_interpolated.csv` **only on measured frames**.

**Interpretation:**
- If correlation is near 1 and RMSE is near 0 on measured frames, then Pass 1–4 is **not fabricating a curve**; it is preserving what the video measurement produced.

### 2.2 Interpolation proportion and gap length
Interpolation can produce an overly “clean” curve if overused.

The validator reports:
- `% interpolated points` (frames that were not considered measured but were filled by Pass 4)
- `max interpolated gap` (in frames and seconds)

**Interpretation (practical):**
- Small interpolation percentages with **short gaps** (e.g., < 400 ms) are generally acceptable in pupillometry pipelines, because they mainly represent blink recovery or brief tracking loss.

---

## 3) Statistical evidence the pipeline did not make the waveform “too artificial”

### 3.1 Smoothing distortion (Pass 4 → Pass 6)
Savitzky–Golay smoothing should reduce jitter while preserving waveform shape.

**How we test it:**
- Compute:
  - correlation between `processed_interpolated.csv` and `processed.csv`
  - RMSE / MAE between the two curves
  - normalized RMSE (relative to signal range)
- Plot the point‑wise residual: `smooth − interpolated`.

**Interpretation:**
- High correlation + small residuals mean smoothing is acting as **noise suppression**, not shape fabrication.

### 3.2 Frequency‑domain (PSD) check
Noise typically occupies higher frequencies than the physiological PLR shape.

**How we test it:**
- Compute Welch power spectral density (PSD) for the interpolated curve and the smoothed curve.
- Report the **high‑frequency power ratio** (e.g., power above ~3 Hz).

**Interpretation:**
- A drop in high‑frequency power with minimal change in low‑frequency power indicates that smoothing removed **measurement jitter**, not the PLR signal.

---

## 4) Optional physiological plausibility checks (when stimulus timing is known)

If the recording protocol has fixed stimulus timing (e.g., `3 s pre‑stim → 0.25 s blue flash → 60 s rest → 0.25 s red flash → …`), the validator can estimate event‑level plausibility around assumed onsets (default: `[3.0, 63.25]` seconds):

- baseline (median diameter before onset)
- minimum diameter after onset
- constriction amplitude and relative amplitude
- approximate latency to 10% constriction

**Interpretation:**
- Values should be in a physiologically plausible range (latency typically on the order of a few hundred milliseconds; constriction reaching a minimum within ~1–2 seconds for many flash protocols, depending on stimulus).

> Important: This step is **not** a clinical diagnostic metric. It is a sanity check that the waveform behaves like a PLR response given known stimulus timing.

---

## 5) How to use (command line)

### Single trial
```bash
python3 process.py --data "videoImplement/data/PLR_<...>" --resolution 1920x1080 --fps 30 --no_show_plot
```

### Batch mode (process all trials in `data/`)
```bash
python3 process.py --data "videoImplement/data" --no_show_plot
```

After running, open each trial folder and include the generated validity artifacts in your Results/Appendix.

---

## 6) How to write this in your SSEF report (short template)

> To confirm that our PLR waveform was not visually plausible by coincidence and was not artificially shaped by preprocessing, we quantified waveform fidelity at multiple stages. First, we compared the raw frame‑wise pupil diameter estimates (from video‑based detection) with the Pass‑4 interpolated trace on frames classified as valid measurements (high confidence and not flagged). The near‑identity of these values demonstrates that Pass 1–4 mainly removes unreliable samples and does not modify retained measurements. Second, we quantified the effect of smoothing (Pass 6) by computing correlation and error metrics between the interpolated and smoothed traces and by analysing the smoothing residual distribution. Third, we evaluated whether smoothing primarily removed high‑frequency jitter rather than physiological structure using a Welch power spectral density comparison. Together, these tests provide statistical evidence that the final PLR waveform is grounded in the video measurements and that preprocessing is conservative rather than waveform‑generating.

---

## References (suggested)

- Steinhauer, S. R., Siegle, G. J., Condray, R., & Pless, M. (2022). *Publication guidelines and recommendations for pupillary measurement in Psychophysiology*. Psychophysiology.
- Santini, T., et al. (2017). *PuRe: An open‑source tool for pupillometry*. (PuRe)
- Santini, T., et al. (2018). *PuReST: Pupillometry preprocessing and analysis*. (PuReST)
- Zandi, A. S., et al. (2021). *PupilEXT: open platform for pupillometry (preprocessing/validation concepts)*.
- Rukmini, A. V., et al. (2019). *Chromatic pupillometry methods for assessing photoreceptor health*.
- Adhikari, P., et al. (2015). *The post‑illumination pupil response (PIPR)*.
