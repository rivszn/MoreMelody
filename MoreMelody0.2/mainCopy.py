import pyaudio
import wave
import os
import crepe
import math
import numpy as np
import soundfile as sf
from tkinter import Tk, simpledialog
from tkinter.ttk import Button
from midiutil import MIDIFile

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
WAVE_OUTPUT_FILENAME = "recording.wav"
RECORDINGS_DIR = 'recordings'

p = pyaudio.PyAudio()

stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

frames = []
recording = False

note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Create Recordings folder if it does not already exist
if not os.path.exists(RECORDINGS_DIR):
    os.makedirs(RECORDINGS_DIR)

# Recording Toggle
def toggle_recording():
    global recording
    recording = not recording
    button_text = "Stop Recording" if recording else "Start Recording"
    record_button.config(text=button_text)
    print("* recording" if recording else "* done recording")
    
    if not recording:
        stop_recording()
    else:
        start_recording()

def start_recording():
    global frames, stream
    frames = []
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

def add_notes_to_midi(mf, notes, tempo):
    # Define a dictionary to map note names to MIDI note numbers
    note_to_midi = {'C': 12, 'C#': 13, 'Db': 13, 'D': 14, 'D#': 15,
                    'Eb': 15, 'E': 16, 'F': 17, 'F#': 18, 'Gb': 18,
                    'G': 19, 'G#': 20, 'Ab': 20, 'A': 21, 'A#': 22,
                    'Bb': 22, 'B': 23}

    # Add the notes to the MIDI file
    for time_in_seconds, note in notes:
        # Convert time from seconds to beats
        time_in_beats = time_in_seconds * (tempo / 60)
        # Parse the note name and octave
        if len(note) == 2:
            note_name = note[0]
            octave = int(note[1])
        else:
            note_name = note[:2]
            octave = int(note[2])
        # Calculate the MIDI note number
        midi_note = note_to_midi[note_name] + octave * 12
        # Add the note to the MIDI file
        mf.addNote(track=0,
                   channel=0,
                   pitch=midi_note,
                   time=time_in_beats,
                   duration=0.5,
                   volume=100)

# Create a new MIDI file with one track
mf = MIDIFile(1)

# Set the tempo (in beats per minute)
tempo = 120
mf.addTempo(track=0, time=0, tempo=tempo)

def stop_recording():
    stream.stop_stream()
    stream.close()
    p.terminate()

    # Save the audio data to a file in the recordings directory
    filename = get_recording_filename()
    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

    # Load the recorded audio file
    audio, sr = sf.read(filename)

    # Analyze the audio data using CREPE
    time, frequency, confidence, activation = crepe.predict(audio, sr)

    # Map the notes to a timeline
    notes = map_notes(time, frequency)

    print(notes)
    add_notes_to_midi(mf, notes, tempo)

root = Tk()

def get_recording_filename():
    # Create Recordings folder if it does not already exist
    if not os.path.exists(RECORDINGS_DIR):
        os.makedirs(RECORDINGS_DIR)
    
    i = 2
    filename = os.path.join(RECORDINGS_DIR, WAVE_OUTPUT_FILENAME)
    while os.path.exists(filename):
        filename = os.path.join(RECORDINGS_DIR, f'recording_{i}.wav')
        i += 1

    new_filename = get_new_filename()
    if new_filename:
        new_filename = os.path.join(RECORDINGS_DIR, new_filename + '.wav')
        if os.path.exists(new_filename):
            overwrite = simpledialog.askstring("Input", f"{new_filename} already exists. Overwrite? (y/n):", parent=root)
            if overwrite.lower() == 'y':
                filename = new_filename
        else:
            filename = new_filename

    return filename

def get_new_filename():
    return simpledialog.askstring("Input", "Enter new filename (leave blank to keep default):", parent=root)

def map_notes(time, frequency):
    notes = []
    for t, f in zip(time, frequency):
        note = frequency_to_note(f)
        notes.append((t, note))

    return notes

def frequency_to_note(frequency):
    note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    note_number = 12 * (math.log(frequency / 440, 2)) + 69
    octave = int(note_number) // 12 - 1
    note = note_names[int(note_number) % 12]
    return f"{note}{octave}"

def record():
    if recording:
        try:
            if stream.is_active():
                data = stream.read(CHUNK)
                frames.append(data)
        except OSError:
            pass
    root.after(1, record)

root.title("Recorder")
root.geometry("300x100")

record_button = Button(root, text="Start Recording", command=toggle_recording)
record_button.pack(expand=True)

root.after(1, record)
root.mainloop()

with open('output.mid', 'wb') as f:
    mf.writeFile(f)