from collections import deque
from threading import Timer

import pretty_midi
import pygame as pg
import pygame.midi as pg_midi

from streaming.midi_note import MidiNote


class MidiUi:
    midi_queue: dict[int, deque]

    def __init__(self, screen_width=1920, screen_height=1080):
        print("Initializing system...")
        pg.init()
        pg.font.init()
        pg.fastevent.init()
        pg_midi.init()

        self.screen = pg.display.set_mode(size=(screen_width, screen_height))

        # Configure I/O
        self.midi_input = pg_midi.Input(pg_midi.get_default_input_id())
        self.midi_out = pg_midi.Output(pg_midi.get_default_output_id())
        self.midi_out.set_instrument(0, channel=0)  # ID 0 = grand acoustic piano
        self.midi_out.set_instrument(25, channel=1)  # ID 25 = acoustic guitar (steel)

        # Configure MIDI queues
        # - channel => list
        self.midi_queue = {}

        # Configure UI display content
        self.manual_active_notes = set()
        self.auto_active_notes = set()

        print("System started!")
        self.main_loop()

    def update(self):
        """ Called every tick until Ctrl+C is detected"""
        # Detect window closing
        for event in pg.event.get():
            if event.type == pg.QUIT:
                raise KeyboardInterrupt

        # Handle MIDI events
        if self.midi_input.poll():
            midi_events = self.midi_input.read(1)
            pitch = midi_events[0][0][1]
            volume = midi_events[0][0][2]
            method = self.note_on if volume != 0 else self.note_off
            method(pitch, channel=1)  # note: we are ignoring volume for now
            if method == self.note_on:
                self.add_to_queue(MidiNote(pitch + 12, 0, 0.25), channel=0)

        # Play queued notes
        for channel, queue in self.midi_queue.items():
            if not queue:
                continue
            note: MidiNote = queue[0]
            queue.popleft()
            self.note_on(note.pitch, volume=note.volume, activation="auto")
            Timer(note.get_duration(), self.note_off, [note.pitch], {"activation": "auto"}).start()

        self.update_ui()

    def update_ui(self):
        # Wipe screen
        self.screen.fill(get_color_tuple("000000"))

        margin = 20  # 20 pixels margin
        text_x_start = margin
        text_y_start = margin

        # Title
        message = f"Elapsed: {pg.time.get_ticks() // 1000} seconds"
        text_image = pg.font.SysFont("Consolas", 32).render(message, False, get_color_tuple("FFFFFF"))
        self.screen.blit(text_image, (text_x_start, text_y_start))
        text_y_start += 60

        # Manual active notes
        message = f"Manual: {', '.join(str(pretty_midi.note_number_to_name(a)) for a in self.manual_active_notes)}"
        text_image = pg.font.SysFont("Consolas", 24).render(message, False, get_color_tuple("FFFFFF"))
        self.screen.blit(text_image, (text_x_start, text_y_start))
        text_y_start += 40

        # Autoplay active notes
        message = f"Auto: {', '.join(str(pretty_midi.note_number_to_name(a)) for a in self.auto_active_notes)}"
        text_image = pg.font.SysFont("Consolas", 24).render(message, False, get_color_tuple("FFFFFF"))
        self.screen.blit(text_image, (text_x_start, text_y_start))
        text_y_start += 40

        # Update display
        pg.display.update()

    def add_to_queue(self, note: MidiNote, channel=0):
        if channel not in self.midi_queue:
            self.midi_queue[channel] = deque()
        self.midi_queue[channel].append(note)

    # Miscellaneous methods
    def main_loop(self):
        while True:
            try:
                self.update()
            except KeyboardInterrupt:
                print("Stopped UI loop!")
                break
        self.teardown()

    def teardown(self):
        print("Shutting down system...")
        del self.midi_input
        del self.midi_out
        pg_midi.quit()
        pg.quit()
        print("Bye!")

    def note_on(self, pitch, volume=100, channel=0, activation="manual"):
        self.midi_out.note_on(pitch, volume, channel=channel)
        if activation == "manual":
            self.manual_active_notes.add(pitch)
        elif activation == "auto":
            self.auto_active_notes.add(pitch)

    def note_off(self, pitch, volume=100, channel=0, activation="manual"):
        self.midi_out.note_off(pitch, volume, channel=channel)
        if activation == "manual":
            self.manual_active_notes.discard(pitch)
        elif activation == "auto":
            self.auto_active_notes.discard(pitch)


def get_color_tuple(color_hex):
    if color_hex is None:
        color_hex = "11c5bf"
    color_hex = color_hex.replace("#", "")
    return tuple(int(color_hex[i:i + 2], 16) for i in (0, 2, 4))


if __name__ == "__main__":
    midi_ui = MidiUi()
