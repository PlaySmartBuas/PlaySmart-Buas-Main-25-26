import keyboard
import subprocess
import time
import psutil
import sys


def kill_openface():
    """Kill any leftover OpenFace FeatureExtraction.exe processes"""
    for proc in psutil.process_iter(["pid", "name"]):
        if proc.info["name"] and "FeatureExtraction.exe" in proc.info["name"]:
            print(f"Killing leftover OpenFace process: PID {proc.pid}")
            proc.kill()


def main():
    """
    Handles script execution flow based on key presses (F7 to start, F12 to stop).
    Author: Thomas Pichardo, Mauro van Hulst, Maikel Boezer
    Modified: Start overlays as hidden/minimized on Windows; remove manual popup when session context exists.
    """
    while True:
        print("Waiting for F7 or F12... (Press F7 to start or F12 to stop)")
        keyboard.wait("f7")

        print("F7 pressed, starting scripts...")
        kill_openface()  # Optional: clear leftover OpenFace processes
        processes = []
        hidden_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        try:
            # Start gaze, emotion, and input logging scripts
            processes.append(subprocess.Popen(["poetry", "run", "python", "src/eye_tracking_script.py"]))
            processes.append(subprocess.Popen(["poetry", "run", "python", "src/Emotion_gaze_visualization.py"]))
            processes.append(subprocess.Popen(["poetry", "run", "python", "src/keyboard_recording.py"]))
            processes.append(subprocess.Popen(["poetry", "run", "python", "src/microphone_recording.py"]))

            time.sleep(2)
            processes.append(subprocess.Popen(["poetry", "run", "python", "src/nuanic_eda.py"]))

            print("Waiting for F12 to stop and upload data...")
            keyboard.wait("f12")

            print("F12 pressed, stopping processes...")
            for process in processes:
                if process.poll() is None:
                    process.terminate()

            time.sleep(2)

            print("Uploading latest data files via pop_up_screen.py...")
            # Capture output so we can detect whether the pop-up was skipped via session context
            result = subprocess.run(
                [
                    "poetry",
                    "run",
                    "python",
                    "src/pop_up_screen.py",
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                out = result.stdout or ""
                # Always print the pop_up_screen output so users can see what was renamed/uploaded
                if out:
                    print(out.strip())
                if "Loaded session context from:" in out:
                    print("Upload successful — used session context; popup not shown.")
                else:
                    print(
                        "Upload successful — popup shown or no session context detected."
                    )
            else:
                print(" Upload failed.")
                # Print script output to help debugging
                if result.stdout:
                    print("pop_up_screen stdout:\n", result.stdout)
                if result.stderr:
                    print("pop_up_screen stderr:\n", result.stderr)
        finally:
            for process in processes:
                if process.poll() is None:
                    process.terminate()
            print("Processes stopped.")


if __name__ == "__main__":
    main()
