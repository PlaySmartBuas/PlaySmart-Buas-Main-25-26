# # import os
# # import glob
# # import time
# # from datetime import datetime
# # import pandas as pd
# # import subprocess

# # def get_latest_file(directory, prefix):
# #     """
# #     Get the latest CSV file in the specified directory with a given prefix.
    
# #     Parameters:
# #     - directory (str): The directory to search for files.
# #     - prefix (str): The prefix of the file (e.g., 'gaze_data_' or 'input_log_').
    
# #     Returns:
# #     - str: The path of the latest file that matches the prefix.
# #     - None: If no files are found with the specified prefix.

# #     Authors: Mauro van Hulst
# #     """
# #     print(f"Searching for the latest file with prefix '{prefix}' in the directory '{directory}'...")

# #     # Search for all CSV files in the directory with the specified prefix
# #     list_of_files = glob.glob(os.path.join(directory, f'{prefix}*.csv'))
    
# #     # If no files are found, return None
# #     if not list_of_files:
# #         return None
    
# #     # Sort the files by modification time and return the latest one
# #     latest_file = max(list_of_files, key=os.path.getmtime)
# #     return latest_file

# # def merge_datasets():
# #     """
# #     Merge the latest gaze data, input log, and webcam CSV files based on the 'unix_time' column.
    
# #     The function searches for the latest gaze, keyboard/mouse input log, and webcam log files, loads them as DataFrames,
# #     and merges them on the 'unix_time' column. It processes the gaze data by dropping rows with NaN values,
# #     rounding the gaze data to 3 decimal places, and averaging the left and right gaze data. Finally, the
# #     merged dataset is saved as a CSV file in the '../data/merged' directory.

# #     Returns:
# #     - None

     
# #     """
# #     time.sleep(1)  # Small delay to ensure files are saved before merging

# #     folder_name = 'data'

# #     # latest_gaze_file = get_latest_file(f"{folder_name}/gaze", 'gaze_data_')
# #     # latest_kbm_file = get_latest_file(f"{folder_name}/input", 'input_log_')
# #     # latest_emotion_file = get_latest_file(f"{folder_name}/emotion", 'emotion_data_')
# #     latest_gaze_file = r"C:\Users\pc03\Documents\research_software\data\gaze\2nd_game_P038_valorant_01-04-2026_16-57-51_gaze.csv"
# #     latest_kbm_file = r"C:\Users\pc03\Documents\research_software\data\input\2nd_game_P038_valorant_01-04-2026_16-57-51_input.csv"
# #     latest_emotion_file = r"C:\Users\pc03\Documents\research_software\data\emotion\1st_game_P038_valorant_01-04-2026_16-39-40_emotion.csv"

# #     if not latest_gaze_file or not latest_kbm_file or not latest_emotion_file:
# #         print("Error: One or more CSV files are missing.")
# #         return

# #     print(f"Latest gaze data file: {latest_gaze_file}")
# #     print(f"Latest input log file: {latest_kbm_file}")
# #     print(f"Latest emotion data file: {latest_emotion_file}")

# #     # Load CSV files
# #     df_gaze = pd.read_csv(latest_gaze_file)
# #     df_kbm = pd.read_csv(latest_kbm_file)
# #     df_emotion = pd.read_csv(latest_emotion_file)

# #     # Convert `unix_time` to numeric format
# #     for df, name in zip([df_gaze, df_kbm, df_emotion], ['Gaze', 'Keyboard', 'Emotion']):
# #         if 'unix_time' not in df.columns:
# #             print(f"Error: `unix_time` column missing in {name} dataset.")
# #             return
# #         df['unix_time'] = pd.to_numeric(df['unix_time'], errors='coerce')
# #         df.dropna(subset=['unix_time'], inplace=True)
# #         df['unix_time'] = df['unix_time'].astype(int)  # Ensure integer format

# #     print("All datasets loaded and cleaned successfully.")

# #     # Merge Gaze & Keyboard data
# #     df_merge_1 = pd.merge_asof(
# #         df_gaze.sort_values('unix_time'), 
# #         df_kbm.sort_values('unix_time'), 
# #         on='unix_time', 
# #         direction='nearest', 
# #         tolerance=1000
# #     )

# #     # Merge with Emotion data
# #     df_merge_2 = pd.merge_asof(
# #         df_merge_1.sort_values('unix_time'), 
# #         df_emotion.sort_values('unix_time'), 
# #         on='unix_time', 
# #         direction='nearest', 
# #         tolerance=1000
# #     )

# #     # Drop duplicates based on `unix_time`
# #     df_merge_2.drop_duplicates(subset='unix_time', inplace=True)

# #     # Save merged file
# #     merged_folder = os.path.join(folder_name, 'merged')
# #     os.makedirs(merged_folder, exist_ok=True)
# #     merged_file_path = os.path.join(merged_folder, 'merged_data_' + datetime.now().strftime('%d-%m-%Y_%H-%M-%S') + '.csv')

# #     df_merge_2.to_csv(merged_file_path, index=False)
    
# #     print(f"Merged data saved to: {merged_file_path}")

# # if __name__ == "__main__":
# #     merge_datasets()































# # import os
# # import argparse
# # import pandas as pd
# # from datetime import datetime
 
# # def load_csv_clean_time(path, label):
# #     """Load CSV and normalize unix_time (ms,int64), staying close to original style."""
# #     df = pd.read_csv(path)
# #     if 'unix_time' not in df.columns:
# #         raise ValueError(f"Error: `unix_time` column missing in {label} dataset: {path}")
 
# #     df['unix_time'] = pd.to_numeric(df['unix_time'], errors='coerce')
# #     before = len(df)
# #     df.dropna(subset=['unix_time'], inplace=True)
 
# #     # If it looks like seconds, convert to ms
# #     if not df.empty and df['unix_time'].max() < 1e12:
# #         print(f"[WARNING] {label} may be in seconds; converting to milliseconds.")
# #         df['unix_time'] *= 1000
 
# #     df['unix_time'] = df['unix_time'].astype('int64')
# #     df = df.sort_values('unix_time')
# #     print(f"{label} unix_time range: {df['unix_time'].min()} → {df['unix_time'].max()}  (kept {len(df)}/{before})")
# #     return df
 
# # def common_prefix_from_three(a, b, c):
# #     """Get shared filename prefix up to the last underscore, like original naming."""
# #     prefix = os.path.commonprefix([os.path.basename(a), os.path.basename(b), os.path.basename(c)])
# #     if "_" in prefix:
# #         prefix = prefix[:prefix.rfind("_") + 1]
# #     return prefix if prefix else "merged_"
 
# # def main():
# #     ap = argparse.ArgumentParser(description="Manually merge gaze, kbm, and emotion CSVs (original style) with emotion start auto-align.")
# #     ap.add_argument("--gaze", required=True, help="Path to gaze CSV (e.g., ..._gaze.csv)")
# #     ap.add_argument("--kbm", required=True, help="Path to keyboard/mouse CSV (e.g., ..._input.csv)")
# #     ap.add_argument("--emotion", required=True, help="Path to emotion CSV (e.g., ..._emotion.csv)")
# #     ap.add_argument("--outdir", required=True, help="Output directory")
# #     ap.add_argument("--tolerance", type=int, default=500, help="merge_asof tolerance in ms (default 100)")
# #     ap.add_argument("--no_auto_align", action="store_true",
# #                     help="Disable auto-align (emotion start → earliest of gaze/KBM).")
# #     args = ap.parse_args()
 
# #     # Load and normalize time
# #     print("Loading datasets…")
# #     df_gaze = load_csv_clean_time(args.gaze, "Gaze")
# #     df_kbm  = load_csv_clean_time(args.kbm,  "Keyboard/Mouse")
# #     df_emo  = load_csv_clean_time(args.emotion, "Emotion")
    
 
# #     # ---- Auto-align emotion start to earliest of gaze/KBM ----
# #     if not args.no_auto_align and not df_emo.empty:
# #         earliest_other = min(df_gaze['unix_time'].min(), df_kbm['unix_time'].min())
# #         emo_start = df_emo['unix_time'].min()
# #         offset = int(earliest_other - emo_start)
# #         if offset != 0:
# #             df_emo = df_emo.copy()
# #             df_emo['unix_time'] = df_emo['unix_time'] + offset
# #             print(f"[Emotion] Auto-aligned: shifted by {offset} ms so emotion start matches earliest gaze/KBM.")
# #         else:
# #             print("[Emotion] Auto-align: no shift needed (already aligned).")
# #     else:
# #         print("[Emotion] Auto-align disabled or emotion empty; no shift applied.")
 
# #     # Quick overlap info (post-alignment)
# #     g_min, g_max = df_gaze['unix_time'].min(), df_gaze['unix_time'].max()
# #     e_min, e_max = df_emo['unix_time'].min(), df_emo['unix_time'].max()
# #     overlap = max(0, min(g_max, e_max) - max(g_min, e_min))
# #     if overlap == 0:
# #         print("[WARN] Still no time overlap after alignment. Check if this emotion file matches the game.")
# #     else:
# #         print(f"[Info] Time overlap after alignment: {overlap} ms (~{overlap/1000:.2f}s)")
 
# #     # Merge gaze ↔ kbm
# #     print(f"Merging gaze ↔ kbm (±{args.tolerance} ms)…")
# #     df_merge_1 = pd.merge_asof(
# #         df_gaze.sort_values('unix_time'),
# #         df_kbm.sort_values('unix_time'),
# #         on='unix_time',
# #         direction='nearest',
# #         tolerance=args.tolerance
# #     )
 
# #     # Merge with emotion
# #     print(f"Merging (gaze+kbm) ↔ emotion (±{args.tolerance} ms)…")
# #     df_merge_2 = pd.merge_asof(
# #         df_merge_1.sort_values('unix_time'),
# #         df_emo.sort_values('unix_time'),
# #         on='unix_time',
# #         direction='nearest',
# #         tolerance=args.tolerance
# #     )
 
# #     # Finalize
# #     df_merge_2.drop_duplicates(subset='unix_time', inplace=True)
# #     df_merge_2['datetime'] = pd.to_datetime(df_merge_2['unix_time'], unit='ms')
 
# #     # Output name: keep original prefix
# #     prefix = common_prefix_from_three(args.gaze, args.kbm, args.emotion)
# #     os.makedirs(args.outdir, exist_ok=True)
# #     out_path = os.path.join(args.outdir, f"{prefix}merged.csv")
# #     df_merge_2.to_csv(out_path, index=False)
# #     print(f"Saved → {out_path}")
 
# # if __name__ == "__main__":
# #     main()











# import os
# import argparse
# import pandas as pd
# from datetime import datetime


# def load_csv_clean_time(path, label):
#     """Load CSV and normalize unix_time (ms,int64), staying close to original style."""
#     df = pd.read_csv(path)

#     if 'unix_time' not in df.columns:
#         raise ValueError(f"Error: `unix_time` column missing in {label} dataset: {path}")

#     df['unix_time'] = pd.to_numeric(df['unix_time'], errors='coerce')
#     before = len(df)
#     df.dropna(subset=['unix_time'], inplace=True)

#     # If it looks like seconds, convert to ms
#     if not df.empty and df['unix_time'].max() < 1e12:
#         print(f"[WARNING] {label} may be in seconds; converting to milliseconds.")
#         df['unix_time'] *= 1000

#     df['unix_time'] = df['unix_time'].astype('int64')
#     df = df.sort_values('unix_time')

#     print(f"{label} unix_time range: {df['unix_time'].min()} → {df['unix_time'].max()}  (kept {len(df)}/{before})")
#     return df


# def common_prefix_from_three(a, b, c):
#     prefix = os.path.commonprefix([os.path.basename(a), os.path.basename(b), os.path.basename(c)])
#     if "_" in prefix:
#         prefix = prefix[:prefix.rfind("_") + 1]
#     return prefix if prefix else "merged_"


# def main():
#     ap = argparse.ArgumentParser(
#         description="Merge gaze, kbm, emotion, and eda CSVs with optional alignment."
#     )
#     ap.add_argument("--gaze", required=True)
#     ap.add_argument("--kbm", required=True)
#     ap.add_argument("--emotion", required=True)
#     ap.add_argument("--eda", required=False)
#     ap.add_argument("--outdir", required=True)
#     ap.add_argument("--tolerance", type=int, default=500,
#                     help="merge_asof tolerance in ms (default 500)")
#     ap.add_argument("--no_auto_align", action="store_true")

#     args = ap.parse_args()

#     # ---------------- LOAD ----------------
#     print("Loading datasets…")
#     df_gaze = load_csv_clean_time(args.gaze, "Gaze")
#     df_kbm  = load_csv_clean_time(args.kbm, "Keyboard/Mouse")
#     df_emo  = load_csv_clean_time(args.emotion, "Emotion")
#     df_eda  = load_csv_clean_time(args.eda, "EDA") if args.eda else None

#     # ---------------- ALIGN EMOTION ----------------
#     if not args.no_auto_align and not df_emo.empty:
#         earliest_other = min(df_gaze['unix_time'].min(), df_kbm['unix_time'].min())
#         emo_start = df_emo['unix_time'].min()
#         offset = int(earliest_other - emo_start)

#         if offset != 0:
#             df_emo = df_emo.copy()
#             df_emo['unix_time'] += offset
#             print(f"[Emotion] Auto-aligned: shifted by {offset} ms.")
#         else:
#             print("[Emotion] Auto-align: no shift needed.")

#     # ---------------- ALIGN EDA ----------------
#     if df_eda is not None and not df_eda.empty and not args.no_auto_align:
#         earliest_other = min(df_gaze['unix_time'].min(), df_kbm['unix_time'].min())
#         eda_start = df_eda['unix_time'].min()
#         offset = int(earliest_other - eda_start)

#         # if offset != 0:
#             df_eda = df_eda.copy()
#             df_eda['unix_time'] += offset
#             print(f"[EDA] Auto-aligned: shifted by {offset} ms.")
#         else:
#             print("[EDA] Auto-align: no shift needed.")

#     # ---------------- MERGE ----------------
#     print(f"Merging gaze ↔ kbm (±{args.tolerance} ms)…")
#     df_merge = pd.merge_asof(
#         df_gaze,
#         df_kbm,
#         on='unix_time',
#         direction='nearest',
#         tolerance=args.tolerance
#     )

#     print(f"Merging with emotion (±{args.tolerance} ms)…")
#     df_merge = pd.merge_asof(
#         df_merge,
#         df_emo,
#         on='unix_time',
#         direction='nearest',
#         tolerance=args.tolerance
#     )

#     # ---------------- MERGE EDA ----------------
#     if df_eda is not None:
#         print(f"Merging with EDA (±{args.tolerance} ms)…")

#         # Prevent column collisions
#         df_eda = df_eda.add_prefix("eda_")
#         df_eda.rename(columns={"eda_unix_time": "unix_time"}, inplace=True)

#         df_merge = pd.merge_asof(
#             df_merge,
#             df_eda,
#             on='unix_time',
#             direction='nearest',
#             tolerance=args.tolerance
#         )

#     # ---------------- FINALIZE ----------------
#     df_merge.drop_duplicates(subset='unix_time', inplace=True)
#     df_merge['datetime'] = pd.to_datetime(df_merge['unix_time'], unit='ms')

#     prefix = common_prefix_from_three(args.gaze, args.kbm, args.emotion)
#     os.makedirs(args.outdir, exist_ok=True)
#     out_path = os.path.join(args.outdir, f"{prefix}merged.csv")

#     df_merge.to_csv(out_path, index=False)
#     print(f"Saved → {out_path}")


# if __name__ == "__main__":
#     main()

import os
import glob
import re
import argparse
import pandas as pd
 
 
# ------------------ BASE PATH ------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
 
 
# ------------------ HELPERS ------------------
 
def extract_session_id(path):
    name = os.path.basename(path)
    parts = name.split("_")
    return "_".join(parts[:-1])  # remove _tag
 
 
def session_time(session):
    """
    Extract datetime from session ID using regex.
    """
    match = re.search(r"(\d{2}-\d{2}-\d{4})_(\d{2}-\d{2}-\d{2})", session)
 
    if not match:
        raise ValueError(f"Cannot parse session time from: {session}")
 
    return pd.to_datetime(
        f"{match.group(1)} {match.group(2)}",
        format="%d-%m-%Y %H-%M-%S"
    )
 
 
def get_sessions(folder, tag):
    files = glob.glob(os.path.join(folder, f"*_{tag}.csv"))
 
    sessions = {}
    for f in files:
        session = extract_session_id(f)
        sessions.setdefault(session, []).append(f)
 
    return sessions
 
 
# ------------------ LOADER ------------------
 
def load_csv_clean_time(path, label):
    df = pd.read_csv(path)
 
    if 'unix_time' not in df.columns:
        raise ValueError(f"{label}: missing 'unix_time' column")
 
    before = len(df)
 
    df['unix_time'] = pd.to_numeric(df['unix_time'], errors='coerce')
 
    # seconds → ms
    if df['unix_time'].max() < 1e12:
        print(f"[WARNING] {label} in seconds → converting to ms")
        df['unix_time'] *= 1000
 
    df['unix_time'] = df['unix_time'].round()
    df.dropna(subset=['unix_time'], inplace=True)
 
    if df.empty:
        raise ValueError(f"{label} empty after cleaning")
 
    df['unix_time'] = df['unix_time'].astype('int64')
    df = df.sort_values('unix_time')
 
    print(f"{label}: {df['unix_time'].min()} → {df['unix_time'].max()} ({len(df)}/{before})")
 
    return df
 
 
# ------------------ MAIN ------------------
 
def main():
    ap = argparse.ArgumentParser(description="Merge gaze, KBM, emotion, and EDA")
 
    ap.add_argument("--gaze")
    ap.add_argument("--kbm")
    ap.add_argument("--emotion")
    ap.add_argument("--eda", required=False)
    ap.add_argument("--outdir", required=True)
 
    ap.add_argument("--tolerance", type=int, default=500)
    ap.add_argument("--auto", action="store_true")
    ap.add_argument("--no_auto_align", action="store_true")
 
    args = ap.parse_args()
 
 
    # ---------------- AUTO MODE ----------------
    if args.auto:
        print("[AUTO] Searching for complete session...")
 
        gaze_sessions = get_sessions(os.path.join(BASE_DIR, "data/gaze"), "gaze")
        kbm_sessions  = get_sessions(os.path.join(BASE_DIR, "data/input"), "input")
        emo_sessions  = get_sessions(os.path.join(BASE_DIR, "data/emotion"), "emotion")
        eda_sessions  = get_sessions(os.path.join(BASE_DIR, "data/eda"), "eda")
 
        common = (
            set(gaze_sessions.keys())
            & set(kbm_sessions.keys())
            & set(emo_sessions.keys())
        )
 
        if not common:
            raise ValueError("❌ No complete session found")
 
        best_session = max(common, key=session_time)
 
        args.gaze = gaze_sessions[best_session][0]
        args.kbm = kbm_sessions[best_session][0]
        args.emotion = emo_sessions[best_session][0]
        args.eda = eda_sessions.get(best_session, [None])[0]
 
        print("\n✅ Selected session:", best_session)
        print("gaze:", args.gaze)
        print("kbm:", args.kbm)
        print("emotion:", args.emotion)
        print("eda:", args.eda)
 
 
    # ---------------- LOAD DATA ----------------
    print("\nLoading datasets...")
 
    df_gaze = load_csv_clean_time(args.gaze, "Gaze")
    df_kbm  = load_csv_clean_time(args.kbm, "KBM")
    df_emo  = load_csv_clean_time(args.emotion, "Emotion")
 
    df_eda = None
    if args.eda:
        df_eda = load_csv_clean_time(args.eda, "EDA")
 
 
    # ---------------- ALIGN ----------------
    if not args.no_auto_align:
        earliest = min(df_gaze['unix_time'].min(), df_kbm['unix_time'].min())
 
        emo_offset = int(earliest - df_emo['unix_time'].min())
        df_emo['unix_time'] += emo_offset
 
        if df_eda is not None:
            eda_offset = int(earliest - df_eda['unix_time'].min())
            df_eda['unix_time'] += eda_offset
 
 
    # ---------------- MERGE ----------------
    print("\nMerging gaze + KBM...")
 
    df_merge = pd.merge_asof(
        df_gaze,
        df_kbm,
        on='unix_time',
        direction='nearest',
        tolerance=args.tolerance
    )
 
    print("Merging emotion...")
 
    df_merge = pd.merge_asof(
        df_merge,
        df_emo,
        on='unix_time',
        direction='nearest',
        tolerance=args.tolerance
    )
 
    if df_eda is not None:
        print("Merging EDA...")
 
        df_merge = pd.merge_asof(
            df_merge,
            df_eda,
            on='unix_time',
            direction='nearest',
            tolerance=args.tolerance
        )
    else:
        print("[EDA] Skipped")
 
 
    # ---------------- SAVE ----------------
    df_merge['datetime'] = pd.to_datetime(df_merge['unix_time'], unit='ms')
 
    prefix = extract_session_id(args.gaze) + "_"
 
    os.makedirs(args.outdir, exist_ok=True)
 
    out_path = os.path.join(args.outdir, f"{prefix}merged.csv")
    df_merge.to_csv(out_path, index=False)
 
    print(f"\nSaved → {out_path}")
 
 
if __name__ == "__main__":
    main()