import pretty_midi
from mido import KeySignatureError


class MidiNote:
    def __init__(self, pitch, start, end, volume=100):
        self.pitch = pitch
        self.start = start
        self.end = end
        self.volume = volume

    @staticmethod
    def from_note(note):
        return MidiNote(note.pitch, note.start, note.end, note.velocity)

    def get_duration(self):
        return self.end - self.start


class MidiInstrument:
    def __init__(self, name, instrument_type):
        self.name = name
        self.instrument_type = instrument_type


class MidiSong:
    def __init__(self):
        self.instruments = []
        self.notes = {}

    @staticmethod
    def load(path):
        """
        Populate this MIDI song from a midi file path
        Args:
            path (str): file path
        """
        try:
            song = MidiSong()
            midi = pretty_midi.PrettyMIDI(path)

            for pm_instrument in midi.instruments:
                # Create new MidiInstrument
                instr = MidiInstrument(pretty_midi.program_to_instrument_name(pm_instrument.program),
                                       pm_instrument.name)
                song.add_notes(instr, [MidiNote.from_note(note) for note in pm_instrument.notes])

            return song
        except KeySignatureError | FileNotFoundError:
            return None

    def add_note(self, instrument, note):
        """
        Add a note by an instrument
        Args:
            instrument (MidiInstrument): instrument that this note is played with
            note (MidiNote): note to be added
        """
        if instrument not in self.instruments:
            self.instruments.append(instrument)
            self.notes[instrument] = []
        self.notes[instrument].append(note)

    def add_notes(self, instrument, notes):
        """
        Add a list of notes by an instrument
        Args:
            instrument (MidiInstrument): instrument that these notes are played with
            notes (list): list of notes to be added
        """
        if instrument not in self.instruments:
            self.instruments.append(instrument)
            self.notes[instrument] = []
        self.notes[instrument] += notes

    def save(self, path):
        """
        Save the song to a MIDI file
        Args:
            path (str): file path
        """
        pm = pretty_midi.PrettyMIDI()
        for instr, notes in self.notes.items():
            pm_instrument = pretty_midi.Instrument(program=pretty_midi.instrument_name_to_program(instr.name))
            for note in notes:
                pm_note = pretty_midi.Note(
                    velocity=note.velocity,
                    pitch=note.pitch,
                    start=note.start,
                    end=note.end
                )
                pm_instrument.notes.append(pm_note)
            pm.instruments.append(pm_instrument)

        pm.write(path)
        return pm
