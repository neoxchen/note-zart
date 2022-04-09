import time

import pygame
import pygame.midi


def start_stream():
    pygame.init()
    pygame.fastevent.init()
    pygame.midi.init()

    # Configure I/O
    midi_input = pygame.midi.Input(pygame.midi.get_default_input_id())
    midi_out = pygame.midi.Output(pygame.midi.get_default_output_id())
    midi_out.set_instrument(0)  # ID 0 = grand acoustic piano
    # ID 25 = acoustic guitar (steel)

    # Configure window
    pygame.display.set_mode((1, 1), flags=pygame.HIDDEN)

    try:
        while True:
            if midi_input.poll():
                midi_events = midi_input.read(1)
                pitch = midi_events[0][0][1]
                volume = midi_events[0][0][2]
                method = note_on if volume != 0 else note_off
                method(midi_out, pitch)  # note: we are ignoring volume for now
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("Stopped MIDI input loop!")

    del midi_input
    del midi_out
    pygame.midi.quit()
    pygame.quit()


def note_on(midi_out, pitch, volume=100):
    midi_out.note_on(pitch, volume)


def note_off(midi_out, pitch, volume=100):
    midi_out.note_off(pitch, volume)


if __name__ == "__main__":
    start_stream()
