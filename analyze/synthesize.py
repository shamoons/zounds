import numpy as np
from scikits.audiolab import play

class WindowedAudioSynthesizer(object):
    '''
    A very simple synthesizer that assumes windowed, but otherwise raw frames
    of audio.
    '''
    def __init__(self,windowsize,stepsize):
        object.__init__(self)
        self.windowsize = windowsize
        self.stepsize = stepsize
    
    def __call__(self,frames):
        output = np.zeros(self.stepsize + len(frames) * self.stepsize)
        for i,f in enumerate(frames):
            start = i * self.stepsize
            stop = start + self.windowsize
            output[start : stop] += f
        return output * .8
            
    def play(self,audio):
        output = self(audio)
        try:
            play(np.tile(output,(2,1)))
        except KeyboardInterrupt:
            pass
        