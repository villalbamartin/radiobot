#!/usr/bin/env python3
import argparse
import json
import nlp_utils
import os
import signal
import sys
import time
from multiprocessing import Pipe


def signal_handler(sig, frame):
    # End the program
    # Delete the voice temporary file
    print("Ending the program")
    llm_pipe[0].send('quit')
    os.waitpid(llm_pid, 0)
    sys.exit(0)


if __name__ == '__main__':
    """ Script for endless generation. 
    """
    # General command line options
    parser = argparse.ArgumentParser(description='Launchs the generation system')
    parser.add_argument('llm', help='LLM to use for speech generation')
    args = parser.parse_args()

    # Read some general parameters
    with open('config.json', 'r') as fp:
        app_config = json.load(fp)

    # Start the services
    llm_pipe = Pipe()
    llm_pid = os.fork()
    if llm_pid == 0:
        # LLM server
        import nlg
        nlg.run_nlg_server(args.llm, llm_pipe[1],
                           username=app_config['username'])
    else:
        signal.signal(signal.SIGINT, signal_handler)
        # Begin the generation procedure
        with open("output_{}.txt".format(int(time.time())), 'w') as fp:
            conversation = list(app_config['monologue_seed'])
            for utterance in conversation:
                print(utterance, flush=True, file=fp)
            while True:
                response_prompt = nlp_utils.broadcast_prompt(
                    app_config['monologue_prompt'],
                    conversation,
                    context_turns=5,
                    username=app_config['username'])
                llm_pipe[0].send(response_prompt)
                response = llm_pipe[0].recv()
                print(response, flush=True, file=fp)
                conversation.append(response)
