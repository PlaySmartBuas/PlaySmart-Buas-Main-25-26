import sounddevice as sd
import soundfile as sf
import datetime
import os
import whisper
from pynput import keyboard

samplerate = 44100
channels = 1
recording = True  # control flag

# ------------------ PATH SETUP ------------------
documents = os.path.expanduser("~/Documents")
audio_folder = os.path.join(documents, "research_software", "data", "audio")
os.makedirs(audio_folder, exist_ok=True)

filename = f"audio_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
filepath = os.path.join(audio_folder, filename)

print(f"Recording microphone audio to: {filepath}")
print("Press F12 to stop recording...")

# ------------------ KEY LISTENER ------------------
def on_press(key):
    global recording
    if key == keyboard.Key.f12:
        print("\nF12 pressed → stopping recording...")
        recording = False
        return False  # stop listener

listener = keyboard.Listener(on_press=on_press)
listener.start()

# ------------------ RECORD AUDIO ------------------
with sf.SoundFile(filepath, mode='w', samplerate=samplerate, channels=channels) as file:
    with sd.InputStream(samplerate=samplerate, channels=channels) as stream:
        while recording:
            data, _ = stream.read(1024)
            file.write(data)

print("Recording stopped.")

# ------------------ TRANSCRIPTION ------------------
print("Loading Whisper model...")
model = whisper.load_model("base")  # tiny/base/small/medium/large

print("Transcribing audio...")
result = model.transcribe(filepath)

segments = result["segments"]

# ------------------ FORMAT TRANSCRIPT ------------------
def format_time(seconds):
    return str(datetime.timedelta(seconds=int(seconds)))

formatted_transcript = ""

for seg in segments:
    start = format_time(seg["start"])
    end = format_time(seg["end"])
    text = seg["text"].strip()

    formatted_transcript += f"[{start} - {end}] {text}\n"

print("Transcription with timestamps:\n")
print(formatted_transcript)

# ------------------ SAVE TRANSCRIPT ------------------
txt_path = filepath.replace(".wav", ".txt")

with open(txt_path, "w", encoding="utf-8") as f:
    f.write(formatted_transcript)

print(f"Transcript saved to: {txt_path}")