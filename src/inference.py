"""
Batch YOLO Inference Script (No Reaction Time)

- Processes all videos inside data/video/
- Detects:
    Class 1 = Enemy (Red box)
    Class 0 = Ally  (Green box)
- Saves annotated outputs into annotated videos/

Author: imani-Jamir Senior
"""

import os
import cv2
import logging
import torch
from ultralytics import YOLO

# ---------------------------
# Configuration
# ---------------------------
VIDEO_FOLDER = "data/video"
OUTPUT_FOLDER = "annotated videos"
MODEL_PATH = "yolov8n.pt"
CONF_THRESHOLD = 0.7

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# ---------------------------
# Load Model
# ---------------------------
def load_model(model_path):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logging.info(f"Loading model on device: {device}")
    model = YOLO(model_path)
    return model, device


# ---------------------------
# Process Single Video
# ---------------------------
def process_video(video_path, model, device, threshold):
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        logging.error(f"Could not open video: {video_path}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    video_name = os.path.basename(video_path)
    output_path = os.path.join(OUTPUT_FOLDER, f"annotated_{video_name}")

    out = cv2.VideoWriter(
        output_path,
        cv2.VideoWriter_fourcc(*'mp4v'),
        fps,
        (width, height)
    )

    frame_count = 0

    logging.info(f"Processing video: {video_name}")
    logging.info(f"Total frames: {total_frames}")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        results = model.predict(frame, conf=threshold, device=device, verbose=False)
        annotated = frame.copy()

        for box in results[0].boxes:
            cls_id = int(box.cls[0].item())
            conf = box.conf[0].item()

            if conf >= threshold:
                xmin, ymin, xmax, ymax = map(int, box.xyxy[0].tolist())

                label = "Enemy" if cls_id == 1 else "Ally"
                color = (0, 0, 255) if cls_id == 1 else (0, 255, 0)

                cv2.rectangle(annotated, (xmin, ymin), (xmax, ymax), color, 2)
                cv2.putText(
                    annotated,
                    f"{label} {conf:.2f}",
                    (xmin, ymin - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    color,
                    2
                )

        cv2.putText(
            annotated,
            f"Frame: {frame_count}",
            (30, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )

        out.write(annotated)
        frame_count += 1

        if frame_count % 100 == 0:
            logging.info(f"{video_name}: Processed {frame_count}/{total_frames} frames")

    cap.release()
    out.release()
    logging.info(f"Finished: {video_name}")
    logging.info(f"Saved to: {output_path}")


# ---------------------------
# Run Batch Inference
# ---------------------------
def run_batch_inference():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    model, device = load_model(MODEL_PATH)

    if not os.path.exists(VIDEO_FOLDER):
        logging.error(f"Video folder not found: {VIDEO_FOLDER}")
        return

    video_files = [
        os.path.join(VIDEO_FOLDER, f)
        for f in os.listdir(VIDEO_FOLDER)
        if f.lower().endswith((".mp4", ".avi", ".mov", ".mkv"))
    ]

    if not video_files:
        logging.warning("No video files found in data/video/")
        return

    logging.info(f"Found {len(video_files)} videos.")

    for video_path in video_files:
        process_video(video_path, model, device, CONF_THRESHOLD)

    logging.info("All videos processed successfully.")


# ---------------------------
# Main
# ---------------------------
if __name__ == "__main__":
    run_batch_inference()