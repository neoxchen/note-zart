import glob

import numpy as np
import pretty_midi as pm
from mido.midifiles.meta import KeySignatureError

from streaming.midi_objects import MidiSong

CHUNK_SIZE = 64

BASE_DATA_PATH = "D:/CMU HW/17644"
DATASET_INFO = {
    "MAESTRO": {
        "path": "maestro-v3.0.0",
        "glob_params": "**/*.mid*"
    },
    "ADL": {
        "path": "adl-piano-midi",
        "glob_params": "Classical/**/**/*.mid*"
    },
	"LMD": {
        "path": "lmd_matched",
        "glob_params": "*/*/*/*/*.mid"
    }
}

CACHE_PATH = "C:/One/CMU/DeepLearning/note-zart/data/caches"


def test_play(file_name):
    """
    Use the PyGame library to play the MIDI file (out loud)
    Args:
        file_name (str): path to the MIDI file
    """
    import pygame

    print(f"Test playing MIDI file: {file_name}...")
    if not pygame.mixer.init():
        pygame.mixer.init()
    clock = pygame.time.Clock()
    pygame.mixer.music.load(file_name)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        clock.tick(30)


def get_all_files(dataset_name="LMD"):
    """
    Fetches all files from a particular dataset
    Args:
        dataset_name (str): dataset name, use keys of DATASET_INFO
    Returns:
        List(str): paths to the MIDI files
    """
    dataset_info = DATASET_INFO[dataset_name]
    print("Enter the BASE_DATA_PATH")
    base_data_path = input()
    print(base_data_path)
    BASE_DATA_PATH =base_data_path
    return glob.glob(f"{BASE_DATA_PATH}/{dataset_info['path']}/{dataset_info['glob_params']}")


def parse_midi(path):
    try:
        midi = pm.PrettyMIDI(path)
    except FileNotFoundError | KeySignatureError:
        return None
    return midi


def load_pitch_data(use_cache=False):
    if use_cache:
        with open(f"{CACHE_PATH}/pitch_only_chunk_{CHUNK_SIZE}.npy", "rb") as f:
            data = np.load(f)
        return data

    def get_pitch_data(midi):
        # Combine all instruments into one big note gallery for now
        notes = []
        for instrument in midi.instruments:
            notes += instrument.notes
        # NOTE: THIS IS CREATING AN ONE-ELEMENT ARRAY, MIGHT BREAK THINGS
        return [[note.pitch] for note in notes]

    paths = get_all_files(dataset_name="ADL")
    data = []
    for path in paths:
        midi = parse_midi(path)
        if not midi:
            continue
        pitches = get_pitch_data(midi)

        # Split MIDIs into chunks of size=CHUNK_SIZE
        for chunk in split_chunks(pitches, CHUNK_SIZE):
            if len(chunk) != CHUNK_SIZE:
                continue
            data.append(chunk)

    data = np.array(data)
    with open(f"{CACHE_PATH}/pitch_only_chunk_{CHUNK_SIZE}.npy", "wb") as f:
        np.save(f, data)
    return data


def split_chunks(to_split, chunk_size):
    """
    Yield successive n-sized chunks from a list
    Args:
        to_split (list): the list to be split
        chunk_size (int): how big each chunk is
    """
    for i in range(0, len(to_split), chunk_size):
        yield np.array(to_split[i:i + chunk_size])


if __name__ == "__main__":
    song = MidiSong.load(get_all_files()[0])
