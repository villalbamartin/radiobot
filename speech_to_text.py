import logging
import os
import sys
import tempfile
import queue
import sounddevice as sd
import soundfile as sf
import numpy  # Make sure NumPy is loaded before it is used in the callback
import whisper

# Queue for the voice recording
q = queue.Queue()


def callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    q.put(indata.copy())


def setup_mic():
    """ Routine for setting up the microphone automatically.
    """
    logger = logging.getLogger('radiobot')
    device = None
    # Use the first available device
    input_devices = sd.query_devices(kind='input')
    if isinstance(input_devices, dict):
        device = input_devices['index']
        logger.debug('Using input device {}: {}'.format(
                     input_devices['index'],
                     input_devices['name']))
    elif isinstance(input_devices, list):
        print("Multiple devices found")
        for dev in input_devices:
            print("Device {}: {}".format(dev['index'], dev['name']))
            if device is None:
                device = dev['index']
        print('Using first input device {}: {}'.format(
               input_devices[0]['index'],
               input_devices[0]['name']))
    else:
        logger.critical('No input device found')
        device = -1
    return device


def run_speech_server(comm_pipe, device=None):
    # Parameters for the recording
    logger = logging.getLogger('radiobot')
    if device is None:
        device = setup_mic()
    device_info = sd.query_devices(device, 'input')
    samplerate = int(device_info['default_samplerate'])
    fd, filename = tempfile.mkstemp(suffix='.wav')
    os.close(fd)
    channels = 1
    # Initialize the speech-to-text system and ensure it only runs on CPU
    # (the GPU will be needed for the language model)
    os.environ['CUDA_VISIBLE_DEVICES'] = ""
    try:
        model = whisper.load_model(os.path.join('~', '.cache', 'whisper', 'base.pt'))
        logger.debug("Loaded local Whisper model")
    except RuntimeError:
        model = whisper.load_model('base')
        logger.debug("Loaded internet Whisper model")
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
                    # Convert the speech to text and return it via pipe
                    result = model.transcribe(filename, language="en")
                    logger.debug('You said: ' + result["text"].strip())
                    comm_pipe.send(result["text"].strip())
        elif control_msg == 'quit':
            # Stop the loop and remove the temporary file
            running = False
            os.unlink(filename)
    # Finish the process nicely
    sys.exit(0)
