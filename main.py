#!/usr/bin/env python3
import os
import pygame
import tempfile
import time
from multiprocessing import Pipe
from ovos_tts_plugin_mimic3 import Mimic3TTSPlugin
from pygame.mixer import music, Sound


def say(text, mimic, voice_file):
    """ Synthesises a text as speech and plays it.

    Parameters
    ----------
    text : str
        Speech that will be read out loud.
    mimic : Mimic3TTSPlugin
        Pre-configured MIMIC-3 plugin
    voice_file : str
        Path to a temporary file that will be overwritten with a WAV file
        containing the desired speech.
    """
    mimic.get_tts(text, voice_file)
    speech = Sound(voice_file)
    Sound.play(speech)
    # We wait until the speech is done
    time.sleep(speech.get_length())


if __name__ == '__main__':
    # Initialize PyGame, including window and sounds
    pygame.init()
    window = pygame.display.set_mode((320, 240))
    window.fill((0, 0, 0))
    music.load('./sounds/gray_noise.ogg')
    button_on = Sound('./sounds/button_on.wav')
    button_off = Sound('./sounds/button_off.wav')
    # Start playing static sound
    music.play(loops=-1)
    music.set_volume(0.5)
    # Voice configuration, including temporary file and MIMIC config
    cfg = {"voice": "en_US/hifi-tts_low", "speaker": "92"}
    mimic = Mimic3TTSPlugin(config=cfg)
    voice_file = tempfile.NamedTemporaryFile(delete=False)
    voice_file.close()
    # Start the Speech-to-Text server
    speech_to_text_pipe = Pipe()
    pid = os.fork()
    if pid == 0:
        # Speech-to-text server
        import speech_to_text
        speech_to_text.run_speech_server(speech_to_text_pipe[1])
    else:
        speech_to_text_pipe = speech_to_text_pipe[0]

        # Start of main loop
        running = True
        recording = False
        while running:
            for e in pygame.event.get():
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_SPACE:
                        if not recording:
                            recording = True
                            # Space key down
                            music.set_volume(0.025)
                            Sound.play(button_on)
                            speech_to_text_pipe.send('start_recording')
                elif e.type == pygame.KEYUP:
                    if e.key == pygame.K_SPACE:
                        if recording:
                            # Space key up
                            # Stop recording
                            print("Done recording...")
                            recording = False
                            # Play the correct sounds
                            music.set_volume(0.5)
                            Sound.play(button_off)
                            # Stop the actual recording
                            speech_to_text_pipe.send('stop_recording')
                            received_text = speech_to_text_pipe.recv()
                            # Test: wait a second and say something predefined
                            music.set_volume(0.025)
                            say(f"You said: \"{received_text}\"",
                                mimic, voice_file.name)
                            music.set_volume(0.5)
                    elif e.key == pygame.K_ESCAPE:
                        # Escape key - quit
                        running = False
                if e.type == pygame.QUIT:
                    running = False
        # Cleanup
        speech_to_text_pipe.send('quit')
        music.stop()
        pygame.quit()
        os.unlink(voice_file.name)
