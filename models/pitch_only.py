import collections
import datetime
import glob
import numpy as np
import pathlib
import pandas as pd
import pretty_midi
import seaborn as sns
import tensorflow as tf
from matplotlib import pyplot as plt

from data.load_data import *

seed = 2022
tf.random.set_seed(seed)
np.random.seed(seed)

print("Loading data...")
dataset = load_pitch_data(use_cache=True)
print(f">> {dataset.shape}")

print("Creating tensorflow dataset...")
notes_dataset = tf.data.Dataset.from_tensor_slices(dataset)
print(f">> {notes_dataset.element_spec}")


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


seq_length = 64
vocab_size = 128  # range of pitches supported in pretty_midi
seq_ds = create_sequences(notes_dataset, seq_length, vocab_size)
print(seq_ds.element_spec)

for seq, target in seq_ds.take(1):
    print('sequence shape:', seq.shape)
    print('sequence elements (first 10):', seq[0: 10])
    print()
    print('target:', target)
