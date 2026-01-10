
"""
align.py (eyeSSEF 8) - Feature extraction entry point

Older versions of align.py were a *hardcoded experiment script* (e.g., always reading Tuna).
This new version is the stable entry point you should use:

    python align.py

It will:
- scan videoImplement/data/ for all folders ending in "_AVG"
- for each averaged waveform (processed_avg.csv), compute PLR + PIPR metrics
- save per-folder metrics.csv + aligned plots
- save videoImplement/data/metrics_summary.csv

Late PIPR is computed as a non-negative, baseline-corrected (drift-corrected) constriction metric over 10–30 s post-stimulus.

Net PIPR is reported in the table using the **Blue − Red** convention (primary). We also save the opposite convention (Red − Blue) in metrics.csv so you can cross-check sign.
"""

import argparse
import os
from feature_extract import Protocol, run_feature_extraction
from scripts.others.util import dprint


def main():
    parser = argparse.ArgumentParser(description="Compute PLR/PIPR metrics from *_AVG folders (processed_avg.csv).")
    parser.add_argument(
        "--data_dir",
        type=str,
        default=None,
        help="Path to the videoImplement/data directory (defaults to ./data next to this script).",
    )
    parser.add_argument("--blue_onset", type=float, default=3.0, help="Nominal BLUE onset time (s) after camera start.")
    parser.add_argument("--stim_dur", type=float, default=0.25, help="Stimulus duration (s).")
    parser.add_argument("--isi", type=float, default=60.0, help="Inter-stimulus interval between BLUE offset and RED onset (s).")
    parser.add_argument("--show_plots", action="store_true", help="Also display interactive plots (in addition to saving PNGs).")
    parser.add_argument("--no_refine_onset", action="store_true", help="Disable onset refinement; use nominal onset times exactly.")

    args = parser.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    data_dir = args.data_dir or os.path.join(here, "data")

    protocol = Protocol(blue_onset_s=args.blue_onset, stim_dur_s=args.stim_dur, isi_s=args.isi, refine_onset=(not args.no_refine_onset))

    dprint(f"Running feature extraction on: {data_dir}")
    run_feature_extraction(data_dir, protocol, show_plots=args.show_plots)


if __name__ == "__main__":
    main()
