import math
import logging


def best_idx(initial_prompt, conversation_log, desired_context, max_chars=1300):
    """ Returns the index to use in a conversation log in order to keep
    the maximum number of utterances possible from turn to turn.
    See "Notes" for more details.

    Parameters
    ----------
    initial_prompt : str
        Prompt for the overall dialogue
    conversation_log : list(str)
        Log of all utterances in the program's history.
    desired_context : int
        Ideal desired length for a prompt. Once this number of utterances have
        been reached, the pointer will be moved forward.
    max_chars : int
        Maximum number of characters supported by the LLM. Note that the LLM
        uses tokens instead of characters, so this measure is just an
        approximation.

    Notes
    -----
    When generating with llama-cpp-python it is useful to keep the previous
    context unaltered, as this will save computation and generate faster.
    Given that there is a maximum number of tokens, we would like to keep the
    context as long as possible.
    This algorithm takes a conversation log and returns the index of the first
    utterance to use. This index is "sticky" in the sense that it will always
    remain the same except in two situation: either when the number of
    utterances reaches the desired context, or when the number of characters
    exceeds max_chars. When that happens we move the window forward, keeping
    only the last two utterances as context.
    """
    word_accum = len(initial_prompt)
    pointer_safe = 0
    pointer_unsafe = 0

    while pointer_unsafe < len(conversation_log):
        new_words = len(conversation_log[pointer_unsafe])
        if word_accum + new_words < max_chars:
            if pointer_unsafe - pointer_safe == desired_context:
                pointer_safe = pointer_unsafe - 2
                word_accum = len(initial_prompt) + \
                             len(conversation_log[pointer_unsafe]) + \
                             len(conversation_log[pointer_unsafe-1])
        else:
            pointer_safe = pointer_unsafe - 2
            word_accum = len(initial_prompt) + \
                         len(conversation_log[pointer_unsafe]) + \
                         len(conversation_log[pointer_unsafe - 1])
        pointer_unsafe += 1
    return pointer_safe


def build_reply_prompt(initial_prompt, conversation_log, context_turns=5, username="User"):
    """ Generates an LLM reply for a given conversation. The conversation
    should be structured such that it is now the LLM's turn.

    Parameters
    ----------
    initial_prompt : str
        Text used at the beginning of the prompt, right before the dialog.
    conversation_log : list(str)
        List of utterances in this dialog, switching between the text between
        the user and the AI. The user always goes first and last.
    context_turns : int
        How many turns to use in the prompt for context. One turn consists of
        one utterance for the User and one for the AI.
    username : str
        Name of the user that the AI is talking to.

    Returns
    -------
    str
        An utterance that the AI generates in response to the given dialog.
    """
    assert len(conversation_log) % 2 == 1, \
        "The conversation should start and end with the user"
    idx = best_idx(prompt, conversation_log, 2*context_turns, max_chars=1280)
    # The user turns are the even ones, while the odd ones are from the computer
    prompt = ""
    user_turns = [conversation_log[::2]
    response_turns = [conversation_log[1::2]
    for user, resp in zip(user_turns, response_turns):
        if prompt == "":
            prompt = "<s>[INST] <<SYS>> " + 
                     initial_prompt.format(username=username) + " <</SYS>> " +
                     user + " [/INST] " + answer + " </s>"
        else:
            prompt += " <s>[INST] {} [/INST] {} </s>".format(user, resp)
    prompt += "<s>[INST] " + conversation_log[-1] + " [/INST]"
    return prompt


def broadcast_prompt(initial_prompt, speech_log, context_turns=10, username="User"):
    """ Generates an LLM reply for a given broadcast.

    Parameters
    ----------
    llm : Llama()
        Language model used to generate the responses
    initial_prompt : str
        Text used at the beginning of the prompt, right before the speech.
    speech_log : list(str)
        List of utterances in this dialog so far.
    context_turns : int
        How many turns to use in the prompt for context. One turn consists
        of roughly one sentence of the AI.
    username : str
        Name of the user that the AI is talking to.

    Returns
    -------
    str
        An utterance that the AI generates in response to the given speech
        history.
    """
    prompt = initial_prompt.format(username=username) + "\n"
    idx = best_idx(prompt, speech_log, context_turns, max_chars=1300)
    for utterance in speech_log[idx:]:
        prompt += f"I: {utterance}\n"
    prompt += "I: "
    print(f"Current idx: {idx}/{len(speech_log)} - {len(prompt)} chars")
    return prompt
