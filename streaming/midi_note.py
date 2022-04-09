class MidiNote:
    def __init__(self, pitch, start, end, volume=100):
        self.pitch = pitch
        self.start = start
        self.end = end
        self.volume = volume

    def get_duration(self):
        return self.end - self.start
