#!/usr/bin/env python3
import nlp_utils
import os
import pygame
import tempfile
import time
from ovos_tts_plugin_mimic3 import Mimic3TTSPlugin
from pygame.mixer import music, Sound


def say(text, mimic, voice_file):
    """ Synthesises a text as speech and plays it. The function returns
    immediately and provides the time it will take for the audio to play.

    Parameters
    ----------
    text : str
        Speech that will be read out loud.
    mimic : Mimic3TTSPlugin
        Pre-configured MIMIC-3 plugin
    voice_file : str
        Path to a temporary file that will be overwritten with a WAV file
        containing the desired speech.

    Returns
    -------
    float
        Time (in seconds) that it will take the sound to end. Useful for doing
        other tasks while the audio plays.
    """
    mimic.get_tts(text, voice_file)
    speech = Sound(voice_file)
    Sound.play(speech)
    # Time until the speech is done
    return speech.get_length()


def _run_main_loop_console():
    pass


def _run_main_loop_gui(pipe_llm, pipe_speech_to_text, json_config,
                       button_on, button_off, mimic, voice_file):
    # TODO: This should be a state machine.

    # Create a screen
    width = json_config['screen_width']
    height = json_config['screen_height']
    window = pygame.display.set_mode((width, height))
    window.fill((0, 0, 0))
    bg = pygame.image.load("./images/background.jpg")
    bg_w, bg_h = bg.get_size()
    window.blit(bg, ((width - bg_w) / 2, (height - bg_h) / 2))
    pygame.display.update()

    # Seed of the initial conversation
    conversation = ['Good morning! Nice to see you.',
                    'Thanks. Good morning to you too!']
    # Are we recording right now? Useful for knowing whether I can
    state = 'idle'
    # Which mode we are in
    is_radio = False
    # Time until the current radio line is done playing
    radio_end_time = 0
    # To know when to finish the loop
    running = True
    while running:
        assert state in ['idle', 'recording', 'replying'], f'Invalid status {state}'
        if is_radio and state == 'idle':
            if time.time() > radio_end_time:
                # We are done playing the last broadcast but we don't have
                # a new one yet, so we raise the static sound.
                music.set_volume(0.5)
            # Create a radio prompt and send it
            response_prompt = nlp_utils.broadcast_prompt(json_config['monologue_prompt'],
                                                conversation,
                                                username=json_config['username'])
            pipe_llm.send(response_prompt)
            state = 'replying'
        for e in pygame.event.get():
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    # Space key down
                    if not is_radio and state == 'idle':
                        state = 'recording'
                        music.set_volume(0.025)
                        Sound.play(button_on)
                        pipe_speech_to_text.send('start_recording')
            elif e.type == pygame.KEYUP:
                if e.key == pygame.K_SPACE:
                    # Space key up
                    if not is_radio and state == 'recording':
                        # Play the correct sounds
                        music.set_volume(0.5)
                        Sound.play(button_off)
                        # Stop the actual recording
                        pipe_speech_to_text.send('stop_recording')
                        received_text = pipe_speech_to_text.recv()
                        conversation.append(received_text)
                        # Build the prompt and send it
                        response_prompt = nlp_utils.build_reply_prompt(
                            json_config['dialog_prompt'],
                            conversation,
                            context_turns=5,
                            username=json_config['username'])
                        pipe_llm.send(response_prompt)
                        # Wait until the next reply come
                        state = 'replying'
                elif e.key == pygame.K_ESCAPE:
                    # Escape key - quit
                    running = False
                elif e.key == pygame.K_r:
                    is_radio = not is_radio
                    if is_radio:
                        conversation = ['Good morning! Nice to see you.',
                                        'Thanks. Good morning to you too!']
                    else:
                        conversation = ['And now, the news.']
                    # This could cause some problems
                    state = 'idle'
                elif e.key == pygame.K_f:
                    pygame.display.toggle_fullscreen()
                    window.fill((0, 0, 0))
                    window.blit(bg, ((width - bg_w) / 2, (height - bg_h) / 2))
                    pygame.display.flip()
                    pygame.display.update()
            elif e.type == pygame.QUIT:
                running = False
        if state == 'replying':
            if pipe_llm.poll() and time.time() > radio_end_time:
                response = pipe_llm.recv()
                music.set_volume(0.025)
                conversation.append(response)
                play_time = say(response, mimic, voice_file)
                # If it's radio mode we can generate the next utterance while
                # the current one is playing. Otherwise we just wait.
                if is_radio:
                    radio_end_time = time.time() + play_time
                else:
                    time.sleep(play_time)
                    music.set_volume(0.5)
                state = 'idle'
    # For debugging
    print("Final chat log")
    for utterance in conversation:
        print(f"- {utterance}")


def run_main_loop(pipe_llm, pipe_speech_to_text, screen, json_config):
    # Initialize PyGame music and sounds
    music.load('./sounds/gray_noise.ogg')
    button_on = Sound('./sounds/button_on.wav')
    button_off = Sound('./sounds/button_off.wav')

    # Start playing static sound
    music.play(loops=-1)
    music.set_volume(0.5)

    # Voice configuration, including temporary file and MIMIC config
    mimic = Mimic3TTSPlugin(config=json_config['tts'])
    voice_file = tempfile.NamedTemporaryFile(delete=False)
    voice_file.close()

    # There are two ways to run the main loop depending on whether
    # you are using the GUI or not. We split the code here because
    # the code for processing inputs is different in each case,
    # and better to have two functions that lots of nested ifs.
    if screen is not None:
        _run_main_loop_gui(pipe_llm, pipe_speech_to_text, json_config,
                           button_on, button_off, mimic, voice_file.name)

    # Cleanup
    pipe_llm.send('quit')
    pipe_speech_to_text.send('quit')
    music.stop()
    pygame.quit()
    # Delete the voice temporary file
    os.unlink(voice_file.name)
