#!/usr/bin/env python3
import os
import pygame
import tempfile
import time
from llama_cpp import Llama
from multiprocessing import Pipe
from ovos_tts_plugin_mimic3 import Mimic3TTSPlugin
from pygame.mixer import music, Sound


def say(text, mimic, voice_file):
    """ Synthesises a text as speech and plays it.

    Parameters
    ----------
    text : str
        Speech that will be read out loud.
    mimic : Mimic3TTSPlugin
        Pre-configured MIMIC-3 plugin
    voice_file : str
        Path to a temporary file that will be overwritten with a WAV file
        containing the desired speech.
    """
    mimic.get_tts(text, voice_file)
    speech = Sound(voice_file)
    Sound.play(speech)
    # We wait until the speech is done
    time.sleep(speech.get_length())


def reply(llm, conversation_log, context_turns=5, other_name="User"):
    """ Generates an LLM reply for a given conversation.

    Parameters
    ----------
    llm : Llama()
        Language model used to generate the responses
    conversation_log : list(str)
        List of utterances in this dialog, switching between the text between
        the user and the AI. The user always goes first.
    context_turns : int
        How many turns to use in the prompt for context. One turn consists of
        one utterance for the User and one for the AI.

    Returns
    -------
    str
        An utterance that the AI generates in response to the given dialog.
    """
    start = time.time()
    if len(conversation_log) % 2 != 1:
        print("The conversation ends in the wrong turn!")
    prompt = f"This is a log of a conversation between {other_name} and I.\n"
    user_turn = True
    subset = 1+2*context_turns
    for utterance in conversation_log[-subset:]:
        if user_turn:
            prompt += f"{other_name}: {utterance}\n"
        else:
            prompt += f"I: {utterance}\n"
        user_turn = not user_turn
    prompt += "I: "
    print(prompt)
    output = llm(prompt, max_tokens=64, stop=[f"{other_name}:", "I:", "\n"], echo=True)
    new_text = output['choices'][0]['text']
    new_text = new_text.split('I: ')[-1].strip()
    print(new_text)
    print("({:.3f}s) Obtained reply: {}".format(time.time()-start, new_text))
    return new_text


if __name__ == '__main__':
    # Start the Speech-to-Text server
    speech_to_text_pipe = Pipe()
    pid = os.fork()
    if pid == 0:
        # Speech-to-text server
        import speech_to_text
        speech_to_text.run_speech_server(speech_to_text_pipe[1])
    else:
        # Main thread
        speech_to_text_pipe = speech_to_text_pipe[0]

        # Initialize PyGame, including window and sounds
        pygame.init()
        width = 800
        height = 425
        window = pygame.display.set_mode((width, height))
        window.fill((0, 0, 0))
        music.load('./sounds/gray_noise.ogg')
        button_on = Sound('./sounds/button_on.wav')
        button_off = Sound('./sounds/button_off.wav')
        bg = pygame.image.load("./images/background.jpg")
        bg_w, bg_h = bg.get_size()
        window.blit(bg, ((width-bg_w)/2, (height-bg_h)/2))
        pygame.display.update()

        # Start playing static sound
        music.play(loops=-1)
        music.set_volume(0.5)

        # LLaMa model and conversation logs
        llm = Llama(model_path="/media/external/CORPORA/llama/ggml-alpaca-7b-q4.bin")
        conversation = ['Good morning! Nice to see you.', 'Thanks. Good morning to you too!']
        # Voice configuration, including temporary file and MIMIC config
        cfg = {"voice": "en_US/hifi-tts_low", "speaker": "92", "length_scale": 1.2}
        mimic = Mimic3TTSPlugin(config=cfg)
        voice_file = tempfile.NamedTemporaryFile(delete=False)
        voice_file.close()

        # Start of main loop
        running = True
        recording = False
        while running:
            for e in pygame.event.get():
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_SPACE:
                        if not recording:
                            recording = True
                            # Space key down
                            music.set_volume(0.025)
                            Sound.play(button_on)
                            speech_to_text_pipe.send('start_recording')
                elif e.type == pygame.KEYUP:
                    if e.key == pygame.K_SPACE:
                        if recording:
                            # Space key up
                            # Stop recording
                            print("Done recording...")
                            recording = False
                            # Play the correct sounds
                            music.set_volume(0.5)
                            Sound.play(button_off)
                            # Stop the actual recording
                            speech_to_text_pipe.send('stop_recording')
                            received_text = speech_to_text_pipe.recv()
                            conversation.append(received_text)
                            # Test: wait a second and say something predefined
                            response = reply(llm, conversation)
                            music.set_volume(0.025)
                            conversation.append(response)
                            say(response, mimic, voice_file.name)
                            music.set_volume(0.5)
                    elif e.key == pygame.K_ESCAPE:
                        # Escape key - quit
                        running = False
                    elif e.key == pygame.K_f:
                        pygame.display.toggle_fullscreen()
                        window.fill((0, 0, 0))
                        window.blit(bg, ((width - bg_w) / 2, (height - bg_h) / 2))
                        pygame.display.flip()
                        pygame.display.update()
                elif e.type == pygame.QUIT:
                    running = False
        # For debugging
        print("Final chat log")
        for utterance in conversation:
            print(f"- {utterance}")
        # Cleanup
        speech_to_text_pipe.send('quit')
        music.stop()
        pygame.quit()
        os.unlink(voice_file.name)
