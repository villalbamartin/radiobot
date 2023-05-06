#!/usr/bin/env python3
from llama_cpp import Llama
import logging


def run_nlg_server(llm_path, comm_pipe, username="User"):
    """ Starts the server that generates a reply for a given prompt.

    Parameters
    ----------
    llm_path : str
        Path to the language model used to generate the responses
    comm_pipe : Pipe()
        Pipe that will be used to receive new prompts and send responses.

    Notes
    -----
    To close the server send the 'quit' message through the pipe.
    """
    logger = logging.getLogger('radiobot')
    llm = Llama(model_path=llm_path)
    running = True
    while running:
        prompt = comm_pipe.recv()
        if prompt == 'quit':
            running = False
        else:
            try:
                output = llm(prompt, max_tokens=64,
                             stop=[f"{username}:", "I: ", "\n"],
                             echo=True)
            except ValueError:
                logger.debug("Prompt too long: {} words, {} characters".format(
                    len(prompt),
                    len(prompt.split(' '))))
                prompt = prompt[-500:]
                output = llm(prompt, max_tokens=64,
                             stop=[f"{username}:", "I: ", "\n"],
                             echo=True)
            new_text = output['choices'][0]['text']
            #if new_text.rfind('.') > 0:
            #    new_text = new_text[:new_text.rfind('.')] + "."
            new_text = new_text.split('I: ')[-1].strip()
            comm_pipe.send(new_text)
