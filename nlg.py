#!/usr/bin/env python3
import os
import pygame
import tempfile
import time
from llama_cpp import Llama
from multiprocessing import Pipe
from ovos_tts_plugin_mimic3 import Mimic3TTSPlugin
from pygame.mixer import music, Sound


def start_server(llm_path, comm_pipe):
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
    running = True
    while running:
        prompt = comm_pipe.recv()
        if prompt == 'quit':
            running = False
        else:
            output = llm(prompt, max_tokens=64,
                         stop=[f"{username}:", "I: ", "\n"],
                         echo=True)
            new_text = output['choices'][0]['text']
            new_text = new_text.split('I: ')[-1].strip()
            comm_pipe.send(new_text)

