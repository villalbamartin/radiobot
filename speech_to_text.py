import os
import tempfile
import queue
import sys

import sounddevice as sd
import soundfile as sf
import numpy  # Make sure NumPy is loaded before it is used in the callback

q = queue.Queue()


def callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    q.put(indata.copy())


def run_speech_server(comm_pipe, device=0):
    device_info = sd.query_devices(device, 'input')
    samplerate = int(device_info['default_samplerate'])
    fd, filename = tempfile.mkstemp(suffix='.wav')
    os.close(fd)
    channels = 1

    running = True
    while running:
        control_msg = comm_pipe.recv()
        if control_msg == 'start_recording':
            # Make sure the temporary file is empty
            if os.path.isfile(filename):
                os.unlink(filename)
            # Begin the recording process
            with sf.SoundFile(filename, mode='x', samplerate=samplerate,
                              channels=channels, subtype='PCM_24') as file:
                with sd.InputStream(samplerate=samplerate, device=device,
                                    channels=channels, callback=callback):
                    recording = True
                    while recording:
                        file.write(q.get())
                        if comm_pipe.poll():
                            control_msg = comm_pipe.recv()
                            if control_msg == 'stop_recording':
                                recording = False
                    # TO-DO: make some actual TTS here
                    text = "Hi there"
                    # Return the recognized text
                    comm_pipe.send(text)
        elif control_msg == 'quit':
            running = False
