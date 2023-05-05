
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
    prompt = initial_prompt.format(username=username)
    user_turn = True
    subset = 1+2*context_turns
    for utterance in conversation_log[-subset:]:
        if user_turn:
            user = username
        else:
            user = "I"
        new_line = f"{user}: {utterance}\n"
        prompt += new_line
        user_turn = not user_turn
    prompt += "I: "
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
    prompt = initial_prompt.format(username=username)
    for utterance in speech_log[-context_turns:]:
        prompt += "I: {utterance}\n"
    prompt += "I: "
    return prompt
