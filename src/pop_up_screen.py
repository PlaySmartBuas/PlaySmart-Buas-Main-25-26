import os
import glob
import datetime
import tkinter as tk
from tkinter import simpledialog
import json
import sys
import time
from tkinter import ttk

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sftp_upload import upload_file_to_sftp

# ------------------ Utility Functions ------------------


def get_latest_file(path):
    """Return the most recently modified CSV file in the given directory."""
    files = glob.glob(os.path.join(path, "*.csv"))
    return max(files, key=os.path.getmtime) if files else None


def get_next_player_id(mapping):
    """Generate the next available player ID like P028."""
    existing_ids = [v for v in mapping.values() if v.startswith("P")]
    nums = [int(pid[1:]) for pid in existing_ids if pid[1:].isdigit()]
    next_num = max(nums, default=0) + 1
    return f"P{next_num:03d}"


def load_mapping(mapping_file="data/json/ign_mapping.json"):
    if os.path.exists(mapping_file):
        with open(mapping_file, "r") as file:
            return json.load(file)
    return {}


def load_session_context(context_file="data/json/session_context.json"):
    """Load latest session context saved by the Electron app (if available).

    Tries a small list of candidate locations so the Electron app can write
    session context in a few common places. Returns the parsed JSON or an
    empty dict if none found.
    """
    candidates = [context_file]

    # project root (parent of src)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates.append(
        os.path.join(project_root, "data", "json", "session_context.json")
    )
    candidates.append(os.path.join(project_root, "session_context.json"))

    # Documents/research_software (used elsewhere in the code for videos)
    docs_path = os.path.join(
        os.path.expanduser("~"),
        "Documents",
        "research_software",
        "data",
        "json",
        "session_context.json",
    )
    candidates.append(docs_path)

    for path in candidates:
        try:
            if os.path.exists(path):
                with open(path, "r") as file:
                    data = json.load(file)
                    print(f"Loaded session context from: {path}")
                    return data
        except json.JSONDecodeError:
            print(f"Warning: corrupted session context file at {path} → ignoring.")
        except Exception as e:
            print(f"Warning: failed to read session context at {path}: {e}")

    print("No session context file found in candidates:")
    for p in candidates:
        print("  -", p)
    return {}


def normalize_game_name(game_name: str) -> str:
    normalized = game_name.strip().lower()
    if normalized in {"lol", "league", "league of legends", "league_of_legends"}:
        return "league_of_legends"
    if normalized in {"valorant", "val"}:
        return "valorant"
    return normalized


def save_mapping(mapping, mapping_file="data/json/ign_mapping.json"):
    os.makedirs(os.path.dirname(mapping_file), exist_ok=True)
    with open(mapping_file, "w") as file:
        json.dump(mapping, file, indent=4)


def load_daily_game_count(count_file="data/json/date_game_count.json"):
    if os.path.exists(count_file):
        try:
            with open(count_file, "r") as file:
                return json.load(file)
        except json.JSONDecodeError:
            print("Warning: corrupted daily count file → reinitializing.")
            return {}
    return {}


def save_daily_game_count(data, count_file="data/json/date_game_count.json"):
    os.makedirs(os.path.dirname(count_file), exist_ok=True)
    with open(count_file, "w") as file:
        json.dump(data, file, indent=4)


def update_daily_game_count(game_name, count_file="data/json/date_game_count.json"):
    today = datetime.datetime.now().strftime("%d-%m-%Y")
    data = load_daily_game_count(count_file)

    data.setdefault(today, {})
    data[today][game_name] = data[today].get(game_name, 0) + 1
    count = data[today][game_name]

    save_daily_game_count(data)
    return get_ordinal(count), today


def get_ordinal(n):
    return f"{n}{'th' if 4 <= n % 100 <= 20 else {1:'st',2:'nd',3:'rd'}.get(n%10,'th')}"


def get_latest_video_any(path):
    """Return newest .mp4 or .mkv video."""
    files = glob.glob(os.path.join(path, "*.mp4")) + glob.glob(
        os.path.join(path, "*.mkv")
    )
    return max(files, key=os.path.getmtime) if files else None


def upload_newest_file(folder_path, dest_directory):
    """Find newest file in folder and upload it to SFTP."""
    try:
        files = [
            os.path.join(folder_path, f)
            for f in os.listdir(folder_path)
            if os.path.isfile(os.path.join(folder_path, f))
        ]
        if not files:
            print(f"No files found in {folder_path} for upload.")
            return
        newest_file = max(files, key=os.path.getctime)
        print(f"Uploading newest file: {newest_file}")
        upload_file_to_sftp(local_file_path=newest_file, dest_directory=dest_directory)
        print(f"Uploaded successfully -> {dest_directory}")
    except Exception as e:
        print(f"Error uploading from {folder_path}: {e}")


# ------------------ MAIN PROGRAM ------------------


def main():
    """Rename and upload latest gaze/input/emotion/video files."""

    class DualInputDialog(simpledialog.Dialog):
        def body(self, master):
            tk.Label(master, text="In-game name:").grid(row=0, column=0, sticky="e")
            tk.Label(master, text="Game:").grid(row=1, column=0, sticky="e")

            mapping = load_mapping()
            self.player_combobox = ttk.Combobox(master, values=sorted(mapping.keys()))
            self.player_combobox.grid(row=0, column=1)

            self.game_combobox = ttk.Combobox(
                master,
                values=["valorant", "league_of_legends", "other"],
                state="readonly",
            )
            self.game_combobox.set("valorant")
            self.game_combobox.grid(row=1, column=1)
            return self.player_combobox

        def apply(self):
            self.player_name = self.player_combobox.get().strip()
            self.game_name = self.game_combobox.get().strip().lower()

    # Load session context if present (Electron app may write this)
    session_context = load_session_context()
    player_name = session_context.get("player_name")
    game_name = session_context.get("normalized_game") or session_context.get("game")

    if not player_name and session_context.get("riot_id"):
        player_name = session_context.get("riot_id", "").split("#", 1)[0]

    # If no session context was loaded (empty dict), show popup to collect details
    popup_used = False
    if not session_context:
        # Show the DualInputDialog (comboboxes) to capture player_name and game_name
        root = tk.Tk()
        root.withdraw()
        dialog = DualInputDialog(root, title="Enter Player & Game Info")
        player_name = getattr(dialog, "player_name", None)
        game_name = getattr(dialog, "game_name", None)

        if not player_name or not game_name:
            print("POPUP_CANCELLED")
            sys.exit(2)

        popup_used = True
        print("POPUP_SHOWN")

    # Load mapping early to allow a silent fallback when there is no session context.
    mapping = load_mapping()

    # If no session context, try to auto-select an existing mapped player.
    if not player_name:
        if mapping:
            # Choose the player with the highest numeric P id (most recently added)
            try:

                def id_num(k):
                    v = mapping.get(k, "P0")
                    return int(v[1:]) if len(v) > 1 and v[1:].isdigit() else 0

                player_name = max(mapping.keys(), key=id_num)
            except Exception:
                # fallback to the first mapping key
                player_name = sorted(mapping.keys())[0]
        else:
            # No mapping exists — create an automatic player entry and use it silently
            auto_name = f"AUTO_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            mapping[auto_name] = get_next_player_id(mapping)
            save_mapping(mapping)
            player_name = auto_name

    # If still no game_name, default to 'other' to avoid showing GUI
    if not game_name:
        game_name = "other"

    game_name = normalize_game_name(game_name)

    # Assign player ID
    mapping = load_mapping()
    if player_name not in mapping:
        mapping[player_name] = get_next_player_id(mapping)
        save_mapping(mapping)

    player_id = mapping[player_name]

    # Construct filename pattern
    ordinal, today = update_daily_game_count(game_name)
    now = datetime.datetime.now().strftime("%H-%M-%S")
    base_name = f"{ordinal}_game_{player_id}_{game_name}_{today}_{now}"

    # ------------------ Handle CSV files ------------------
    for folder, tag in {
        "data/input": "input",
        "data/gaze": "gaze",
        "data/emotion": "emotion",
    }.items():
        latest = get_latest_file(folder)
        if latest:
            new_path = os.path.join(folder, f"{base_name}_{tag}.csv")
            os.replace(latest, new_path)
            print(f"Renamed {tag}: {latest} -> {new_path}")
        else:
            print(f"No {tag} file found in {folder}")

    # ------------------ Handle Video ------------------

    # Source: current Windows user's Videos folder
    video_source_folder = os.path.join(os.path.expanduser("~"), "Videos")

    # Destination: research_software/data/video inside Documents
    video_save_dir = os.path.join(
        os.path.expanduser("~"), "Documents", "research_software", "data", "video"
    )
    os.makedirs(video_save_dir, exist_ok=True)

    latest_video = get_latest_video_any(video_source_folder)

    if latest_video:
        ext = os.path.splitext(latest_video)[1]  # keep original extension
        new_video_path = os.path.join(video_save_dir, f"{base_name}{ext}")
        os.replace(latest_video, new_video_path)
        print(f"Renamed video: {latest_video} -> {new_video_path}")
    else:
        print(f"No video file found in {video_source_folder}")

    # ------------------ Upload Files ------------------
    print("Waiting 5 seconds before uploading...")
    time.sleep(5)

    upload_newest_file("data/emotion", "/data/emotion/")
    upload_newest_file("data/input", "/data/input/")
    upload_newest_file("data/gaze", "/data/gaze/")
    upload_newest_file(video_save_dir, "/data/video/")


if __name__ == "__main__":
    main()
