#!/usr/bin/env python3
import pygame
from pygame.mixer import music, Sound


if __name__ == '__main__':
    pygame.init()
    window = pygame.display.set_mode((320, 240))
    window.fill((0, 0, 0))
    running = True
    static_noise = music.load('./sounds/gray_noise.ogg')
    button_on = Sound('./sounds/button_on.wav')
    button_off = Sound('./sounds/button_off.wav')
    music.play(loops=-1)
    music.set_volume(0.5)
    while running:
        for e in pygame.event.get():
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    music.set_volume(0.025)
                    Sound.play(button_on)
                    print("Key down")
            elif e.type == pygame.KEYUP:
                if e.key == pygame.K_SPACE:
                    print("Key up")
                    Sound.play(button_off)
                    music.set_volume(0.5)
                elif e.key == pygame.K_ESCAPE:
                    running = False
            if e.type == pygame.QUIT:
                running = False
    music.stop()
    pygame.quit()
