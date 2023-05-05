#!/usr/bin/env python3
import logging
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
    """ Runs the main loop of the progran in GUI mode.

    Notes
    -----
    This code uses a Statechart state machine under the hood.
    See the documentation for a proper diagram.
    """
    # Create a PyGame screen
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

    # List of possible states plus the current one
    all_states = {'idle_dialog', 'recording', 'transcribing', 'thinking',
                  'speaking', 'idle_radio', 'thinking_radio', 'think_and_say',
                  'slow_tongue'}
    state = 'idle_dialog' 
    events = []
    # Time until the current radio line is done playing
    radio_end_time = 0
    # To know when to finish the loop. This should be part of the
    # state machine, but it's easier this way.
    running = True
    while running:
        assert state in all_states, f'Invalid state {state}'
        old_state = state
        # First, collect all possible events.
        # Let's start with all types of key presses.
        for e in pygame.event.get():
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    events.append('press_space')
            elif e.type == pygame.KEYUP:
                if e.key == pygame.K_SPACE:
                    events.append('release_space')
                elif e.key == pygame.K_r:
                    events.append('release_r')
                elif e.key == pygame.K_f:
                    # Switch screen mode - this doesn't need to go through the
                    # regular pipeline
                    pygame.display.toggle_fullscreen()
                    window.fill((0, 0, 0))
                    window.blit(bg, ((width - bg_w) / 2, (height - bg_h) / 2))
                    pygame.display.flip()
                    pygame.display.update()
                elif e.key == pygame.K_ESCAPE:
                    # This is the one condition that doesn't go through the
                    # state machine
                    running = False
            elif e.type == pygame.QUIT:
                running = False
        # Now, check whether we were talking but then finished.
        # Note: this event could get lost
        if 0 < time.time() - radio_end_time < 1:
            events.append('done_speaking')
        # Check whether the LLM said something
        if pipe_llm.poll():
            events.append('llm_uttered')
        if pipe_speech_to_text.poll():
            events.append('transcribed')

        # Now that I'm done with all the events, it is time to compare them
        # to my current state

        # Bug: many keypresses are getting lost.

        if state == 'idle_dialog':
            if 'press_space' in events:
                # Start recording
                music.set_volume(0.025)
                Sound.play(button_on)
                pipe_speech_to_text.send('start_recording')
                state = 'recording'
            elif 'release_r' in events:
                # Change from dialog to radio mode
                state = 'idle_radio'
                conversation = list(json_config['monologue_seed'])
                music.set_volume(0.5)
                # TODO: Animation and sound
        elif state == 'recording':
            if 'release_space' in events:
                # Stop recording
                music.set_volume(0.05)
                Sound.play(button_off)
                pipe_speech_to_text.send('stop_recording')
                state = 'transcribing'
        elif state == 'transcribing':
            if 'transcribed' in events:
                # Add this text to the prompt and send it to the LLM
                new_utterance = pipe_speech_to_text.recv()
                conversation.append(new_utterance)
                response_prompt = nlp_utils.build_reply_prompt(
                                       json_config['dialog_prompt'],
                                       conversation,
                                       context_turns=5,
                                       username=json_config['username'])
                pipe_llm.send(response_prompt)
                state = 'thinking'
        elif state == 'thinking':
            if 'llm_uttered' in events:
                # The LLM is done thinking and it is time to talk
                response = pipe_llm.recv()
                music.set_volume(0.025)
                conversation.append(response)
                play_time = say(response, mimic, voice_file)
                radio_end_time = time.time() + play_time
                state = 'speaking'
        elif state == 'speaking':
            if 'done_speaking' in events:
                # The LLM is done speaking and the loop starts again
                music.set_volume(0.5)
                state = 'idle_dialog'
        elif state == 'idle_radio':
            if 'release_r' in events:
                # Change from dialog to radio mode
                conversation = list(json_config['dialog_seed'])
                music.set_volume(0.5)
                state = 'idle_dialog'
            else:
                # I'm not doing anything, so let's generate
                response_prompt = nlp_utils.broadcast_prompt(
                    json_config['monologue_prompt'],
                    conversation,
                    context_turns=5,
                    username=json_config['username'])
                pipe_llm.send(response_prompt)
                # TODO: Animation and sound
                state = 'thinking_radio'
        elif state == 'thinking_radio':
            if 'llm_uttered' in events:
                # The LLM is done thinking and it is time to talk
                response = pipe_llm.recv()
                music.set_volume(0.025)
                conversation.append(response)
                play_time = say(response, mimic, voice_file)
                radio_end_time = time.time() + play_time
                # We can start thinking the next sentence already
                response_prompt = nlp_utils.broadcast_prompt(
                                       json_config['monologue_prompt'],
                                       conversation,
                                       username=json_config['username'])
                pipe_llm.send(response_prompt)
                state = 'think_and_say'
        elif state == 'think_and_say':
            if 'llm_uttered' in events:
                # The LLM is done thinking the next sentence,
                # but we are not done talking yet
                state = 'slow_tongue'
            elif 'done_speaking' in events:
                # The system is done speaking, but the next utterance is not
                # there yet.
                music.set_volume(0.5)
                state = 'thinking_radio'
        elif state == 'slow_tongue':
            if 'done_speaking' in events:
                # I am ready to speak some more
                state = 'thinking_radio'
        # Is this correct?
        events = []
        if state != old_state:
            logging.debug(f"{old_state} -> {state}")
    # For debugging
    print("Final chat log")
    for utterance in conversation:
        print(f"- {utterance}")


def run_main_loop(pipe_llm, pipe_speech_to_text, json_config):
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
    if True:
        _run_main_loop_gui(pipe_llm, pipe_speech_to_text, json_config,
                           button_on, button_off, mimic, voice_file.name)
    else:
        raise NotImplementedError("There's an issue for when you have audio input and no screen. "
                                  "The wrong events get captured.")

    # Cleanup
    pipe_llm.send('quit')
    pipe_speech_to_text.send('quit')
    music.stop()
    pygame.quit()
    # Delete the voice temporary file
    os.unlink(voice_file.name)
