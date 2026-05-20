import cv2
import glob
import os

def get_latest_video(path):
    """
    Get the most recently modified video file (e.g., MP4) in the specified directory.

    Args:
        path (str): The directory path to search for video files.

    Returns:
        str: The path of the latest video file, or None if no files are found.
    """
    video_files = glob.glob(os.path.join(path, "*.mp4"))
    if not video_files:
        return None
    latest_video = max(video_files, key=os.path.getmtime)
    return latest_video

def resize_video(input_path, output_path, height, frame_skip=1):
    """
    Resize a video using OpenCV with optimizations for faster processing.

    Args:
        input_path (str): Path to the input video file.
        output_path (str): Path to save the resized video.
        height (int): Desired height of the output video.
        frame_skip (int): Number of frames to skip during processing (1 = process all frames).
    """
    # Open the input video
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print("Error: Cannot open video file.")
        return

    # Get original dimensions and video properties
    original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) / frame_skip  # Adjust FPS for skipped frames
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Calculate new dimensions while maintaining aspect ratio
    aspect_ratio = original_width / original_height
    new_width = int(height * aspect_ratio)

    # Define the codec and create a VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec for .mp4 files
    out = cv2.VideoWriter(output_path, fourcc, fps, (new_width, height))

    print(f"Processing video: {input_path}")
    print(f"Original dimensions: {original_width}x{original_height}, FPS: {fps * frame_skip}")
    print(f"New dimensions: {new_width}x{height}, Output FPS: {fps}")
    print(f"Total frames to process: {frame_count}")

    # Process the video frame by frame
    frame_num = 0
    processed_frames = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Skip frames for faster processing
        if frame_num % frame_skip == 0:
            # Resize the frame
            resized_frame = cv2.resize(frame, (new_width, height))
            # Write the resized frame to the output video
            out.write(resized_frame)
            processed_frames += 1

            # Print progress every 100 frames, showing progress as "processed 100 / 2000 frames"
            if processed_frames % 100 == 0:
                print(f"Processed {processed_frames} / {frame_count} frames...")

        frame_num += 1

    # Release resources
    cap.release()
    out.release()
    print(f"Finished processing. Total frames written: {processed_frames}")
    print(f"Resized video saved to: {output_path}")


# Main script
video_folder = r'C:\Users\mauro\Videos'  # Replace with your video folder path
output_file = r'C:\Users\mauro\Videos\movie_resized.mp4'  # Replace with your output file path

latest_video = get_latest_video(video_folder)
if latest_video:
    print(f"Latest video found: {latest_video}")
    resize_video(latest_video, output_file, height=360, frame_skip=1)  # Adjust frame_skip for faster processing
else:
    print("No video files found in the specified folder.")
