Radiobot
========
A project that simulates a radio for taking with a Large Language Model (LLM).

The system supports two modes, `chat` and `radio`. In `chat` mode you can talk
to the system, while `radio` mode lets the model generate infinite text.

A second script `endless_gen.py` generates infinite text.

Installation
------------
First, install the system dependencies. In Debian you install it with:

```
apt-get install libffi-dev ffmpeg
```

Most Python dependencies are listed in the `requirements.txt` file.
You can create a virtual environment for them and install all dependencies
with the following commands:

```
python3 -m venv <path/to/virtual_env>
source <path/to/virtual_env>/bin/activate
pip3 install -r requirements.txt
pip3 install --force-reinstall --no-binary :all: cffi
```

Once this is done, you can activate this environment whenever you want to use
the software with the command:

```
source <path/to/virtual_env>/bin/activate
```

Note, however, that `mimic3` requires Python 3.9. If you have Python 3.11 the
best alternative is to use [Miniforge](https://github.com/conda-forge/miniforge)
to install an earlier version.
Once installed, you can create a Conda environment with the command:

```
conda create --name radiobot python=3.9
conda activate radiobot
pip3 install -r requirements.txt
pip3 install --force-reinstall --no-binary :all: cffi
```

And you activate it with:

```
conda activate radiobot
```

Usage
-----
You run the code with the command:

```
python3 radiobot.py <path/to/llm>
```

You need a configuration file before your first run. The provided file
`config.json.template` is an example of such a file. You can copy it to a
file named `config.json`.

The tweakable parameters are:

  * `username`: any name written here will be used in your dialog prompt.
  * `dialog_prompt`: prompt for the dialog mode. This prompt is repeated at
    every generation, ensuring that the conversation remains on track.
  * `dialog_seed`: lines of dialog to jump-start the conversation. The first
    conversation is assumed to be by the user, the second one by the AI, and so
    on. Given that the system starts running after the first recording, the
    dialog seed must contain an even number of utterances.
  * `monologue_prompt`: prompt to use for the radio mode. This prompt is also
    repeated before every utterance to keep the monologue on track.
  * `monologue_seed`: some examples of the type of utterances that the system
    should generate.
  * `tts`: parameters for the text-to-speech system. If you want to change the
    speaker you can do so here. You can listen to all available voices following
    [this link](https://mycroftai.github.io/mimic3-voices/).
  * `screen_width` and `screen_height`: screen size to use for the PyGame
    window. Given that this code is designed with a retro aesthetic, it is
    recommended to choose a low resolution and toggle fullscreen.

By default the program shows a single screen with a radio and plays static
noise. 

  * To talk to the system press the space bar to talk and release it once
    you're done talking. The system's reply will be played over the speakers.
  * Use the R key to toggle radio mode. When in radio mode the system will
    speak constantly. Press R again to go back to chat mode.
  * Use the F key to toggle fulscreen mode.

The program supports the following flags:

  * `--no-gui` disables the GUI and shows only general debugging output.
    Useful for running in text-only mode.
  * `--no-mic` disables the speech recognition. In this mode you enter text
    in the console and the system speaks back. Given that you need access to
    the console to type, this mode also activates `--no-gui`.
  * You can use the `-llm` parameter to select a path to a specific LLM. At this
    time the current only support the quantized 4-bit version provided by the
    `llama.cpp` project.


endless_gen.py
--------------
The script `endless_gen.py` will generate a never-ending stream of texts.
These texts will use the same prompt defined for radio mode.

You can stop the program pressing Ctrl-C. The program generates two files as
output, one where every line is stored as plain text plus a second file in
SSML format with extra instructions for making a small pause between
lines.

You can play the SSML file with the command:

```
mimic3 --ssml --interactive --voice 'en_US/hifi-tts_low#92' < file.ssml
```

Using a different llama.cpp
---------------------------
If you want to install a specific version of `llama.cpp` while keeping
the Python bindings, or if you need some specific compile flags
(for instance, if you run into
[this bug](https://github.com/ggerganov/whisper.cpp/issues/876)),
you can do so by compiling the library as a separate project and then
copying the `libllama.so` file.

This is an example for how to compile directly with the `LLAMA_CUBLAS`
flag:

```
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
LLAMA_CUBLAS=1 make libllama.so
# Your path may be slightly different here
cp libllama.so <path/to/virtual_env>/lib/python3.9/site-packages/llama_cpp/libllama.so
```

Attributions
------------
The [static noise sound](https://commons.wikimedia.org/wiki/File:Gray_noise.ogg)
has been created by User `Omegatron` in Wikimedia 
and released in the public domain.

The [button clicking sound](https://freesound.org/people/OneKellyOrdered/sounds/624631/)
has been created by User `OneKellyOrdered` and released under a
Creative Commons 0 license.

The prompts provided in the default config file are written according to the
schema presented in the paper "Concept-based Persona Expansion for
Improving Diversity of Persona-Grounded Dialogue" (Kim et al. 2023).
