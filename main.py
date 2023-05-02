#!/usr/bin/env python3
import pygame


if __name__ == '__main__':
    pygame.init()
    window = pygame.display.set_mode((320, 240))
    window.fill((0, 0, 0))
    running = True
    static_noise = pygame.mixer.music.load('./sounds/Gray_noise.ogg')
    pygame.mixer.music.play(loops=-1)
    while running:
        for e in pygame.event.get():
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    pygame.mixer.music.set_volume(0.025)
                    print("Key down")
            elif e.type == pygame.KEYUP:
                if e.key == pygame.K_SPACE:
                    print("Key up")
                    pygame.mixer.music.set_volume(0.5)
                elif e.key == pygame.K_ESCAPE:
                    running = False
            if e.type == pygame.QUIT:
                running = False
    pygame.mixer.music.stop()
    pygame.quit()
