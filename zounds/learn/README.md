One of Zounds' motivations is to help organize machine learning experiments
dealing with audio.

Zounds' focus is currently more on unsupervised learning, and doesn't currently
have great mechanics for supervised learning experiments.

The following code:

- downloads several [bach piano pieces from internet archive](https://archive.org/details/AOC11B)
- extracts features and stores them in an [LMDB database](https://symas.com/lightning-memory-mapped-database/)
- Learns and stores pipeline that includes some pre-processing, and a [pytorch autoencoder](https://github.com/pytorch/pytorch)
- Exercises the learned model and starts up an in-browser REPL so that a human can evaluate the generated samples


```python
import featureflow as ff
import zounds
import numpy as np
from torch import nn, optim
from random import choice

samplerate = zounds.SR11025()
BaseModel = zounds.stft(resample_to=samplerate, store_fft=True)

scale = zounds.GeometricScale(
    start_center_hz=300,
    stop_center_hz=3040,
    bandwidth_ratio=0.016985,
    n_bands=300)
scale.ensure_overlap_ratio(0.5)


@zounds.simple_lmdb_settings('bach', map_size=1e10, user_supplied_id=True)
class Sound(BaseModel):
    """
    An audio processing pipeline that computes a frequency domain representation
    of the sound that follows a geometric scale
    """
    bark = zounds.ArrayWithUnitsFeature(
        zounds.BarkBands,
        samplerate=samplerate,
        stop_freq_hz=samplerate.nyquist,
        needs=BaseModel.fft,
        store=True)

    long_windowed = zounds.ArrayWithUnitsFeature(
        zounds.SlidingWindow,
        wscheme=zounds.SampleRate(
            frequency=zounds.Milliseconds(340),
            duration=zounds.Milliseconds(680)),
        wfunc=zounds.OggVorbisWindowingFunc(),
        needs=BaseModel.resampled,
        store=True)

    long_fft = zounds.ArrayWithUnitsFeature(
        zounds.FFT,
        needs=long_windowed,
        store=True)

    freq_adaptive = zounds.FrequencyAdaptiveFeature(
        zounds.FrequencyAdaptiveTransform,
        transform=np.fft.irfft,
        scale=scale,
        window_func=np.hanning,
        needs=long_fft,
        store=False)


class InnerLayer(nn.Module):
    """
    A single, hidden layer of our simple autoencoder
    """
    def __init__(self, in_size, out_size):
        super(InnerLayer, self).__init__()
        self.linear = nn.Linear(in_size, out_size, bias=False)
        self.relu = nn.LeakyReLU(0.2)

    def forward(self, inp):
        x = self.linear(inp)
        x = self.relu(x)
        return x


class OutputLayer(nn.Module):
    """
    The output layer of our simple autoencoder
    """
    def __init__(self, in_size, out_size):
        super(OutputLayer, self).__init__()
        self.linear = nn.Linear(in_size, out_size, bias=False)
        self.tanh = nn.Tanh()

    def forward(self, inp):
        x = self.linear(inp)
        x = self.tanh(x)
        return x


class AutoEncoder(nn.Module):
    """
    A simple autoencoder.  No bells, whistles, or convolutions
    """
    def __init__(self):
        super(AutoEncoder, self).__init__()
        self.encoder = nn.Sequential(
            InnerLayer(8192, 1024),
            InnerLayer(1024, 512),
            InnerLayer(512, 256))
        self.decoder = nn.Sequential(
            InnerLayer(256, 512),
            InnerLayer(512, 1024),
            OutputLayer(1024, 8192))

    def forward(self, inp):
        encoded = self.encoder(inp)
        decoded = self.decoder(encoded)
        return decoded


@zounds.simple_settings
class FreqAdaptiveAutoEncoder(ff.BaseModel):
    """
    Define a processing pipeline to learn a compressed representation of the
    Sound.freq_adaptive feature.  Once this is trained and the pipeline is
    stored, we can apply all the pre-processing steps and the autoencoder
    forward and in reverse.
    """
    docs = ff.Feature(
        ff.IteratorNode,
        store=False)

    shuffle = zounds.ArrayWithUnitsFeature(
        zounds.ReservoirSampler,
        nsamples=1e5,
        needs=docs,
        store=True)

    log = ff.PickleFeature(
        zounds.Log,
        needs=shuffle,
        store=False)

    scaled = ff.PickleFeature(
        zounds.InstanceScaling,
        needs=log,
        store=False)

    autoencoder = ff.PickleFeature(
        zounds.PyTorchAutoEncoder,
        model=AutoEncoder(),
        loss=nn.MSELoss(),
        optimizer_func=lambda ae: optim.Adam(
            ae.parameters(), lr=0.00005, betas=(0.5, 0.999)),
        epochs=40,
        batch_size=64,
        needs=scaled,
        store=False)

    # assemble the previous steps into a re-usable pipeline, which can perform
    # forward and backward transformations
    pipeline = ff.PickleFeature(
        zounds.PreprocessingPipeline,
        needs=(log, scaled, autoencoder),
        store=True)


if __name__ == '__main__':

    # download a set of bach piano pieces, compute and store features
    for request in zounds.InternetArchive('AOC11B'):
        if Sound.exists(request.url):
            print '{request.url} is already processed'.format(**locals())
            continue
        Sound.process(meta=request, _id=request.url)
        print 'processed {request.url}'.format(**locals())

    # train the pipeline, including the autoencoder
    try:
        FreqAdaptiveAutoEncoder.process(
            docs=(snd.freq_adaptive for snd in Sound),
            raise_if_exists=True)
    except ff.ModelExistsError:
        print 'model already trained'
        pass

    # choose a random bach piece
    snds = list(Sound)
    snd = choice(snds)

    # run the model forward and backward
    autoencoder = FreqAdaptiveAutoEncoder()
    encoded = autoencoder.pipeline.transform(snd.freq_adaptive)
    inverted = encoded.inverse_transform()

    # create a synthesizer that can invert the frequency adaptive representation
    synth = zounds.FrequencyAdaptiveFFTSynthesizer(scale, samplerate)

    # compare the audio of the original and the reconstruction
    original = synth.synthesize(snd.freq_adaptive)
    recon = synth.synthesize(inverted)

    # start up an in-browser REPL to interact with the results
    app = zounds.ZoundsApp(
        model=Sound,
        audio_feature=Sound.ogg,
        visualization_feature=Sound.bark,
        globals=globals(),
        locals=locals())
    app.start(8888)

```