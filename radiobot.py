#!/usr/bin/env python3
import argparse
import control
import json
import logging
import os
import pygame
import sys
from multiprocessing import Pipe


if __name__ == '__main__':
    # The very first thing is setting the logger
    logger = logging.getLogger('radiobot')
    logger.setLevel(logging.DEBUG)

    # General command line options
    parser = argparse.ArgumentParser(description='Launchs the radio')
    parser.add_argument('llm', help='LLM to use for speech generation')
    parser.add_argument('-mic-device', type=int, help='Device to use as mic.')
    parser.add_argument('-t', '--no-gui',
                        action='store_true',
                        help='Use the console-ony interface.')
    args = parser.parse_args()
    logger.debug(args)

    # Read some general parameters
    with open('config.json', 'r') as fp:
        app_config = json.load(fp)

    # Start the services
    # First, the speech-to-Text server
    speech_to_text_pipe = Pipe()
    speech_pid = os.fork()
    if speech_pid == 0:
        # Speech-to-text server
        import speech_to_text
        if args.no_gui:
            # We don't actually need this process, because there will be
            # no recording.
            sys.exit(0)
        else:
            speech_to_text.run_speech_server(speech_to_text_pipe[1],
                                         device=args.mic_device)
    else:
        llm_pipe = Pipe()
        llm_pid = os.fork()
        if llm_pid == 0:
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
            if args.no_gui:
                print("Display disabled")
            else:
                print("Using PyGame for display")
            control.run_main_loop(llm_pipe[0], speech_to_text_pipe[0],
                                  app_config, not args.no_gui)
            # Wait for the subprocesses to finish
            os.waitpid(speech_pid, 0)
            os.waitpid(llm_pid, 0)
            sys.exit(0)
