#!/usr/bin/env python3
import argparse
import json
import logging
import pygame
import sounddevice as sd
import sys
from multiprocessing import Pipe


def setup_mic():
    """ Routine for setting up the microphone automatically.
    """
    device = None
    # Use the first available device
    input_devices = sd.query_devices(kind='input')
    if isinstance(input_devices, dict):
        device = input_devices['index']
        logging.debug('Using input device {}: {}'.format(
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
        print('No input device found')
        device = -1
    return device

    

if __name__ == '__main__':
    # General command line options
    parser = argparse.ArgumentParser(description='Launchs the radio')
    parser.add_argument('-llm', help='LLM to use for speech generation')
    parser.add_argument('-mic-device', type=int, help='Device to use as mic.')
    parser.add_argument('-t', '--no-gui',
                        action='store_true',
                        help='Don\'t show anything on screen')
    parser.add_argument('-m', '--no-mic',
                        action='store_true',
                        help='Use the keyboard for input instead of speech')
    args = parser.parse_args()
    print(args)

    # Set up the microphone if needed
    mic_device = None
    if args.no_mic:
        print("Using keyboard as input")
    else:
        print("Using microphone as input")
        # We need to set up a microphone
        if args.mic_device is None:
            mic_device = setup_mic()
        else:
            mic_device = args.mic_device

    # Read some general parameters
    with open('config.json', 'r') as fp:
        app_config = json.load(fp)

    # Start the services
    # First, the speech-to-Text server
    speech_to_text_pipe = Pipe()
    pid = os.fork()
    if pid == 0:
        # Speech-to-text server
        import speech_to_text
        speech_to_text.run_speech_server(speech_to_text_pipe[1])
    else:
        llm_pipe = Pipe()
        pid = os.fork()
        if pid == 0:
            # LLM server
            import nlg
            nlg.run_nlg_server(args.llm, llm_pipe[1],
                             username=app_config['username'])
        else:
            # Control and screen thread
            # speech_to_text_pipe[0] is ours
            # commands: 'start_recording', 'stop_recording', 'quit'
            # llm_pipe[0] is also ours 
            # send 'quit' to quit

            # Set up the screen if needed
            pygame.init()
            if args.no_gui or args.no_mic:
                print("Display disabled")
                window = None
            else:
                print("Using PyGame for display")
                width = 800
                height = 425
                window = pygame.display.set_mode((width, height))
                window.fill((0, 0, 0))

