#!/usr/bin/env python3
import argparse
import json
import nlp_utils
import os
import random
import signal
import sys
from multiprocessing import Pipe


# A list of animal names, used to generate the output files and give them
# slightly informative names because the timestamp method was annoying
animals = {'aardvark', 'bat', 'cow', 'dolphin', 'eagle', 'fox', 'giraffe',
           'horse', 'iguana', 'jaguar', 'koala', 'llama', 'monkey',
           'nandu', 'ocelot', 'panther', 'rhino', 'salamander', 'tortoise',
           'viper', 'wombat', 'yaguarete', 'zebra'}


def signal_handler(sig, frame):
    # End the program
    # Delete the voice temporary file
    print("Ending the program")
    llm_pipe[0].send('quit')
    os.waitpid(llm_pid, 0)
    with open(ssml_output, 'a') as fp:
        print('</speak>', file=fp)
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

    a0, a1 = random.sample(animals, 2)
    txt_output = "monologue_{}_{}.txt".format(a0, a1)
    ssml_output = "monologue_{}_{}.ssml".format(a0, a1)

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
        with open(txt_output, 'w') as fp:
            with open(ssml_output, 'w') as fp_ssml:
                print("<speak>", flush=True, file=fp_ssml)
                conversation = list(app_config['monologue_seed'])
                for utterance in conversation:
                    print(utterance, flush=True, file=fp)
                    print(f'<s>{utterance}</s><break time="1s" />', flush=True, file=fp_ssml)
                while True:
                    response_prompt = nlp_utils.broadcast_prompt(
                        app_config['monologue_prompt'],
                        conversation,
                        context_turns=5,
                        username=app_config['username'])
                    llm_pipe[0].send(response_prompt)
                    response = llm_pipe[0].recv()
                    print(response, flush=True, file=fp)
                    print(f'<s>{response}</s><break time="1s" />', flush=True, file=fp_ssml)
                    conversation.append(response)
