import random
from collections import defaultdict
from collections import deque
from threading import Timer

import pretty_midi
import pygame as pg
import pygame.midi as pg_midi

from data import load_data
from streaming.midi_objects import MidiNote, MidiSong


class MidiUi:

    def __init__(self, screen_width=960, screen_height=540):
        print("Initializing system...")
        pg.init()
        pg.font.init()
        pg.fastevent.init()
        pg_midi.init()

        self.screen = pg.display.set_mode(size=(screen_width, screen_height))

        # Configure I/O
        self.midi_input = get_midi_input()
        self.midi_out = pg_midi.Output(pg_midi.get_default_output_id())
        self.midi_out.set_instrument(25, channel=0)  # ID 25 = acoustic guitar (steel)
        self.midi_out.set_instrument(22, channel=1)  # ID 22 = harmonica

        # Channel 5-15 are reserved for autoplay
        for a in range(11, 15 + 1, 1):
            self.midi_out.set_instrument(0, channel=a)  # ID 0 = grand acoustic piano

        # Configure MIDI queues
        # - channel => list
        self.midi_queue = {}

        # Configure UI display content
        self.manual_active_notes = defaultdict(set)
        self.auto_active_notes = defaultdict(set)

        print("System started!")
        self.is_active = True
        self.main_loop()

    def update(self):
        """ Called every tick until Ctrl+C is detected"""
        # Handle MIDI events
        if self.midi_input and self.midi_input.poll():
            midi_events = self.midi_input.read(1)
            pitch = midi_events[0][0][1]
            volume = midi_events[0][0][2]
            method = self.note_on if volume != 0 else self.note_off
            method(pitch, channel=0)  # note: we are ignoring volume for now

        # Play queued notes
        for channel, queue in self.midi_queue.items():
            while queue:
                start_time, note = queue[0]
                if start_time > pg.time.get_ticks():
                    break
                queue.popleft()
                self.note_on(note.pitch, volume=100, activation="auto", channel=channel)
                Timer(note.get_duration(), self.note_off, [note.pitch], {
                    "activation": "auto",
                    "channel": channel
                }).start()

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
        message = f"Manual channels:"
        text_image = pg.font.SysFont("Consolas", 24).render(message, False, get_color_tuple("FFFFFF"))
        self.screen.blit(text_image, (text_x_start, text_y_start))
        text_y_start += 40

        # Manual channels
        for a in [0, 1]:
            message = f"Ch#{a:02d}: {', '.join(str(pretty_midi.note_number_to_name(a)) for a in self.manual_active_notes[a])}"
            text_image = pg.font.SysFont("Consolas", 24).render(message, False, get_color_tuple("FFFFFF"))
            self.screen.blit(text_image, (text_x_start, text_y_start))
            text_y_start += 40
        text_y_start += 20

        # Auto channels
        # Autoplay active notes
        message = f"Auto channels ({self.queue_length()}):"
        text_image = pg.font.SysFont("Consolas", 24).render(message, False, get_color_tuple("FFFFFF"))
        self.screen.blit(text_image, (text_x_start, text_y_start))
        text_y_start += 40

        for a in range(11, 15 + 1, 1):
            message = f"Ch#{a:02d}: {', '.join(str(pretty_midi.note_number_to_name(a)) for a in self.auto_active_notes[a])}"
            text_image = pg.font.SysFont("Consolas", 24).render(message, False, get_color_tuple("FFFFFF"))
            self.screen.blit(text_image, (text_x_start, text_y_start))
            text_y_start += 40

        text_y_start = self.draw_staff(text_x_start, text_y_start, "treble")
        text_y_start = self.draw_staff(text_x_start, text_y_start, "bass")

        # Update display
        pg.display.update()

    def draw_staff(self, x, y, staff_type, color="AAAAAA", max_width=600):
        y_initial = y
        y += 5
        for a in range(5):
            pg.draw.rect(self.screen, get_color_tuple(color), [x, y, max_width, 2])
            y += 10

        icon = pg.image.load(f"assets/{'treble.png' if staff_type == 'treble' else 'bass.png'}")
        icon = pg.transform.scale(icon, (50, 50))
        self.screen.blit(icon, (x, y_initial))

        # Draw notes
        x_notes = 80
        width_per_second = 100
        current_tick = pg.time.get_ticks() // 1000
        if not self.midi_queue:
            return y + 10

        limit = 20 // len(self.midi_queue)
        for channel, queue in self.midi_queue.items():
            for i, a in enumerate(queue):
                if i > limit:
                    break

                note = a[1]
                if (note.pitch > 64 and staff_type == "bass") or (note.pitch < 64 and staff_type == "treble"):
                    continue
                pg.draw.rect(self.screen, get_color_tuple("FFFFFF"),
                             [x_notes + max(0, note.start - current_tick) * width_per_second,
                              y_initial + note.pitch - 30,
                              note.get_duration() * width_per_second, 5])
                limit += 1

        return y + 10

    def queue_length(self):
        return sum(len(a) for a in self.midi_queue.values())

    def add_note_to_queue(self, note: MidiNote, channel=0):
        if channel not in self.midi_queue:
            self.midi_queue[channel] = deque()
        self.midi_queue[channel].append((pg.time.get_ticks() + note.start * 1000, note))

    def add_song_to_queue(self, song: MidiSong):
        if song is None:
            return
        for i, data in enumerate(song.notes.items()):
            instrument, notes = data
            for note in notes:
                self.add_note_to_queue(note, channel=11 + i)

    # Miscellaneous methods
    def main_loop(self):
        stop = False
        try:
            while not stop:
                # Detect window closing
                for event in pg.event.get():
                    if event.type == pg.QUIT:
                        stop = True
                    elif event.type == pg.KEYDOWN:
                        if event.key == pg.K_z:
                            self.midi_queue.clear()
                            path = load_data.get_all_files()[random.randint(0, 500)]
                            print(path)
                            midi_song = MidiSong.load(path)
                            self.add_song_to_queue(midi_song)

                self.update()
        except KeyboardInterrupt:
            pass
        print("Stopped UI loop!")
        self.teardown()

    def teardown(self):
        print("Shutting down system...")
        self.is_active = False
        del self.midi_input
        del self.midi_out
        pg_midi.quit()
        pg.quit()
        print("Bye!")

    def note_on(self, pitch, volume=100, channel=0, activation="manual"):
        self.midi_out.note_on(pitch, volume, channel=channel)
        if activation == "manual":
            self.manual_active_notes[channel].add(pitch)
        elif activation == "auto":
            self.auto_active_notes[channel].add(pitch)

    def note_off(self, pitch, volume=100, channel=0, activation="manual"):
        if not self.is_active:
            return
        self.midi_out.note_off(pitch, volume, channel=channel)
        if activation == "manual":
            self.manual_active_notes[channel].discard(pitch)
        elif activation == "auto":
            self.auto_active_notes[channel].discard(pitch)


def get_midi_input():
    try:
        return pg_midi.Input(pg_midi.get_default_input_id())
    except pg_midi.MidiException:
        return None


def get_color_tuple(color_hex):
    if color_hex is None:
        color_hex = "11c5bf"
    color_hex = color_hex.replace("#", "")
    return tuple(int(color_hex[i:i + 2], 16) for i in (0, 2, 4))


if __name__ == "__main__":
    midi_ui = MidiUi()
