#!/usr/bin/env python3
import os
import pygame
import tempfile
from ovos_tts_plugin_mimic3 import Mimic3TTSPlugin
from pygame.mixer import music, Sound


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
    # Play a test voice
    cfg = {"voice": "en_US/hifi-tts_low", "speaker": "92"}
    mimic = Mimic3TTSPlugin(config=cfg)
    voice_file = tempfile.NamedTemporaryFile(delete=False)
    voice_file.close()
    print(voice_file.name)
    mimic.get_tts("hello world", voice_file.name)

    # Start of main loop
    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    # Space key down
                    music.set_volume(0.025)
                    Sound.play(button_on)
            elif e.type == pygame.KEYUP:
                if e.key == pygame.K_SPACE:
                    # Space key up
                    music.set_volume(0.5)
                    Sound.play(button_off)
                elif e.key == pygame.K_ESCAPE:
                    # Escape key - quit
                    running = False
            if e.type == pygame.QUIT:
                running = False
    # Cleanup
    music.stop()
    pygame.quit()
    os.unlink(voice_file.name)
