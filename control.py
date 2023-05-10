#!/usr/bin/env python3
import logging
import math
import nlp_utils
import os
import pygame
import random
import select
import sys
import tempfile
import time
from ovos_tts_plugin_mimic3 import Mimic3TTSPlugin
from pygame.mixer import music, Sound


def say(text, mimic, voice_file, text_output=False):
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
    text_output : bool
        If True, the text will also be printed out.

    Returns
    -------
    float
        Time (in seconds) that it will take the sound to end. Useful for doing
        other tasks while the audio plays.
    """
    mimic.get_tts(text, voice_file)
    if text_output:
        print(text)
    speech = Sound(voice_file)
    Sound.play(speech)
    # Time until the speech is done
    return speech.get_length()


def draw_image(window, width, height, images, needle_hist, speak=True):
    """ Draws the background image.

    Parameters
    ----------
    window : pygame.Display
        Display where all images are to be drawn.
    width : int
        Width of the screen.
    height : int
        Height of the screen.
    images : dict
        Dictionary containing all required images.
    needle_hist : list(float)
        History of last states of the needle - required to make the movement
        more natural.
    speak : bool
        Whether to draw the image with or without the microphene.
    """
    window.fill((0, 0, 0))
    bg_w, bg_h = images['bg'].get_size()
    window.blit(images['bg'], ((width - bg_w) / 2, (height - bg_h) / 2))
    
    # Draws the needle
    radius = 50.0
    min_angle = 3.141592/4.0
    max_angle = 3.0*3.141592/4.0
    # The larger this value, the slower the needle will move
    history_steps = 4 
    if music.get_volume() > 0.3:
        # The static is high, so no one is talking
        new_angle = random.gauss(min_angle, 0.07)
    else:
        # The static is low, so someone is talking
        new_angle = random.gauss(max_angle, 0.07)
    # Clamp the values to the valid range
    new_angle = min(max(new_angle, min_angle), max_angle)
    needle_hist.append(new_angle)
    angle = sum(needle_hist[-history_steps:])/len(needle_hist[-history_steps:])
    start = (377, 200)
    # My favorite equations of all time: convert angles and radius
    # into (x,y) coordinates.
    # Also, we flip the angle around (min_angle + max_angle - angle) because
    # otherwise the needle moves in the opposite direction
    end = (start[0] + int(radius*math.cos(min_angle + (max_angle-angle))),
           start[1] - int(radius*math.sin(min_angle + (max_angle-angle))))
    pygame.draw.line(window, (200, 50, 50), start, end, 1)
    window.blit(images['needle_thingy'], (365, 194))
    # Draws the microphone and buttons
    if speak:
        window.blit(images['white_button'], (344, 239))
        window.blit(images['mic'], (-5, 107))
    else:
        window.blit(images['red_button'], (386, 239))
    pygame.display.flip()
    pygame.display.update()


def _run_main_loop_gui(pipe_llm, pipe_speech_to_text, json_config,
                       mimic, voice_file):
    """ Runs the main loop of the progran in GUI mode.

    Notes
    -----
    This code uses a Statechart state machine under the hood.
    See the documentation for a proper diagram.
    """
    logger = logging.getLogger('radiobot')
    # Load the button sounds
    button_on = Sound('./sounds/button_on.wav')
    button_off = Sound('./sounds/button_off.wav')
    # Create a PyGame screen
    window = pygame.display.set_mode((json_config['screen_width'],
                                      json_config['screen_height']))
    images = dict()
    images['red_button'] = pygame.image.load("./images/red_button_on.png")
    images['white_button'] = pygame.image.load("./images/white_button_on.png")
    images['needle_thingy'] = pygame.image.load("./images/needle_support.png")
    images['mic'] = pygame.image.load("./images/mic.png")
    images['bg'] = pygame.image.load("./images/background.png")
    # History of the needle - required for animation
    needle_history = []
    draw_image(window, json_config['screen_width'],
               json_config['screen_height'], images, needle_history,
               speak=True)
    # When did we draw the screen for the last time?
    last_redraw = time.time()

    # List of possible states plus the current one
    dialog_states = {'idle_dialog', 'recording', 'transcribing', 'thinking',
                     'speaking'}
    radio_states = {'idle_radio', 'thinking_radio', 'think_and_say',
                    'slow_tongue', 'clear_queue', 'finish_talking'}
    all_states = dialog_states.union(radio_states)
    # Seed of the initial conversation
    conversation = list(json_config['dialog_seed'])
    # Initial state
    state = 'idle_dialog'
    # List of events that happen at every loop
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
        elif state == 'recording':
            if 'release_space' in events:
                # Stop recording
                music.set_volume(0.5)
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
                # Change from radio to dialog mode
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
                # This state is only reached at the very beginning, so let's
                # play the opening prompt. But first we trigger a redraw
                # because the system will be unresponsive afterwards.
                draw_image(window, json_config['screen_width'],
                           json_config['screen_height'], images,
                           needle_history, speak=state in dialog_states)

                music.set_volume(0.025)
                play_time = say('\n'.join(conversation), mimic, voice_file)
                time.sleep(play_time)
                music.set_volume(0.5)
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
            elif 'release_r' in events:
                # We want to go back to dialog mode, but we first need
                # to clean the utterance queue
                state = 'clear_queue'
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
            elif 'release_r' in events:
                # We want to go back to dialog mode, but we first need
                # to clean the utterance queue.
                # Note that the system is still speaking. This is technically
                # a bug to be solved with an extra state
                state = 'clear_queue'
        elif state == 'slow_tongue':
            if 'done_speaking' in events:
                # I am ready to speak some more
                state = 'thinking_radio'
            elif 'release_r' in events:
                # I want to go back to dialog mode, but the system is still
                # talking
                state = 'finish_talking'
        elif state == 'finish_talking':
            if 'done_speaking' in events:
                # Go back to dialog mode
                music.set_volume(0.5)
                conversation = list(json_config['dialog_seed'])
                state = 'idle_dialog'
        elif state == 'clear_queue':
            if 'llm_uttered' in events:
                # The queue is clear and I can go back to dialog mode
                _ = pipe_llm.recv()
                conversation = list(json_config['dialog_seed'])
                state = 'idle_dialog'
        # Is this correct?
        events = []
        if state != old_state:
            logger.debug(f"{old_state} -> {state}")
        # Finally, redraw the screen at an astonishing 5 FPS
        if time.time() > last_redraw + 0.2:
            last_redraw = time.time()
            draw_image(window, json_config['screen_width'],
                       json_config['screen_height'], images,
                       needle_history, speak=state in dialog_states)
    # Output the last dialog for debugging
    logger.debug("Last chat log")
    for utterance in conversation:
        logger.debug(f"- {utterance}")


def _run_main_loop_txt(pipe_llm, pipe_speech_to_text, json_config,
                       mimic, voice_file):
    """ Runs the main loop of the progran in text-only mode.
    The input is provided via keyboard instead of speech.

    Notes
    -----
    This code uses a Statechart state machine under the hood.
    See the documentation for a proper diagram.
    """
    logger = logging.getLogger('radiobot')

    # Seed of the initial conversation
    conversation = list(json_config['dialog_seed'])

    # List of possible states plus the current one
    dialog_states = {'idle_dialog', 'thinking', 'speaking'}
    radio_states = {'idle_radio', 'thinking_radio', 'think_and_say',
                    'slow_tongue', 'clear_queue', 'finish_talking'}
    all_states = dialog_states.union(radio_states)

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

        # Check whether we were talking but then finished.
        # Note: this event could get lost
        if 0 < time.time() - radio_end_time < 1:
            events.append('done_speaking')
        # Check whether the LLM said something
        if pipe_llm.poll():
            events.append('llm_uttered')

        # Now that I'm done with all the events, it is time to compare them
        # to my current state
        if state == 'idle_dialog':
            text = input('[Quit/Radio/Utterance] ')
            if text.casefold().strip() == 'quit':
                running = False
            elif text.casefold().strip() == 'radio':
                state = 'idle_radio'
                conversation = list(json_config['monologue_seed'])
            else:
                # Add this text to the prompt and send it to the LLM
                new_utterance = text
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
                play_time = say(response, mimic, voice_file, text_output=True)
                radio_end_time = time.time() + play_time
                state = 'speaking'
        elif state == 'speaking':
            if 'done_speaking' in events:
                # The LLM is done speaking and the loop starts again
                music.set_volume(0.5)
                state = 'idle_dialog'
        elif state == 'idle_radio':
            print("Entering Radio mode. " +
                  "Press 'R' to return to Dialog mode or 'Esc' to quit")
            # I'm not doing anything, so let's generate
            response_prompt = nlp_utils.broadcast_prompt(
                json_config['monologue_prompt'],
                conversation,
                context_turns=5,
                username=json_config['username'])
            pipe_llm.send(response_prompt)
            # This state is only reached at the very beginning, so let's
            # play the opening prompt
            music.set_volume(0.025)
            play_time = say('\n'.join(conversation), mimic, voice_file,
                            text_output=True)
            time.sleep(play_time)
            music.set_volume(0.5)
            state = 'thinking_radio'
        elif state == 'thinking_radio':
            if 'llm_uttered' in events:
                # The LLM is done thinking and it is time to talk
                response = pipe_llm.recv()
                music.set_volume(0.025)
                conversation.append(response)
                play_time = say(response, mimic, voice_file, text_output=True)
                radio_end_time = time.time() + play_time
                # We can start thinking the next sentence already
                response_prompt = nlp_utils.broadcast_prompt(
                                       json_config['monologue_prompt'],
                                       conversation,
                                       username=json_config['username'])
                pipe_llm.send(response_prompt)
                state = 'think_and_say'
            else:
                # We maybe want to go back to dialog mode, but we first need
                # to clean the utterance queue
                print("Press Enter within 3 seconds to return to dialog mode")
                key_press, _, _ = select.select([sys.stdin], [], [], 3)
                if key_press:
                    # There was input, so we first clear the STDIN queue.
                    _ = sys.stdin.readline().strip()
                    # We now go back to dialog mode after cleaning
                    # the queue of messages from the LLM.
                    state = 'clear_queue'
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
            elif 'release_r' in events:
                # We want to go back to dialog mode, but we first need
                # to clean the utterance queue.
                # Note that the system is still speaking. This is technically
                # a bug to be solved with an extra state
                music.set_volume(0.5)
                state = 'clear_queue'
        elif state == 'slow_tongue':
            if 'done_speaking' in events:
                # I am ready to speak some more
                state = 'thinking_radio'
            elif 'release_r' in events:
                # I want to go back to dialog mode, but the system is still
                # talking
                state = 'finish_talking'
        elif state == 'finish_talking':
            if 'done_speaking' in events:
                # Get ready to go back to dialog mode
                music.set_volume(0.5)
                conversation = list(json_config['dialog_seed'])
                state = 'idle_dialog'
        elif state == 'clear_queue':
            if 'llm_uttered' in events:
                _ = pipe_llm.recv()
                conversation = list(json_config['dialog_seed'])
                state = 'idle_dialog'
        # Is this correct?
        events = []
        if state != old_state:
            logger.debug(f"{old_state} -> {state}")
        # Finally, redraw the screen at an astonishing 5 FPS
    # Output the last dialog for debugging
    logger.debug("Last chat log")
    for utterance in conversation:
        logger.debug(f"- {utterance}")


def run_main_loop(pipe_llm, pipe_speech_to_text, json_config, use_gui=True):
    """ Runs the main interaction loop.

    Parameters
    ----------
    pipe_llm : Pipe()
        Pipe to send and receive messages to and from the LLM.
    pipe_speech_to_text : Pipe()
        Pipe to send and receive messages to and from the speech-to-text.
    json_config : dict()
        Dictionary with general configuration options for the system.
    use_gui : bool
        Whether to use the GUI or the text-only interface.
    """
    # Initialize PyGame music and sounds, and start playing static
    music.load('./sounds/gray_noise.ogg')
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
    if use_gui:
        _run_main_loop_gui(pipe_llm, pipe_speech_to_text, json_config,
                           mimic, voice_file.name)
    else:
        _run_main_loop_txt(pipe_llm, pipe_speech_to_text, json_config,
                           mimic, voice_file.name)

    # Cleanup
    pipe_llm.send('quit')
    pipe_speech_to_text.send('quit')
    music.stop()
    pygame.quit()
    # Delete the voice temporary file
    os.unlink(voice_file.name)
