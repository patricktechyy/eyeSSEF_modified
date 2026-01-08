# TODO
# add a counter for processing iterations?
# set data as bad if confidence < threshold
# set data as bad IF the difference in pupil diameter between any 2 frames is >0.5mm (applies for 60fps)
# do cubic spline interpolation to fill in bad data points



import os
import cv2
import shutil
import datetime
import argparse
import re
import subprocess
import sys
import scripts.others.splitVideo as splitVideo
import scripts.detection.ppDetect as ppDetect
import scripts.others.graph as graph
import scripts.others.util as util
import matplotlib.pyplot as plt
import pandas as pd
from scipy.interpolate import CubicSpline

#from scripts.preProcessing.firstPass import preProcessFirstPass
# make sure later u save the detected images into a folder

pathToVideo = "../eyeVids/tuna/PLR_Tuna_R_1920x1080_30_4.mp4"  # default fallback; CLI can override
pathToLeft = "./videos/left_half.mp4"
pathToRight = "./videos/right_half.mp4"
confidenceThresh = 0.75

# Video filename convention (stem, no extension):
# PLR_[Username]_[EyeSide L/R]_[Resolution]_[FPS]_[TrialIndex]
# Example: PLR_Patrick_R_1920x1080_30_2
TRIAL_VIDEO_RE = re.compile(r"^PLR_(?P<user>.+)_(?P<eye>[LR])_(?P<res>\d+x\d+)_(?P<fps>\d+)_(?P<trial>\d+)$")


processingIteration = 0
pxToMm = 30.0  # pixels per mm at 1080p (baseline). Prefer using settings.ProcessingConfig.

# --- Configuration helpers (fps & resolution) ---------------------------------
# Many thresholds are time-based -> they depend on fps.
# Pixel-to-mm conversion depends on resolution (and your optical setup).
#
# You can keep using the old globals (confidenceThresh, pxToMm),
# but for new code we recommend using videoImplement/settings.py.
try:
    from settings import px_to_mm_from_resolution, parse_resolution
except Exception:
    px_to_mm_from_resolution = None
    parse_resolution = None

def configure_processing_params(frame_rate: float, width: int, height: int,
                                fps_override=None,
                                resolution_override=None,
                                px_to_mm_override=None):
    """Return (fps, width, height, px_to_mm) using user overrides if provided."""
    fps = float(fps_override) if fps_override is not None else float(frame_rate)

    if resolution_override and parse_resolution is not None:
        w, h = parse_resolution(resolution_override)
    else:
        w, h = int(width), int(height)

    if px_to_mm_override is not None:
        px_to_mm = float(px_to_mm_override)
    elif px_to_mm_from_resolution is not None:
        px_to_mm = px_to_mm_from_resolution(w, h)
    else:
        px_to_mm = pxToMm  # fallback to legacy global

    return fps, w, h, px_to_mm




# print stuff with timestamp at the start cuz it looks nice
# lmao


def splitEyes(video, left, right, widthThresh):
    util.dprint(f"attemping to convert video file '{video} into left and right videos '{left}' and '{right}'")
    # Paths
    input_video = video  # path to video
    output_left = left
    output_right = right

    splitVideo.split_video_left_right(input_video, output_left, output_right, widthThresh)



def resetFolder(folderName):
    if os.path.exists(folderName):
        util.dprint(f"folder '{folderName}' exists, removing contents in folder")
        try:
            shutil.rmtree(folderName)
            util.dprint(f"Folder '{folderName}' and all its contents deleted successfully.")
        except OSError as e:
            util.dprint(f"Error: {e}. An error occurred during deletion.")
        util.dprint(f"Making new '{folderName}'")
        os.makedirs(folderName)
    else: 
        util.dprint(f"Folder '{folderName}' does not exist, making the folder")
        try:
            os.makedirs(folderName)
        except OSError:
            util.dprint(f"Error: Creating folder '{folderName}'")
    return folderName

# split the video into multiple image files
def videoToImages(video, folderName):
    folderName = str(folderName)
    util.dprint(f"Trying to convert video '{video}' into frames and storing into '{folderName}'")
    # 2. convert the video into multiple .bmp files and store it in the tempImages folder
    cam = cv2.VideoCapture(video)
    currentframe = 0
    frameRate = cam.get(cv2.CAP_PROP_FPS)
    print(f"Video frame rate: {frameRate} fps")
    while True:
        ret,frame = cam.read()
        if ret:
            #name = './frames/' + folderName +'/frame' + str(currentframe) + '.bmp'
            name = os.path.join(folderName, 'frame' + str(currentframe) + '.bmp')
            util.dprint("Creating... " + name)

            cv2.imwrite(name, frame)

            currentframe += 1
        else:
            break

    cam.release()
    cv2.destroyAllWindows()    
    util.dprint("All frames done!")

    return frameRate, currentframe

    # 3. turn images ito grayscale (actually i think this is part of the algorithm but meh)
    
def pupilDetectionInFolder(folderPath):
    util.dprint(f"Starting pupil detection in folder '{folderPath}'")
    conf = []
    diameter = []
    for i in range(len(os.listdir(folderPath))):
        filename = f"frame{i}.bmp"
        newPath = os.path.join(folderPath, filename)
        imgWithPupil, outline_confidence, pupil_diameter = ppDetect.detect(newPath)
        
        conf.append(outline_confidence)
        diameter.append(pupil_diameter)
        util.dprint(f"Showing image {newPath} with detected pupil...")
        # show the images continuously using cv2 window
        cv2.imshow("Pupil Detection for " + pathToVideo, imgWithPupil)
        cv2.waitKey(1)  # Display each image for 1 ms

        # closes window after all images are shown
    cv2.destroyAllWindows()
    return conf, diameter

def calculateTimeStamps(frameRate, totalFrames):
    timePerFrame = 1.0 / frameRate
    timestamps = [i * timePerFrame for i in range(totalFrames)]
    return timestamps


def getAverageOfColumn(dataframe, colName):
    return dataframe[colName].mean()



def blinkDetection(image):
    pass

# save data to csv with Columns: 'frame_id', 'timestamp', 'diameter', 'diameter_mm', 'confidence', 'is_bad_data'
def saveDataToCSV(frameIDs, timestamps, diameters, confidences, outputPath, px_to_mm=None):
    data = {
        'frame_id': frameIDs,
        'timestamp': timestamps,
        'diameter': diameters,
        'confidence': confidences
    }
    df = pd.DataFrame(data)
    # Mark bad data points (confidence < 1)
    df['is_bad_data'] = df['confidence'] < confidenceThresh
    df['diameter_mm'] = df['diameter'] / (px_to_mm if px_to_mm is not None else pxToMm)
    df.to_csv(outputPath, index=False)
    util.dprint(f"Data saved to CSV at '{outputPath}'")
    
    # return the pandas dataframe too if needed
    return df




def _get_video_props(video_path: str):
    """Return (fps, width, height) from the video container using OpenCV."""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    cap.release()
    return float(fps), int(width), int(height)


def _find_videos(input_path: str, recursive: bool = False):
    """Find video files under input_path. Supported extensions: .mp4, .mov, .avi, .mkv, .h264"""
    exts = {'.mp4', '.mov', '.avi', '.mkv', '.h264'}
    videos = []
    if os.path.isfile(input_path):
        return [input_path]
    if not os.path.isdir(input_path):
        return []
    if recursive:
        for root, _, files in os.walk(input_path):
            for f in files:
                if os.path.splitext(f)[1].lower() in exts:
                    videos.append(os.path.join(root, f))
    else:
        for f in os.listdir(input_path):
            p = os.path.join(input_path, f)
            if os.path.isfile(p) and os.path.splitext(f)[1].lower() in exts:
                videos.append(p)
    videos.sort()
    return videos


def generateReport(video_path: str, show_raw_plot: bool = True):
    """Run detection on one video -> writes raw.csv into videoImplement/data/<stem>/"""
    util.dprint("Running standalone pupil detection implementation...")
    resetFolder("videos")
    resetFolder("frames")

    stem = os.path.splitext(os.path.basename(video_path))[0]

    # Try to parse fps/resolution from filename; fall back to video metadata
    fps_override = None
    res_override = None
    m = TRIAL_VIDEO_RE.match(stem)
    if m:
        fps_override = int(m.group('fps'))
        res_override = m.group('res')

    meta_fps, meta_w, meta_h = _get_video_props(video_path)
    fps, w, h, px_to_mm = configure_processing_params(
        frame_rate=meta_fps if meta_fps else (fps_override if fps_override else 0),
        width=meta_w,
        height=meta_h,
        fps_override=fps_override,
        resolution_override=res_override,
        px_to_mm_override=None,
    )

    # Convert video -> frames (BMPs) and run pupil detection
    _frameRate, totalFrames = videoToImages(video_path, "frames")
    conf, diameter = pupilDetectionInFolder("frames/")

    # Use fps (possibly from filename override) for timestamps
    timestamps = calculateTimeStamps(fps, totalFrames)

    dataFolderPath = resetFolder(os.path.join("data", stem))
    csvDataPath = os.path.join("data", stem, "raw.csv")
    df = saveDataToCSV(list(range(totalFrames)), timestamps, diameter, conf, csvDataPath, px_to_mm=px_to_mm)

    print(("Average pupil diameter (pixels): ", getAverageOfColumn(df, 'diameter')))
    # Raw plot is usually helpful for debugging, but in batch mode it can spam windows.
    graph.plotResults(df, savePath=os.path.join(dataFolderPath, "rawPlot.png"), showPlot=show_raw_plot, showMm=True)

    return dataFolderPath


def _run_preprocessing(data_dir: str):
    """Run Pass 1->6 preprocessing (and 2-trial averaging) on a data directory."""
    process_py = os.path.join(os.path.dirname(__file__), "process.py")
    # Run as a subprocess so matplotlib uses the normal interactive backend (same as old behavior)
    cmd = [sys.executable, process_py, "--data", data_dir]
    util.dprint("Running preprocessing pipeline: " + " ".join(cmd))
    subprocess.run(cmd, check=True)


# ENTRY POINT
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=None,
                        help="A single video file, or a folder containing videos. If omitted, uses the legacy pathToVideo.")
    parser.add_argument("--recursive", action="store_true", help="Search for videos recursively when --input is a folder.")
    parser.add_argument("--no_raw_plot", action="store_true", help="Do not open raw interactive plot windows.")
    parser.add_argument("--no_preprocess", action="store_true", help="Only generate raw.csv; do not run Pass 1-6 preprocessing.")
    args = parser.parse_args()

    input_path = args.input or pathToVideo

    videos = _find_videos(input_path, recursive=args.recursive)

    # If input is a folder but no videos were found, assume it's already a data folder and just preprocess it.
    if os.path.isdir(input_path) and not videos and not args.no_preprocess:
        _run_preprocessing(input_path)
        raise SystemExit(0)

    if not videos:
        raise SystemExit(f"No videos found at: {input_path}")

    # In batch mode, avoid popping up one raw plot per video unless explicitly desired
    show_raw = (len(videos) == 1) and (not args.no_raw_plot)

    for v in videos:
        util.dprint(f"Processing video: {v}")
        generateReport(v, show_raw_plot=show_raw)

    if not args.no_preprocess:
        # Preprocess everything in videoImplement/data (groups and averages automatically)
        data_parent = os.path.join(os.path.dirname(__file__), "data")
        _run_preprocessing(data_parent)