from __future__ import division
import numpy as np
import unittest2
from frequencyscale import LinearScale, LogScale, FrequencyBand
from weighting import AWeighting
from zounds.timeseries import Seconds, TimeDimension
from zounds.spectral import FrequencyDimension
from zounds.core import ArrayWithUnits, IdentityDimension


class TimeFrequencyRepresentationTests(unittest2.TestCase):
    def test_sum_along_frequency_axis(self):
        td = TimeDimension(Seconds(1), Seconds(1))
        fd = FrequencyDimension(LinearScale(FrequencyBand(20, 22050), 100))
        tf = ArrayWithUnits(np.ones((30, 100)), [td, fd])
        result = tf.sum(axis=1)
        self.assertIsInstance(result, ArrayWithUnits)
        self.assertEqual(1, len(result.dimensions))
        self.assertEqual((30,), result.shape)
        self.assertIsInstance(result.dimensions[0], TimeDimension)

    def test_from_example(self):
        td = TimeDimension(Seconds(1), Seconds(1))
        fd = FrequencyDimension(LinearScale(FrequencyBand(20, 22050), 100))
        tf = ArrayWithUnits(np.ones((30, 100)), [td, fd])
        from_example = ArrayWithUnits.from_example(np.ones((30, 100)), tf)
        self.assertEqual(tf.shape, from_example.shape)
        self.assertItemsEqual(tf.dimensions, from_example.dimensions)

    def test_can_multiply_by_frequency_weighting_linear_scale(self):
        frequency = Seconds(1)
        duration = Seconds(1)
        scale = LinearScale(FrequencyBand(20, 22050), 100)

        td = TimeDimension(frequency, duration)
        fd = FrequencyDimension(scale)

        tf = ArrayWithUnits(np.ones((30, 100)), [td, fd])
        result = tf * AWeighting()
        self.assertIsInstance(result, ArrayWithUnits)
        peak_frequency_band = FrequencyBand(9000, 11000)
        lower_band = FrequencyBand(100, 300)
        peak_slice = np.abs(result[:, peak_frequency_band]).max()
        lower_slice = np.abs(result[:, lower_band]).max()
        self.assertGreater(peak_slice, lower_slice)

    def test_can_multiply_by_frequency_weighting_log_scale(self):
        frequency = Seconds(1)
        duration = Seconds(1)
        scale = LogScale(FrequencyBand(20, 22050), 100)

        td = TimeDimension(frequency, duration)
        fd = FrequencyDimension(scale)

        tf = ArrayWithUnits(np.ones((30, 100)), [td, fd])

        result = tf * AWeighting()
        self.assertIsInstance(result, ArrayWithUnits)
        peak_frequency_band = FrequencyBand(9000, 11000)
        lower_band = FrequencyBand(100, 300)
        peak_slice = np.abs(result[:, peak_frequency_band]).max()
        lower_slice = np.abs(result[:, lower_band]).max()
        self.assertGreater(peak_slice, lower_slice)

    def test_can_multiply_by_array(self):
        frequency = Seconds(1)
        duration = Seconds(1)
        scale = LinearScale(FrequencyBand(20, 22050), 100)
        td = TimeDimension(frequency, duration)
        fd = FrequencyDimension(scale)
        tf = ArrayWithUnits(np.ones((30, 100)), [td, fd])
        result = tf * np.ones(100)
        self.assertIsInstance(result, ArrayWithUnits)
        np.testing.assert_allclose(tf, result)

    def test_can_use_list_of_integers_as_index(self):
        frequency = Seconds(1)
        duration = Seconds(1)
        scale = LinearScale(FrequencyBand(20, 22050), 100)

        td = TimeDimension(frequency, duration)
        fd = FrequencyDimension(scale)

        tf = ArrayWithUnits(np.zeros((30, 100)), [td, fd])

        indexed = tf[[0, 10, 14]]
        self.assertEqual((3, 100), indexed.shape)
        self.assertIsInstance(indexed, ArrayWithUnits)
        self.assertIsInstance(indexed.dimensions[0], IdentityDimension)
        self.assertIsInstance(indexed.dimensions[1], FrequencyDimension)

    def test_can_construct_instance(self):
        frequency = Seconds(1)
        duration = Seconds(1)
        scale = LinearScale(FrequencyBand(20, 22050), 100)
        td = TimeDimension(frequency, duration)
        fd = FrequencyDimension(scale)
        tf = ArrayWithUnits(np.zeros((30, 100)), [td, fd])
        self.assertIsInstance(tf, ArrayWithUnits)

    def test_raises_if_scale_length_does_not_match_frequency_dimension(self):
        frequency = Seconds(1)
        duration = Seconds(1)
        scale = LinearScale(FrequencyBand(20, 22050), 1000)

        td = TimeDimension(frequency, duration)
        fd = FrequencyDimension(scale)

        self.assertRaises(
                ValueError,
                lambda: ArrayWithUnits(np.ones((30, 100)), [td, fd]))

    def test_can_slice_frequency_dimension_with_integer_indices(self):
        frequency = Seconds(1)
        duration = Seconds(1)
        scale = LinearScale(FrequencyBand(20, 22050), 100)
        td = TimeDimension(frequency, duration)
        fd = FrequencyDimension(scale)
        tf = ArrayWithUnits(np.zeros((30, 100)), [td, fd])
        sliced = tf[:, 10: 20]
        self.assertEqual((30, 10), sliced.shape)
        self.assertIsInstance(sliced, ArrayWithUnits)

    def test_can_slice_frequency_dimensions_with_frequency_band(self):
        frequency = Seconds(1)
        duration = Seconds(1)
        scale = LinearScale(FrequencyBand(20, 22050), 100)
        td = TimeDimension(frequency, duration)
        fd = FrequencyDimension(scale)
        tf = ArrayWithUnits(np.zeros((30, 100)), [td, fd])
        bands = list(scale)
        sliced = tf[:, bands[0]]
        self.assertEqual((30, 1), sliced.shape)
        self.assertIsInstance(sliced, ArrayWithUnits)

    def test_can_slice_freq_dimension_with_freq_band_spanning_bins(self):
        frequency = Seconds(1)
        duration = Seconds(1)
        scale = LinearScale(FrequencyBand(20, 22050), 100)
        td = TimeDimension(frequency, duration)
        fd = FrequencyDimension(scale)
        tf = ArrayWithUnits(np.zeros((30, 100)), [td, fd])
        bands = list(scale)
        wide_band = FrequencyBand(bands[0].start_hz, bands[9].stop_hz)
        sliced = tf[:, wide_band]
        self.assertEqual((30, 10), sliced.shape)
        self.assertIsInstance(sliced, ArrayWithUnits)

    def test_scale_is_modified_after_slice(self):
        frequency = Seconds(1)
        duration = Seconds(1)
        scale = LinearScale(FrequencyBand(20, 22050), 100)
        td = TimeDimension(frequency, duration)
        fd = FrequencyDimension(scale)
        tf = ArrayWithUnits(np.zeros((30, 100)), [td, fd])
        bands = list(scale)
        wide_band = FrequencyBand(bands[0].start_hz, bands[9].stop_hz)
        sliced = tf[:, wide_band]
        self.assertEqual((30, 10), sliced.shape)
        self.assertIsInstance(sliced, ArrayWithUnits)
        self.assertLess(sliced.dimensions[1].scale.stop_hz, scale.stop_hz)
        self.assertEqual(10, sliced.dimensions[1].scale.n_bands)

    def test_ellipsis(self):
        scale = LinearScale(FrequencyBand(0, 10000), 100)
        arr = ArrayWithUnits(
                np.zeros((10, 3, 100)),
                [IdentityDimension(),
                 TimeDimension(Seconds(1)),
                 FrequencyDimension(scale)])
        sliced = arr[..., FrequencyBand(1000, 5000)]
        self.assertEqual((10, 3, 41), sliced.shape)
        self.assertIsInstance(sliced.dimensions[0], IdentityDimension)
        self.assertIsInstance(sliced.dimensions[1], TimeDimension)
        self.assertIsInstance(sliced.dimensions[2], FrequencyDimension)

