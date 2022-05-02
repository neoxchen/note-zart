import random

import numpy as np
import pandas as pd
import pretty_midi
import tensorflow as tf
from matplotlib import pyplot as plt

from data.load_data import load_pitch_data

###################
# GLOBAL SETTINGS #
###################
LOAD_DATA_USE_CACHE = True
LOAD_DATA_SIZE = 640_000

TRAINING_CALLBACKS = [
    tf.keras.callbacks.ModelCheckpoint(
        filepath="./training_checkpoints/ckpt_{epoch}",
        save_weights_only=True),
    tf.keras.callbacks.EarlyStopping(
        monitor='loss',
        patience=5,
        verbose=1,
        restore_best_weights=True)
]

MAX_TRAIN_EPOCHS = 100


def create_sequences(dataset: tf.data.Dataset, seq_length: int, vocab_size=128) -> tf.data.Dataset:
    """ Returns TF Dataset of sequence and label examples """
    seq_length = seq_length + 1

    # Take 1 extra for the labels
    windows = dataset.window(seq_length, shift=1, stride=1, drop_remainder=True)

    # `flat_map` flattens the" dataset of datasets" into a dataset of tensors
    flatten = lambda x: x.batch(seq_length, drop_remainder=True)
    sequences = windows.flat_map(flatten)

    # Normalize note pitch
    def scale_pitch(x):
        return x / vocab_size

    # Split the labels
    def split_labels(sequences):
        inputs = sequences[:-1]
        labels_dense = sequences[-1]
        labels = {key: labels_dense[i] for i, key in enumerate(["pitch"])}

        return scale_pitch(inputs), labels

    return sequences.map(split_labels, num_parallel_calls=tf.data.AUTOTUNE)


def build_model(seq_length, learning_rate=0.005):
    input_shape = (seq_length, 1)
    inputs = tf.keras.Input(input_shape)

    x = tf.keras.layers.LSTM(512)(inputs)
    x = tf.keras.layers.Dense(512, kernel_regularizer=tf.keras.regularizers.l2(0.001))(x)
    x = tf.keras.layers.Dense(256, kernel_regularizer=tf.keras.regularizers.l2(0.001))(x)

    outputs = {
        "pitch": tf.keras.layers.Dense(128, name="pitch")(x)
    }

    model = tf.keras.Model(inputs, outputs)
    loss = {
        "pitch": tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)
    }

    optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate)
    model.compile(loss=loss, optimizer=optimizer)
    return model


def notes_to_midi_file(starter_notes, notes: pd.DataFrame, out_file: str):
    midi_composer = pretty_midi.PrettyMIDI()
    starter_instrument = pretty_midi.Instrument(
        program=pretty_midi.instrument_name_to_program("Acoustic Guitar (steel)"))
    instrument = pretty_midi.Instrument(program=pretty_midi.instrument_name_to_program("Acoustic Grand Piano"))

    # Add starter notes
    prev_start = 0
    for note in starter_notes:
        start = prev_start + 0.1
        n = pretty_midi.Note(
            velocity=random.randint(80, 120),
            pitch=int(note[0]),
            start=start,
            end=start + random.random(),
        )
        starter_instrument.notes.append(n)
        prev_start = start
    midi_composer.instruments.append(starter_instrument)

    # Add generated notes
    for i, note in notes.iterrows():
        n = pretty_midi.Note(
            velocity=random.randint(80, 120),
            pitch=int(note["pitch"]),
            start=prev_start + note["start"],
            end=prev_start + note["end"],
        )
        instrument.notes.append(n)

    midi_composer.instruments.append(instrument)
    midi_composer.write(out_file)
    return midi_composer


if __name__ == "__main__":
    # Setup workspace
    print("Num GPUs Available: ", len(tf.config.list_physical_devices("GPU")))
    seed = 2022
    tf.random.set_seed(seed)
    np.random.seed(seed)

    # Load data
    print("Loading data...")
    dataset = load_pitch_data(use_cache=LOAD_DATA_USE_CACHE).reshape((1_406_848, 1))[:LOAD_DATA_SIZE]
    print(f">> {dataset.shape}")
    note_count = len(dataset)

    # Create tensorflow dataset
    print("Creating tensorflow dataset...")
    notes_dataset = tf.data.Dataset.from_tensor_slices(dataset)
    print(f">> {notes_dataset.element_spec}")

    # Create sequences
    seq_length = 64
    vocab_size = 128  # range of pitches supported in pretty_midi
    sequence_dataset = create_sequences(notes_dataset, seq_length, vocab_size)
    print(sequence_dataset.element_spec)

    # Preview sequence
    for seq, target in sequence_dataset.take(1):
        print('sequence shape:', seq.shape)
        print('sequence elements (first 5):', seq[0: 5])
        print('target:', target)

    # Prepare training dataset
    batch_size = 512
    buffer_size = note_count - seq_length  # the number of items in the dataset
    train_dataset = (sequence_dataset
                     .shuffle(buffer_size)
                     .batch(batch_size, drop_remainder=True)
                     .cache()
                     .prefetch(tf.data.experimental.AUTOTUNE))

    # Build model
    model = build_model(seq_length)
    model.summary()

    # Train model
    history = model.fit(
        train_dataset,
        epochs=MAX_TRAIN_EPOCHS,
        callbacks=TRAINING_CALLBACKS,
    )

    # Plot training loss
    plt.plot(history.epoch, history.history['loss'], label='total loss')
    plt.show()
