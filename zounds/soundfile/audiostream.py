from io import BytesIO
from os import SEEK_END
from soundfile import SoundFile
from zounds.timeseries import audio_sample_rate, AudioSamples
from .byte_depth import chunk_size_samples
from featureflow import Node


class AudioStream(Node):
    """
    `AudioStream` expects to process a raw stream of bytes (e.g. one
    produced by :class:`featureflow.ByteStream`) and produces chunks of
    :class:`~zounds.timeseries.AudioSamples`

    Args:
        sum_to_mono (bool): True if this node should return a
            :class:`~zounds.timeseries.AudioSamples` instance with a single
            channel
        needs (Feature): a processing node that produces a byte stream (e.g.
            :class:`~featureflow.ByteStream`

    Here's how'd you typically see :class:`AudioStream` used in a processing
    graph.

    .. code:: python

        import featureflow as ff
        import zounds

        chunksize = zounds.ChunkSizeBytes(
            samplerate=zounds.SR44100(),
            duration=zounds.Seconds(30),
            bit_depth=16,
            channels=2)

        @zounds.simple_in_memory_settings
        class Document(ff.BaseModel):
            meta = ff.JSONFeature(
                zounds.MetaData,
                store=True,
                encoder=zounds.AudioMetaDataEncoder)

            raw = ff.ByteStreamFeature(
                ff.ByteStream,
                chunksize=chunksize,
                needs=meta,
                store=False)

            pcm = zounds.AudioSamplesFeature(
                zounds.AudioStream,
                needs=raw,
                store=True)


        synth = zounds.NoiseSynthesizer(zounds.SR11025())
        samples = synth.synthesize(zounds.Seconds(10))
        raw_bytes = samples.encode()
        _id = Document.process(meta=raw_bytes)
        doc = Document(_id)
        print doc.pcm.__class__  # returns an AudioSamples instance
    """

    def __init__(
            self,
            sum_to_mono=True,
            needs=None):

        super(AudioStream, self).__init__(needs=needs)
        self._sum_to_mono = sum_to_mono
        self._buf = None
        self._sf = None
        self._chunk_size_samples = None
        self._cache = b''

    def _enqueue(self, data, pusher):
        self._cache += data

    def _dequeue(self):
        v = self._cache
        self._cache = b''
        return v

    def _get_samples(self):
        raw_samples = self._sf.read(self._chunk_size_samples)
        sr = audio_sample_rate(self._sf.samplerate)
        samples = AudioSamples(raw_samples, sr)
        if self._sum_to_mono:
            return samples.mono
        return samples

    def _process(self, data):
        b = data

        # TODO: Use the _first_chunk() hook instead of the if statement
        if self._buf is None:
            self._buf = MemoryBuffer(b.total_length)

        self._buf.write(b)

        if self._sf is None:
            self._sf = SoundFile(self._buf)

        if self._chunk_size_samples is None:
            self._chunk_size_samples = chunk_size_samples(self._sf, b)

        yield self._get_samples()

    def _last_chunk(self):
        samples = self._get_samples()
        while samples.size:
            yield samples
            samples = self._get_samples()


class MemoryBuffer(object):
    """
    This class is the implementation of the virtual io interface required by
    PySoundfile/libsndfile.

    Some of the stateful/hacky things in this class (see KLUDGE note below)
    could be avoided if this class had the following modifications:
        - it maintains its own position
        - it maintains the span of its buffer/BytesIO instance
        -
    """

    def __init__(self, content_length, max_size=10 * 1024 * 1024):
        super(MemoryBuffer, self).__init__()
        self._content_length = content_length
        self._buf = BytesIO()
        self._max_size = max_size
        self.tell = self._tell

        self._total_bytes_written = 0
        self._total_bytes_read = 0

    def read(self, count):
        if count == -1:
            return self._buf.read()
        data = self._buf.read(count)
        return data

    def readinto(self, buf):
        data = self.read(len(buf))
        ld = len(data)
        buf[:ld] = data
        return ld

    def write(self, data):
        read_pos = self._buf.tell()
        if read_pos > self._max_size:
            new_buf = BytesIO()
            new_buf.write(self._buf.read())
            self._buf = new_buf
            read_pos = 0
        self._buf.seek(0, 2)
        self._buf.write(data)
        self._buf.seek(read_pos)
        return len(data)

    def _tell(self):
        return self._buf.tell()

    def _tell_end(self):
        self.tell = self._tell
        return self._content_length

    def seek(self, offset, whence):
        if whence == SEEK_END:
            # KLUDGE: PySoundfile no longer supports __len__, which means that
            # this stateful garbage is required.
            self.tell = self._tell_end
        self._buf.seek(offset, whence)

    def flush(self):
        self._buf.flush()
