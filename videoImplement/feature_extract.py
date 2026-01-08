
"""
Feature extraction for eyeSSEF (PLR + PIPR metrics) from a single representative waveform.

Input:
- A processed waveform CSV produced by your pipeline (recommended: processed_avg.csv in *_AVG folders).
  Required columns: timestamp (s), diameter_mm (mm)

Output:
- metrics_summary.csv in videoImplement/data/
- per-participant plots and per-folder metrics.csv

This script implements the PLR metrics you listed and a Steinhauer-style late PIPR metric:
- Baseline pupil diameter (BPD): average prestimulus period (we compute 1 s and 10 s variants)
- Transient PLR: peak change 180–500 ms after light onset
- Constriction velocity: stimulus gradient (slope) of a linear model near onset
- Peak constriction amplitude: minimum pupil size, expressed as % baseline
- PIPR (10–30 s post-stimulus): mean baseline-corrected constriction in the 10–30 s window (unitless)
- Net PIPR: by default we report **Blue − Red** using the above PIPR metric (unitless).
  (We also compute the opposite convention, Red − Blue, for cross-checking.)

Because your protocol has TWO stimuli (blue then red) in the same recording, we compute metrics separately for each.

Notes for your protocol:
- Blue onset nominally occurs 3.0 s after camera start.
- Stimulus duration is 0.25 s (offset = onset + 0.25 s).
- Red onset nominally occurs 63.25 s after camera start: 3.0 + 0.25 + 60.0.

We keep the code robust by:
- Using nominal times as defaults (good if your stimulus controller timing is stable)
- Optionally "refining" onset by searching for the start of the constriction near the nominal time.
"""

from __future__ import annotations

import os
import re
import math
from dataclasses import dataclass
from typing import Dict, Tuple, Optional, List

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

from scripts.others.util import dprint


@dataclass
class Protocol:
    blue_onset_s: float = 3.0
    stim_dur_s: float = 0.25
    isi_s: float = 60.0
    refine_onset: bool = True  # set False to use nominal onsets only
    # red onset = blue onset + stim_dur + isi
    def red_onset_s(self) -> float:
        return self.blue_onset_s + self.stim_dur_s + self.isi_s

    # windows
    baseline_short_s: float = 1.0      # your requested baseline definition
    baseline_long_s: float = 10.0      # Adhikari BPD definition uses 10 s prestimulus
    transient_start_s: float = 0.180   # 180 ms
    transient_end_s: float = 0.500     # 500 ms
    peak_search_s: float = 5.0         # look for minimum within 5 s after onset
    # Late PIPR window (Steinhauer-style): 10–30 s post *stimulus onset* (pulse is short so onset/offset difference is negligible)
    pipr_start_s: float = 10.0
    pipr_end_s: float = 30.0

    # Legacy names kept for backward compatibility (not used by default anymore)
    auc_late_start_s: float = 10.0
    auc_late_end_s: float = 30.0
    plateau_start_s: float = 10.0
    plateau_end_s: float = 30.0


def _infer_dt_seconds(t: np.ndarray) -> float:
    """Infer sampling interval from timestamps."""
    diffs = np.diff(t)
    diffs = diffs[np.isfinite(diffs)]
    if len(diffs) == 0:
        return float("nan")
    return float(np.median(diffs))


def _window_mask(t: np.ndarray, t0: float, t1: float) -> np.ndarray:
    return (t >= t0) & (t < t1)


def _nanmean_or_nan(x: np.ndarray) -> float:
    x = x[np.isfinite(x)]
    return float(np.mean(x)) if len(x) else float("nan")


def _linear_slope(t: np.ndarray, y: np.ndarray) -> float:
    """Least-squares slope of y = a*t + b."""
    mask = np.isfinite(t) & np.isfinite(y)
    t2, y2 = t[mask], y[mask]
    if len(t2) < 2:
        return float("nan")
    t_center = t2 - np.mean(t2)
    denom = np.sum(t_center ** 2)
    if denom == 0:
        return float("nan")
    slope = np.sum(t_center * (y2 - np.mean(y2))) / denom
    return float(slope)


def refine_onset_by_constriction_start(
    t: np.ndarray,
    y: np.ndarray,
    nominal_onset: float,
    search_radius_s: float = 2.0,
) -> float:
    """
    Optional refinement: uses nominal onset as anchor, then tries to detect where
    the pupil begins to constrict.

    Strategy:
    - Find the local minimum in [nominal_onset, nominal_onset + peak_search] (the constriction trough)
    - Walk backward from that trough until the derivative becomes near-zero (baseline-like),
      then pick the next index where derivative turns strongly negative.

    If anything fails, we return nominal_onset.
    """
    # guard
    if not np.isfinite(nominal_onset):
        return nominal_onset

    dt = _infer_dt_seconds(t)
    if not np.isfinite(dt) or dt <= 0:
        return nominal_onset

    # search region
    start = nominal_onset - search_radius_s
    end = nominal_onset + search_radius_s + 5.0
    mask = _window_mask(t, max(t[0], start), min(t[-1], end))
    if mask.sum() < 10:
        return nominal_onset

    idxs = np.where(mask)[0]
    # trough after nominal onset
    post = idxs[t[idxs] >= nominal_onset]
    if len(post) < 5:
        return nominal_onset

    trough_idx = post[np.nanargmin(y[post])]
    # derivative
    dy = np.gradient(y, dt)
    # baseline noise estimate from 1 s before nominal onset
    base_mask = _window_mask(t, nominal_onset - 1.0, nominal_onset)
    base_dy = dy[base_mask & np.isfinite(dy)]
    if len(base_dy) < 5:
        thr = -0.2  # mm/s fallback
    else:
        thr = -3.0 * np.std(base_dy)  # 3-sigma negative slope threshold
        thr = min(thr, -0.15)         # don't make it too close to zero

    # walk backwards to find "start of constriction"
    i = trough_idx
    while i > 1 and t[i] > nominal_onset - search_radius_s:
        if np.isfinite(dy[i]) and dy[i] < thr:
            # candidate: dy is strongly negative here, check that just before was closer to baseline
            if np.isfinite(dy[i - 1]) and dy[i - 1] > thr * 0.5:
                return float(t[i])
        i -= 1

    return nominal_onset


def compute_metrics_for_stimulus(
    df: pd.DataFrame,
    onset_s: float,
    stim_dur_s: float,
    label: str,
    protocol: Protocol,
) -> Dict[str, float]:
    """
    Compute PLR + PIPR metrics for a given stimulus onset.
    All calculations are done on diameter_mm.

    Returns a dict of metrics (float; NaN if unavailable).
    """
    t = df["timestamp"].to_numpy(float)
    y = df["diameter_mm"].to_numpy(float)

    # Optionally refine onset (useful if camera start is slightly offset).
    refined_onset = refine_onset_by_constriction_start(t, y, onset_s) if protocol.refine_onset else onset_s

    offset_s = refined_onset + stim_dur_s

    # Baselines
    b_short = _nanmean_or_nan(y[_window_mask(t, refined_onset - protocol.baseline_short_s, refined_onset)])
    b_long = _nanmean_or_nan(y[_window_mask(t, refined_onset - protocol.baseline_long_s, refined_onset)])

    # If 10s baseline not available, fall back to 1s (but keep both outputs)
    if not np.isfinite(b_long):
        b_long = b_short

    # Transient PLR (% baseline): peak change in 180–500 ms post onset
    w_tr = _window_mask(t, refined_onset + protocol.transient_start_s, refined_onset + protocol.transient_end_s)
    # constriction fraction = (B - y)/B
    tr_frac = (b_short - y[w_tr]) / b_short if np.isfinite(b_short) and b_short != 0 else np.array([])
    transient_plr_pct = float(np.nanmax(tr_frac) * 100.0) if len(tr_frac) else float("nan")
    transient_plr_mm = float(np.nanmax(b_short - y[w_tr])) if len(tr_frac) else float("nan")

    # Constriction velocity (mm/s):
    # Papers sometimes report a single "constriction velocity" value. Practically,
    # two common implementations are:
    #   (a) MAX constriction velocity = most negative dy/dt (very sensitive to single-frame noise)
    #   (b) a robust proxy (e.g., 5th percentile of dy/dt) to reduce one-frame spikes
    dt = _infer_dt_seconds(t)
    constr_vel_mm_s_min = float("nan")
    constr_vel_mm_s_p5 = float("nan")
    constr_vel_abs_mm_s_p5 = float("nan")
    if np.isfinite(dt) and np.any(w_tr):
        dy = np.gradient(y, dt)  # mm/s
        dy_seg = dy[w_tr]
        dy_seg = dy_seg[np.isfinite(dy_seg)]
        if len(dy_seg):
            constr_vel_mm_s_min = float(np.min(dy_seg))
            constr_vel_mm_s_p5 = float(np.percentile(dy_seg, 5))  # robust, still negative
            constr_vel_abs_mm_s_p5 = abs(constr_vel_mm_s_p5)
    # We expose both; by default you can use the robust p5 value for reporting.
    constr_vel_mm_s = constr_vel_mm_s_p5
    constr_vel_abs_mm_s = constr_vel_abs_mm_s_p5

    # For transparency, we also keep the linear-fit slope over the same window (may differ if curve is not linear).
    constr_vel_linear_fit_mm_s = _linear_slope(t[w_tr], y[w_tr])
# Peak constriction (minimum pupil size) within first 5s after onset (protocol adapted for short pulses)
    w_peak = _window_mask(t, refined_onset, refined_onset + protocol.peak_search_s)
    min_mm = float(np.nanmin(y[w_peak])) if np.any(w_peak) else float("nan")
    min_pct_baseline = float((min_mm / b_short) * 100.0) if np.isfinite(min_mm) and np.isfinite(b_short) and b_short != 0 else float("nan")
    peak_constriction_amp_pct = 100.0 - min_pct_baseline if np.isfinite(min_pct_baseline) else float("nan")  # amplitude as % reduction

    # Late PIPR (Steinhauer-style): 10–30 s post-stimulus
    #
    # Your latest requirement: PIPR should be the *difference between baseline and the blue waveform*,
    # and it should not go negative.
    #
    # Why your previous AUC could be negative:
    # - The Adhikari-style AUC computes (BPD − pupil)/BPD and then sums it over time.
    # - If the pupil trace rises above baseline in that window (APD > BPD), the signed formula becomes negative.
    #
    # To match the “baseline-corrected” visualization (green diagonal lines) used in many standards figures,
    # we apply a simple **local drift correction** across the 10–30 s window:
    #   1) Work in % baseline (normalized to the 1 s baseline you requested)
    #   2) Build a straight baseline line between the trace value at 10 s and at 30 s
    #   3) Measure only the constriction BELOW that line (clip negatives to 0)
    #
    # This makes the PIPR metric:
    #   - unitless (fraction of baseline)
    #   - non-negative by construction
    #   - visually consistent with the shaded area you expect
    pipr_t0 = refined_onset + protocol.pipr_start_s
    pipr_t1 = refined_onset + protocol.pipr_end_s
    w_pipr = _window_mask(t, pipr_t0, pipr_t1)

    pipr_mean_unitless = float('nan')
    pipr_auc_unitless_sum = float('nan')
    pipr_auc_unitless_seconds = float('nan')

    if np.isfinite(b_short) and b_short != 0 and np.any(w_pipr):
        # percent baseline trace
        y_pct = (y / b_short) * 100.0

        # interpolation requires finite points
        mfin = np.isfinite(t) & np.isfinite(y_pct)
        t_f = t[mfin]
        y_pct_f = y_pct[mfin]

        if len(t_f) >= 2 and pipr_t1 > pipr_t0:
            # endpoints of the drift line (in % baseline)
            y0 = float(np.interp(pipr_t0, t_f, y_pct_f))
            y1 = float(np.interp(pipr_t1, t_f, y_pct_f))

            tw = t[w_pipr]
            yw = y_pct[w_pipr]
            rel = (tw - pipr_t0) / (pipr_t1 - pipr_t0)
            drift_line = y0 + (y1 - y0) * rel

            # only count constriction below the drift line
            diff_pct = np.clip(drift_line - yw, 0.0, None)
            diff_unitless = diff_pct / 100.0  # unitless fraction of baseline

            pipr_mean_unitless = float(np.nanmean(diff_unitless))
            pipr_auc_unitless_sum = float(np.nansum(diff_unitless))

            dt = _infer_dt_seconds(t)
            if np.isfinite(dt):
                pipr_auc_unitless_seconds = float(pipr_auc_unitless_sum * dt)

    # Package metrics
    out = {
        f"{label}_onset_s_nominal": float(onset_s),
        f"{label}_onset_s_used": float(refined_onset),
        f"{label}_offset_s_used": float(offset_s),

        f"{label}_baseline_1s_mm": float(b_short),
        f"{label}_baseline_10s_mm_BPD": float(b_long),

        f"{label}_transientPLR_pct": float(transient_plr_pct),
        f"{label}_transientPLR_mm": float(transient_plr_mm),

        f"{label}_constriction_velocity_mm_s": float(constr_vel_mm_s),
        f"{label}_constriction_velocity_abs_mm_s": float(constr_vel_abs_mm_s),
        f"{label}_constriction_velocity_mm_s_min": float(constr_vel_mm_s_min),
        f"{label}_constriction_velocity_mm_s_p5": float(constr_vel_mm_s_p5),
        f"{label}_constriction_velocity_linear_fit_mm_s": float(constr_vel_linear_fit_mm_s),

        # "Peak constriction amplitude" in Adhikari is "minimum pupil size, % baseline"
        f"{label}_min_pupil_pct_baseline": float(min_pct_baseline),
        f"{label}_peak_constriction_amp_pct": float(peak_constriction_amp_pct),
        f"{label}_PIPR_10_30_mean_unitless": float(pipr_mean_unitless),
        f"{label}_PIPR_10_30_auc_unitless_sum": float(pipr_auc_unitless_sum),
        f"{label}_PIPR_10_30_auc_unitless_seconds": float(pipr_auc_unitless_seconds),
    }
    return out


def plot_aligned(
    df: pd.DataFrame,
    onset_s_used: float,
    stim_dur_s: float,
    baseline_mm: float,
    title: str,
    out_path: str,
    protocol: Protocol,
    show_plot: bool = False,
) -> None:
    """Save an aligned plot similar to standards figures (percent baseline + mm)."""
    t = df["timestamp"].to_numpy(float)
    y = df["diameter_mm"].to_numpy(float)

    rel_t = t - onset_s_used
    y_pct = (y / baseline_mm) * 100.0 if np.isfinite(baseline_mm) and baseline_mm != 0 else np.full_like(y, np.nan)

    fig, ax1 = plt.subplots(figsize=(9, 4.5))
    ax1.plot(rel_t, y_pct)
    ax1.set_xlabel("Time (s) relative to stimulus onset")
    ax1.set_ylabel("Pupil diameter (% baseline)")
    ax1.axvline(0, linestyle="--")
    ax1.axvspan(0, stim_dur_s, alpha=0.2)

    # annotate key windows
    ax1.axvspan(protocol.transient_start_s, protocol.transient_end_s, alpha=0.15)
    ax1.axvspan(protocol.pipr_start_s, protocol.pipr_end_s, alpha=0.08)

    # mm axis
    ax2 = ax1.twinx()
    ax2.plot(rel_t, y, alpha=0.0)  # invisible; axis scale only
    ax2.set_ylabel("Pupil diameter (mm)")

    ax1.set_title(title)
    ax1.set_xlim(rel_t.min(), rel_t.max())
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    if show_plot:
        plt.show()
    plt.close(fig)


def _pretty_table_from_row(row: Dict[str, float]) -> pd.DataFrame:
    """Create a compact table for quick visual verification (rounded by caller).

    Rows:
      - Blue
      - Red
      - Net (Blue-Red)

    Columns include the metrics you asked for.
    """
    blue = {
        "Baseline (mm)": row.get("blue_baseline_1s_mm", np.nan),
        "Transient PLR (%)": row.get("blue_transientPLR_pct", np.nan),
        "Constriction vel (mm/s)": row.get("blue_constriction_velocity_mm_s", np.nan),
        "Peak constriction (%)": row.get("blue_peak_constriction_amp_pct", np.nan),
        "PIPR (10–30s, unitless)": row.get("blue_PIPR_10_30_mean_unitless", np.nan),
        "Net PIPR (Blue−Red)": np.nan,
        "Net PIPR (Red−Blue)": np.nan,
    }
    red = {
        "Baseline (mm)": row.get("red_baseline_1s_mm", np.nan),
        "Transient PLR (%)": row.get("red_transientPLR_pct", np.nan),
        "Constriction vel (mm/s)": row.get("red_constriction_velocity_mm_s", np.nan),
        "Peak constriction (%)": row.get("red_peak_constriction_amp_pct", np.nan),
        "PIPR (10–30s, unitless)": row.get("red_PIPR_10_30_mean_unitless", np.nan),
        "Net PIPR (Blue−Red)": np.nan,
        "Net PIPR (Red−Blue)": np.nan,
    }
    net_blue_minus_red = row.get("netPIPR_PIPR_10_30_mean_unitless_blue_minus_red", np.nan)
    net_red_minus_blue = row.get("netPIPR_PIPR_10_30_mean_unitless_red_minus_blue", np.nan)
    net = {
        "Baseline (mm)": np.nan,
        "Transient PLR (%)": np.nan,
        "Constriction vel (mm/s)": np.nan,
        "Peak constriction (%)": np.nan,
        "PIPR (10–30s, unitless)": np.nan,
        "Net PIPR (Blue−Red)": net_blue_minus_red,
        "Net PIPR (Red−Blue)": net_red_minus_blue,
    }
    return pd.DataFrame([blue, red, net], index=["Blue", "Red", "Net (Blue-Red)"])


def _print_pretty_table(table_df: pd.DataFrame) -> None:
    """Print the compact metrics table (rounded) with light ANSI coloring in terminal."""
    # ANSI helpers (safe: if terminal doesn't support, it will just show raw text)
    BLUE = "\033[94m"
    RED = "\033[91m"
    YELL = "\033[93m"
    RESET = "\033[0m"

    # Convert to string to safely inject ANSI color codes without dtype warnings.
    dfp = table_df.copy().astype(str)

    # Color the PIPR values for blue/red and the primary Net PIPR (Blue−Red) cell
    try:
        dfp.loc["Blue", "PIPR (10–30s, unitless)"] = f"{BLUE}{dfp.loc['Blue','PIPR (10–30s, unitless)']}{RESET}"
        dfp.loc["Red", "PIPR (10–30s, unitless)"] = f"{RED}{dfp.loc['Red','PIPR (10–30s, unitless)']}{RESET}"
        dfp.loc["Net (Blue-Red)", "Net PIPR (Blue−Red)"] = f"{YELL}{dfp.loc['Net (Blue-Red)','Net PIPR (Blue−Red)']}{RESET}"
    except Exception:
        pass

    dprint("Metrics (rounded to 3 d.p.):")
    # Use pandas string repr for a clean table
    print(dfp.to_string())


def plot_overlay_with_table(
    df: pd.DataFrame,
    row: Dict[str, float],
    protocol: Protocol,
    out_path: str,
    show_plot: bool = False,
) -> None:
    """Overlay BLUE and RED aligned waveforms (percent baseline) + show a metrics table.

    This is meant to look similar to standards figures: both traces share the same
    time axis (relative to onset) so you can visually compare PLR and late PIPR.

    - We align BLUE to its onset and RED to its own onset; then overlay both on the
      same *relative* timeline.
    - We normalize each trace to its own 1-second baseline (as you requested).
    - We highlight:
        * stimulus interval (0–stim_dur)
        * transient PLR window (180–500 ms)
        * late PIPR window (10–30 s after onset)
        * net PIPR area (fill between traces within late window)
    """
    t = df["timestamp"].to_numpy(float)
    y = df["diameter_mm"].to_numpy(float)

    blue_on = float(row["blue_onset_s_used"])
    red_on = float(row["red_onset_s_used"])
    stim = float(protocol.stim_dur_s)

    # segments (relative time)
    def seg(onset: float, baseline_mm: float, max_t: float = 60.0):
        rel = t - onset
        mask = (rel >= -1.0) & (rel <= max_t)
        rel2 = rel[mask]
        y2 = y[mask]
        y_pct = (y2 / baseline_mm) * 100.0 if np.isfinite(baseline_mm) and baseline_mm != 0 else np.full_like(y2, np.nan)
        return rel2, y_pct

    bx = float(row.get("blue_baseline_1s_mm", np.nan))
    rx = float(row.get("red_baseline_1s_mm", np.nan))
    x_b, y_b = seg(blue_on, bx)
    x_r, y_r = seg(red_on, rx)

    # Reference baseline for the secondary mm axis (approx) – for readability only.
    baseline_ref = float(np.nanmean([bx, rx])) if np.isfinite(bx) or np.isfinite(rx) else np.nan

    # Build the verification table
    table_df = _pretty_table_from_row(row).round(3)

    fig = plt.figure(figsize=(11, 6.5))
    gs = GridSpec(2, 1, height_ratios=[3.3, 1.2], hspace=0.25)

    ax = fig.add_subplot(gs[0, 0])
    ax.plot(x_b, y_b, label="Blue stimulus", linewidth=2, color="tab:blue")
    ax.plot(x_r, y_r, label="Red stimulus", linewidth=2, color="tab:red")
    ax.set_xlabel("Time (s) relative to stimulus onset")
    ax.set_ylabel("Pupil diameter (% baseline)")
    ax.axhline(100.0, linestyle="--", linewidth=1)
    ax.axvline(0.0, linestyle="--", linewidth=1)

    # stimulus bar
    ax.axvspan(0.0, stim, alpha=0.18, color="0.6")

    # transient PLR window
    ax.axvspan(protocol.transient_start_s, protocol.transient_end_s, alpha=0.12, color="tab:green")

    # late PIPR window (relative to onset)
    late0 = protocol.pipr_start_s
    late1 = protocol.pipr_end_s
    ax.axvspan(late0, late1, alpha=0.08, color="0.85")

    # Visual verification shading inside the late window:
    # - Blue PIPR: area between baseline (100%) and the BLUE trace, only where BLUE < 100%
    # - Red  PIPR: area between baseline (100%) and the RED  trace, only where RED  < 100%
    # - Net PIPR: fill between RED and BLUE (yellow), matching the “solid yellow” region in many papers
    #
    # Note: If a trace rises above baseline in the late window, we do NOT count that as negative AUC.
    # The clipped AUC calculation (see compute_metrics_for_stimulus) aligns with this visualization.

    try:
        if len(x_b) > 5 and len(x_r) > 5:
            x_common = np.linspace(late0, late1, 600)
            yb_i = np.interp(x_common, x_b, y_b)
            yr_i = np.interp(x_common, x_r, y_r)

            # Steinhauer-style baseline correction line (green diagonal) for EACH trace
            # Build a line between the trace at 10 s and at 30 s (in % baseline)
            yb0 = float(np.interp(late0, x_b, y_b))
            yb1 = float(np.interp(late1, x_b, y_b))
            yr0 = float(np.interp(late0, x_r, y_r))
            yr1 = float(np.interp(late1, x_r, y_r))

            line_b = yb0 + (yb1 - yb0) * (x_common - late0) / (late1 - late0)
            line_r = yr0 + (yr1 - yr0) * (x_common - late0) / (late1 - late0)

            # Draw the baseline correction lines (green diagonal lines)
            ax.plot([late0, late1], [yb0, yb1], color='tab:green', linewidth=1)
            ax.plot([late0, late1], [yr0, yr1], color='tab:green', linewidth=1, alpha=0.7)

            # Shade PIPR area: only where trace is below its drift line (non-negative by definition)
            ax.fill_between(
                x_common,
                yb_i,
                line_b,
                where=(yb_i < line_b),
                alpha=0.12,
                color='tab:blue',
                interpolate=True,
            )
            ax.fill_between(
                x_common,
                yr_i,
                line_r,
                where=(yr_i < line_r),
                alpha=0.12,
                color='tab:red',
                interpolate=True,
            )

            # Net region between RED and BLUE (yellow), matching the standards-style visualization
            ax.fill_between(x_common, yb_i, yr_i, alpha=0.30, color="#F5D547")
    except Exception:
        pass

    ax.set_xlim(-1.0, 60.0)
    ax.legend(loc="upper right")

    # Secondary axis in mm (approx; uses mean baseline)
    if np.isfinite(baseline_ref) and baseline_ref != 0:
        def pct_to_mm(p):
            return (np.array(p) / 100.0) * baseline_ref

        def mm_to_pct(m):
            return (np.array(m) / baseline_ref) * 100.0

        sec = ax.secondary_yaxis('right', functions=(pct_to_mm, mm_to_pct))
        sec.set_ylabel("Pupil diameter (mm) (approx)")

    # Title + key numbers (we show Blue−Red as the primary convention)
    net_pipr = float(table_df.loc["Net (Blue-Red)", "Net PIPR (Blue−Red)"])
    ax.set_title(f"Overlay aligned responses (Blue vs Red) | Net PIPR (Blue−Red) = {net_pipr:.3f}")

    # Table subplot
    ax_t = fig.add_subplot(gs[1, 0])
    ax_t.axis("off")

    cell_text = table_df.astype(object).values.tolist()
    col_labels = list(table_df.columns)
    row_labels = list(table_df.index)

    tab = ax_t.table(
        cellText=cell_text,
        rowLabels=row_labels,
        colLabels=col_labels,
        cellLoc="center",
        loc="center",
    )
    tab.auto_set_font_size(False)
    tab.set_fontsize(10)
    tab.scale(1, 1.3)

    # Color key cells: PIPR for blue/red, Net PIPR cell for net row
    # Note: Matplotlib table indices include header row at (0, ...).
    try:
        auc_col = col_labels.index("PIPR (10–30s, unitless)")
        net_col = col_labels.index("Net PIPR (Blue−Red)")
        alt_net_col = col_labels.index("Net PIPR (Red−Blue)")

        # Blue row is 1, Red row is 2, Net row is 3 (because header row is 0)
        tab[(1, auc_col)].set_facecolor((0.80, 0.88, 1.00))  # light blue
        tab[(2, auc_col)].set_facecolor((1.00, 0.85, 0.85))  # light red
        tab[(3, net_col)].set_facecolor((1.00, 0.95, 0.70))  # light yellow (primary)
        tab[(3, alt_net_col)].set_facecolor((0.92, 0.92, 0.92))  # light grey (alt convention)
    except Exception:
        pass

    fig.tight_layout()
    fig.savefig(out_path, dpi=220)
    if show_plot:
        dprint("Close the plot window to continue...")
        plt.show()
    plt.close(fig)


FOLDER_RE = re.compile(
    r"^PLR_(?P<user>[^_]+)_(?P<eye>[LR])_(?P<res>\d+x\d+)_(?P<fps>\d+)_AVG$"
)


def process_avg_folder(avg_folder: str, protocol: Protocol, show_plots: bool = False) -> Optional[pd.DataFrame]:
    """Compute metrics for one *_AVG folder and save outputs inside it."""
    name = os.path.basename(avg_folder.rstrip("/"))
    m = FOLDER_RE.match(name)
    if not m:
        return None

    user = m.group("user")
    eye = m.group("eye")
    res = m.group("res")
    fps = int(m.group("fps"))

    csv_path = os.path.join(avg_folder, "processed_avg.csv")
    if not os.path.exists(csv_path):
        dprint(f"[skip] No processed_avg.csv found in {avg_folder}")
        return None

    df = pd.read_csv(csv_path)
    if "timestamp" not in df.columns or "diameter_mm" not in df.columns:
        dprint(f"[skip] Missing required columns in {csv_path}")
        return None

    # Compute metrics for blue and red
    blue_onset = protocol.blue_onset_s
    red_onset = protocol.red_onset_s()

    metrics_blue = compute_metrics_for_stimulus(df, blue_onset, protocol.stim_dur_s, "blue", protocol)
    metrics_red  = compute_metrics_for_stimulus(df, red_onset,  protocol.stim_dur_s, "red",  protocol)

    # Net PIPR (late 10–30 s window): we compute BOTH conventions and store both.
    #
    # IMPORTANT SIGN NOTE:
    # Many figures/papers show pupil diameter as "% baseline" (so a *smaller* value means a *stronger* response).
    # In that convention, authors often write net as (control − test) = (red − blue) in terms of pupil diameter.
    #
    # Our "PIPR (10–30 s)" metric is defined as a *difference* (baseline-corrected line minus pupil diameter),
    # so "Blue − Red" in our metric is mathematically equivalent to "Red − Blue" in diameter units.
    #
    # For consistency across your plots/tables (and to make the expected net value positive), we report
    # Blue − Red as the PRIMARY value.
    net_pipr_blue_minus_red = metrics_blue["blue_PIPR_10_30_mean_unitless"] - metrics_red["red_PIPR_10_30_mean_unitless"]
    net_pipr_red_minus_blue = -net_pipr_blue_minus_red

    row = {
        "user": user,
        "eye": eye,
        "resolution": res,
        "fps": fps,
        **metrics_blue,
        **metrics_red,
        "netPIPR_PIPR_10_30_mean_unitless_blue_minus_red": float(net_pipr_blue_minus_red),
        "netPIPR_PIPR_10_30_mean_unitless_red_minus_blue": float(net_pipr_red_minus_blue),
    }

    # Save per-folder metrics.csv
    out_metrics = os.path.join(avg_folder, "metrics.csv")
    pd.DataFrame([row]).to_csv(out_metrics, index=False)

    # Save a compact, user-facing table for quick verification
    pretty_tbl = _pretty_table_from_row(row).round(3)
    pretty_tbl.to_csv(os.path.join(avg_folder, "metrics_table.csv"))
    _print_pretty_table(pretty_tbl)

    # Save per-stimulus aligned plots (PNG only; interactive display handled by the overlay figure)
    plot_aligned(
        df,
        onset_s_used=row["blue_onset_s_used"],
        stim_dur_s=protocol.stim_dur_s,
        baseline_mm=row["blue_baseline_1s_mm"],
        title=f"{user} {eye} BLUE aligned (res={res}, fps={fps})",
        out_path=os.path.join(avg_folder, "alignedBlue.png"),
        protocol=protocol,
        show_plot=False,
    )
    plot_aligned(
        df,
        onset_s_used=row["red_onset_s_used"],
        stim_dur_s=protocol.stim_dur_s,
        baseline_mm=row["red_baseline_1s_mm"],
        title=f"{user} {eye} RED aligned (res={res}, fps={fps})",
        out_path=os.path.join(avg_folder, "alignedRed.png"),
        protocol=protocol,
        show_plot=False,
    )

    # NEW: overlay plot + embedded metrics table (the format you asked for)
    plot_overlay_with_table(
        df,
        row=row,
        protocol=protocol,
        out_path=os.path.join(avg_folder, "overlayBlueRed_metrics.png"),
        show_plot=show_plots,
    )

    dprint(f"[ok] Saved metrics + aligned plots in {avg_folder}")
    return pd.DataFrame([row])


def run_feature_extraction(data_dir: str, protocol: Protocol, show_plots: bool = False) -> pd.DataFrame:
    """
    Run over all *_AVG folders in the data_dir and return a summary dataframe.
    """
    rows: List[pd.DataFrame] = []
    for name in sorted(os.listdir(data_dir)):
        if not name.endswith("_AVG"):
            continue
        folder = os.path.join(data_dir, name)
        if not os.path.isdir(folder):
            continue
        df_row = process_avg_folder(folder, protocol, show_plots=show_plots)
        if df_row is not None:
            rows.append(df_row)

    if rows:
        summary = pd.concat(rows, ignore_index=True)
    else:
        summary = pd.DataFrame()

    out_path = os.path.join(data_dir, "metrics_summary.csv")
    summary.to_csv(out_path, index=False)
    dprint(f"Saved metrics summary to {out_path}")
    return summary


if __name__ == "__main__":
    # Default: run on ./data relative to videoImplement/
    here = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(here, "data")
    protocol = Protocol()
    run_feature_extraction(data_dir, protocol, show_plots=False)
