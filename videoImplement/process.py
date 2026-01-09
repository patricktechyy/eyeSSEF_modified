# load a pupil csv data and then test them with the preprocessing scripts
import os
import pandas as pd
from main import confidenceThresh, pxToMm
from scripts.preProcessing.secondPass import removeSusBio
from scripts.preProcessing.thirdPass import madFilter
#from scripts.preProcessing.fourthPass import interpolateData
#from scripts.preProcessing.fourthPassNoBoundaryCheck import interpolateData
from scripts.preProcessing.fourthPassCubicOnly import interpolateData
from scripts.preProcessing.fifthPass import averagePLRGraphs   
from scripts.preProcessing.firstPass import confidenceFilter
from scripts.preProcessing.sixthPass import savgolSmoothing
from scripts.others.util import dprint
import scripts.others.graph as graph

# load sample data
dprint("Loading sample pupil data for testing preprocessing scripts")
df1Path = "../videoImplement/data/PLR_Tuna_R_1920x1080_30_3"
#df2Path = "../videoImplement/data/PLR_Tuna_R_1280x720_60_2/firstPass.csv"
df1 = pd.read_csv(df1Path + "/raw.csv")
#df2 = pd.read_csv(df2Path)

<<<<<<< Updated upstream
dprint("Initial data loaded:")
dprint(df1.head())
=======
from scripts.preProcessing.firstPass import confidenceFilter
from scripts.preProcessing.secondPass import removeSusBio
from scripts.preProcessing.thirdPass import madFilter
from scripts.preProcessing.fourthPassLinear import interpolateData
from scripts.preProcessing.fifthPass import averagePLRGraphs
from scripts.preProcessing.sixthPass import savgolSmoothing
from scripts.validation.validity import run_validity_report

>>>>>>> Stashed changes

fps = 30

def doProcessing(df, fps=30, saveBeforeInterpolation=False, savePathBeforeInterpolation=df1Path + "/beforeInterpolation.csv"):
    # first pass
    df = confidenceFilter(df)
    dprint("After first pass (confidenceFilter):")
    dprint(df.head())

    # second pass
    df = removeSusBio(df, fps)
    dprint("After second pass (removeSusBio):")
    dprint(df.head())

    # third pass
    df = madFilter(df)
    dprint("After third pass (madFilter):")
    dprint(df.head())

    # save before interpolation if needed
    if saveBeforeInterpolation:
        dfNoInterpolation = df.copy()
        df.to_csv(savePathBeforeInterpolation, index=False)
        dprint(f"Data before interpolation saved to '{savePathBeforeInterpolation}'")

        # percentage of NaNs before interpolation
        totalPoints = len(dfNoInterpolation)
        badPoints = dfNoInterpolation['is_bad_data'].sum()
        badPercentage = (badPoints / totalPoints) * 100.0
        

    # fourth pass
    #df = interpolateData(df, fps)
    df = interpolateData(df)
    dprint("After fourth pass (interpolateData):")
    dprint(df.head())


    # fifth pass
    # skipping averagePLRGraphs here as we only have one dataset

    # sixth pass
    df = savgolSmoothing(df, fps=fps)
    dprint("After sixth pass (savgolSmoothing):")
    dprint(df.head())

    if saveBeforeInterpolation: 
        return df, dfNoInterpolation, totalPoints, badPoints, badPercentage
    else: 
        return df


<<<<<<< Updated upstream
dprint("Processing first dataset")
df1_processed = doProcessing(df1, fps=fps)
# get stats before interpolation
#df1_processed, df1_beforeInterpolation, totalPoints, badPoints, badPercentage = doProcessing(df1, fps=60, saveBeforeInterpolation=True, savePathBeforeInterpolation=df1Path + "/beforeInterpolation.csv")
#dprint(f"Before interpolation - Total data points: {totalPoints}, Bad data points: {badPoints}, Bad percentage: {badPercentage:.2f}%")

# save to csv
csvPreprocessedPath = "data/" + os.path.basename(df1Path).split('.')[0] + "/processed.csv"
df1_processed.to_csv(csvPreprocessedPath, index=False)
dprint(f"Processed data saved to CSV at '{csvPreprocessedPath}'")

# plotting results
dataFolderPath = "data/" + os.path.basename(df1Path).split('.')[0]
graph.plotResults(df1_processed, savePath=dataFolderPath + "/processedPlot.png", showPlot=True, showMm=True)

# plot non interpolated data for comparison
#dataFolderPath = "data/" + os.path.basename(df1Path).split('.')[0]
#graph.plotResults(df1_beforeInterpolation, savePath=dataFolderPath + "/beforeInterpolationPlot.png", showPlot=True, showMm=True)
#dprint("Processing second dataset")
#df2_processed = doProcessing(df2, fps=30)

# averaging
#dprint("Averaging the two processed datasets")
#averaged_df = averagePLRGraphs(df1_processed, df2_processed)
#dprint("After fifth pass (averagePLRGraphs):")
#dprint(averaged_df.head())
=======
def process_single_trial(
    trial_dir: str,
    config: ProcessingConfig,
    show_plot: bool,
    recompute_mm: bool,
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Process one trial directory and write processed outputs into the same folder.

    In addition to processed.csv + processedPlot.png, this writes:
    - processed_interpolated.csv: output after Pass 4 (before smoothing)
    - validity_report.(csv/json) + validity_*.png: statistical validation artifacts
    """

    raw_df = _load_raw_csv(trial_dir)

    # Optionally recompute diameter_mm from pixels using config.px_to_mm
    if recompute_mm:
        if config.px_to_mm is None:
            raise ValueError("recompute_mm requested but config.px_to_mm is None.")
        raw_df["diameter_mm"] = pd.to_numeric(raw_df["diameter"], errors="coerce") / float(config.px_to_mm)

    # Pass 1-4
    df_after_4, counts, _ = run_passes_1_to_4(raw_df.copy(), config)

    out_csv_p4 = os.path.join(trial_dir, "processed_interpolated.csv")
    df_after_4.to_csv(out_csv_p4, index=False)
    dprint(f"Saved Pass 4 output: {out_csv_p4}")

    # Pass 6
    df_final, _ = run_pass_6(df_after_4.copy(), config)

    # Save outputs
    out_csv = os.path.join(trial_dir, "processed.csv")
    df_final.to_csv(out_csv, index=False)
    dprint(f"Saved processed CSV: {out_csv}")

    out_plot = os.path.join(trial_dir, "processedPlot.png")
    graph.plotResults(df_final, savePath=out_plot, showPlot=show_plot, showMm=True)
    dprint(f"Saved plot: {out_plot}")

    # Final summary for this trial
    total = counts["total"]
    flagged_total = int(_flagged_mask(df_final).sum())
    interpolated = counts["interpolated"]
    _quality_summary(total, flagged_total, interpolated)

    # Statistical validity report (saved to trial folder)
    try:
        # Assumed onsets based on your fixed recording protocol:
        # 3s pre-stim, 0.25s blue, 60s rest, 0.25s red, 60s rest.
        # If the trial is shorter, the validator will ignore missing windows.
        assumed_onsets = [3.0, 63.25]
        run_validity_report(
            out_dir=trial_dir,
            raw_df=raw_df,
            interpolated_df=df_after_4,
            smoothed_df=df_final,
            fps_hint=float(config.fps),
            confidence_thresh=float(config.confidence_thresh),
            assumed_onsets_s=assumed_onsets,
            trial_label=os.path.basename(os.path.abspath(trial_dir)),
        )
        dprint("Saved validity report artifacts (CSV/JSON/PNG).")
    except Exception as e:
        dprint(f"WARNING: validity report failed: {e}")

    return df_final, counts


def _find_trials_in_parent(parent_dir: str) -> List[Tuple[str, TrialMeta]]:
    trials: List[Tuple[str, TrialMeta]] = []
    for name in os.listdir(parent_dir):
        full = os.path.join(parent_dir, name)
        if not os.path.isdir(full):
            continue
        meta = _parse_trial_dirname(name)
        if not meta:
            continue
        if not os.path.exists(os.path.join(full, "raw.csv")):
            continue
        trials.append((full, meta))
    return trials


def process_group_average(
    parent_dir: str,
    group_key: Tuple[str, str, str, int],
    trial_items: List[Tuple[str, TrialMeta]],
    show_plot: bool,
    recompute_mm: bool,
    max_gap_ms: int,
    savgol_window_ms: int,
    confidence_thresh: float,
) -> None:
    """Process the latest 2 trials in this group, average (Pass 5) if possible, then smooth (Pass 6)."""
    user, eye, res, fps = group_key

    # choose two trials with highest trial index
    trial_items = sorted(trial_items, key=lambda x: x[1].trial)
    chosen = trial_items[-2:] if len(trial_items) >= 2 else trial_items
    if len(chosen) == 0:
        return

    dprint(f"\n=== Group: user={user}, eye={eye}, res={res}, fps={fps} | trials={[m.trial for _,m in chosen]} ===")

    # Build config for this group (from filename)
    width, height = parse_resolution(res)
    px_to_mm = px_to_mm_from_resolution(width, height)
    config = ProcessingConfig(
        fps=fps,
        resolution=(width, height),
        px_to_mm=px_to_mm,
        confidence_thresh=confidence_thresh,
        max_gap_ms=max_gap_ms,
        savgol_window_ms=savgol_window_ms,
    )

    dfs_after_interp: List[pd.DataFrame] = []
    counts_list: List[Dict[str, int]] = []

    # Process each chosen trial (save per-trial outputs, but do not show plot for each)
    for trial_dir, meta in chosen:
        dprint(f"\n--- Processing trial folder: {meta.dirname} ---")
        df = _load_raw_csv(trial_dir)

        if recompute_mm:
            df["diameter_mm"] = pd.to_numeric(df["diameter"], errors="coerce") / float(config.px_to_mm)

        df_after_4, counts, _ = run_passes_1_to_4(df, config)

        # Save the per-trial interpolated output (useful for debugging / averaging input)
        out_csv = os.path.join(trial_dir, "processed_interpolated.csv")
        df_after_4.to_csv(out_csv, index=False)
        dprint(f"Saved Pass 4 output: {out_csv}")

        # Also produce the per-trial final output (Pass 6), but do not show plot windows in batch mode.
        df_final, _ = run_pass_6(df_after_4.copy(), config)

        out_csv_final = os.path.join(trial_dir, "processed.csv")
        df_final.to_csv(out_csv_final, index=False)

        out_plot_final = os.path.join(trial_dir, "processedPlot.png")
        graph.plotResults(df_final, savePath=out_plot_final, showPlot=False, showMm=True)

        dprint(f"Saved per-trial processed CSV: {out_csv_final}")
        dprint(f"Saved per-trial plot: {out_plot_final}")

        # Per-trial quality summary
        _quality_summary(
            total_frames=counts["total"],
            flagged_total=int(_flagged_mask(df_final).sum()),
            interpolated=counts["interpolated"],
        )
        # Statistical validity report (per-trial)
        try:
            assumed_onsets = [3.0, 63.25]
            run_validity_report(
                out_dir=trial_dir,
                raw_df=df,
                interpolated_df=df_after_4,
                smoothed_df=df_final,
                fps_hint=float(config.fps),
                confidence_thresh=float(config.confidence_thresh),
                assumed_onsets_s=assumed_onsets,
                trial_label=meta.dirname,
            )
            dprint("Saved validity report artifacts (per-trial).")
        except Exception as e:
            dprint(f"WARNING: validity report failed (per-trial): {e}")


        dfs_after_interp.append(df_after_4)
        counts_list.append(counts)

    # If we have two trials, attempt averaging (Pass 5) only if both fully filled
    averaged_df = None
    if len(dfs_after_interp) == 2:
        has_nan_1 = bool(dfs_after_interp[0]["diameter_mm"].isna().any())
        has_nan_2 = bool(dfs_after_interp[1]["diameter_mm"].isna().any())

        if not has_nan_1 and not has_nan_2:
            averaged_df = averagePLRGraphs(dfs_after_interp[0], dfs_after_interp[1], px_to_mm=config.px_to_mm, fps=fps)
            if averaged_df is None:
                dprint('Pass 5 skipped: averaging failed (e.g., insufficient overlap). Using first trial as output.')
                averaged_df = dfs_after_interp[0].copy()
        else:
            dprint("Pass 5 skipped: one or both graphs still contain NaNs after interpolation.")
            averaged_df = dfs_after_interp[0].copy()
    else:
        averaged_df = dfs_after_interp[0].copy()

    # Pass 5 reporting:
    # After averaging, `averaged_df['is_bad_data']` already represents the OR of both trials (see fifthPass.py).
    # Averaging should not introduce new "bad" frames by itself, so we set prev_flagged = current flagged
    # to report newly-flagged=0 consistently.
    prev_p5 = _flagged_mask(averaged_df)
    _report_stage("Pass 5 (averaging)", averaged_df, prev_p5)

    averaged_after_5 = averaged_df.copy()

    # Pass 6 on the final output
    averaged_df, _ = run_pass_6(averaged_df, config)

    # Output folder for the group
    out_dirname = f"PLR_{user}_{eye}_{res}_{fps}_AVG"
    out_dir = os.path.join(parent_dir, out_dirname)
    os.makedirs(out_dir, exist_ok=True)
    out_csv_p5 = os.path.join(out_dir, "processed_avg_interpolated.csv")
    averaged_after_5.to_csv(out_csv_p5, index=False)
    dprint(f"Saved averaged Pass 5 output: {out_csv_p5}")


    out_csv = os.path.join(out_dir, "processed_avg.csv")
    averaged_df.to_csv(out_csv, index=False)

    out_plot = os.path.join(out_dir, "processedAvgPlot.png")
    graph.plotResults(averaged_df, savePath=out_plot, showPlot=show_plot, showMm=True)

    dprint(f"Saved averaged CSV: {out_csv}")
    dprint(f"Saved averaged plot: {out_plot}")

    # Quality summary for averaged output:
    total = len(averaged_df)
    flagged_total = int(_flagged_mask(averaged_df).sum())
    interpolated_total = sum(c["interpolated"] for c in counts_list) // max(1, len(counts_list))
    _quality_summary(total, flagged_total, interpolated_total)
    # Statistical validity report for averaged output
    try:
        assumed_onsets = [3.0, 63.25]
        run_validity_report(
            out_dir=out_dir,
            raw_df=None,
            interpolated_df=averaged_after_5,
            smoothed_df=averaged_df,
            fps_hint=float(config.fps),
            confidence_thresh=float(config.confidence_thresh),
            assumed_onsets_s=assumed_onsets,
            trial_label=out_dirname,
        )
        dprint("Saved validity report artifacts (averaged output).")
    except Exception as e:
        dprint(f"WARNING: validity report failed (averaged output): {e}")



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True,
                        help="Either: (a) a single trial directory containing raw.csv, or "
                             "(b) a parent directory containing multiple PLR_* trial folders.")
    parser.add_argument("--fps", type=int, default=None,
                        help="Override fps for single-trial mode. In batch mode, fps is inferred from folder name.")
    parser.add_argument("--resolution", type=str, default=None,
                        help="Override resolution for single-trial mode (e.g., 1920x1080). "
                             "In batch mode, resolution is inferred from folder name.")
    parser.add_argument("--recompute_mm", action="store_true",
                        help="Recompute diameter_mm from diameter pixels using px_to_mm derived from resolution.")
    parser.add_argument("--max_gap_ms", type=int, default=400,
                        help="Pass 4: maximum gap duration to interpolate (ms). Default 400 ms.")
    parser.add_argument("--savgol_window_ms", type=int, default=150,
                        help="Pass 6: smoothing window duration (ms). Default 150 ms.")

    # Restored behaviour: show plot window by default, allow disabling
    parser.add_argument("--no_show_plot", action="store_true",
                        help="Disable interactive matplotlib plot window (still saves PNG).")
    parser.add_argument("--show_all_plots", action="store_true",
                        help="Batch mode only: show plots for every processed trial as well (not recommended).")

    args = parser.parse_args()

    data_path = args.data
    show_plot = not args.no_show_plot

    # Single-trial mode if raw.csv exists directly inside --data
    if os.path.exists(os.path.join(data_path, "raw.csv")):
        # Determine config for single mode
        # Prefer CLI overrides; otherwise infer fps from timestamps and resolution from folder name if possible.
        folder_name = os.path.basename(os.path.abspath(data_path))
        meta = _parse_trial_dirname(folder_name)

        fps = args.fps
        if fps is None:
            if meta is not None:
                fps = meta.fps
            else:
                df_tmp = pd.read_csv(os.path.join(data_path, "raw.csv"))
                fps = infer_fps_from_timestamps(df_tmp)

        if args.resolution is not None:
            width, height = parse_resolution(args.resolution)
        elif meta is not None:
            width, height = parse_resolution(meta.res)
        else:
            raise ValueError("Resolution not provided and could not be inferred. Use --resolution 1920x1080.")

        config = ProcessingConfig(
            fps=int(fps),
            resolution=(width, height),
            px_to_mm=px_to_mm_from_resolution(width, height),
            confidence_thresh=0.75,
            max_gap_ms=args.max_gap_ms,
            savgol_window_ms=args.savgol_window_ms,
        )

        process_single_trial(
            trial_dir=data_path,
            config=config,
            show_plot=show_plot,
            recompute_mm=args.recompute_mm,
        )
        return

    # Otherwise, batch mode: scan subfolders
    trials = _find_trials_in_parent(data_path)
    if not trials:
        raise ValueError(f"No trial folders found under: {data_path}")

    # Group by (user, eye, res, fps)
    groups: Dict[Tuple[str, str, str, int], List[Tuple[str, TrialMeta]]] = {}
    for trial_dir, meta in trials:
        key = (meta.user, meta.eye, meta.res, meta.fps)
        groups.setdefault(key, []).append((trial_dir, meta))

    dprint(f"Found {len(trials)} trial folders forming {len(groups)} groups.")

    # In batch mode, showing every plot can block the pipeline. Default: show only final averaged plots.
    for key, items in sorted(groups.items(), key=lambda kv: kv[0]):
        process_group_average(
            parent_dir=data_path,
            group_key=key,
            trial_items=items,
            show_plot=show_plot,  # shows averaged plot windows
            recompute_mm=args.recompute_mm,
            max_gap_ms=args.max_gap_ms,
            savgol_window_ms=args.savgol_window_ms,
            confidence_thresh=0.75,
        )

        if args.show_all_plots and show_plot:
            # Optionally show each individual trial plot (after full processing)
            for trial_dir, meta in items[-2:]:
                # Load processed.csv if available and show
                p = os.path.join(trial_dir, "processed.csv")
                if os.path.exists(p):
                    df = pd.read_csv(p)
                    graph.plotResults(df, savePath=None, showPlot=True, showMm=True, title=f"{meta.dirname}")


if __name__ == "__main__":
    main()
>>>>>>> Stashed changes
