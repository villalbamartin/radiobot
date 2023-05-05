Radiobot
========
A project that simulates a radio for taking with a Large Language Model (LLM).

The system supports two modes, `chat` and `radio`. In `chat` mode you can talk
to the system, while `radio` mode lets the model generate infinite text.


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
pip install -r requirements.txt
pip install --force-reinstall --no-binary :all: cffi
```

Once this is done, you can activate this environment whenever you want to use
the software with the command:

```
source <path/to/virtual_env>/bin/activate
```

Usage
-----
You run the code with the command:

```
python3 radiobot.py <path/to/llm>
```

By default the program shows a single screen with a radio and plays static
noise. 

  * To talk to the system press the space bar to talk and release it once
    you're done talking. The system's reply will be played over the speakers.
  * Use the R key to toggle radio mode. When in radio mode the system will
    speak constantly. Press R again to go back to chat mode.

The program supports the following flags:

  * `--no-gui` disables the GUI and shows only general debugging output.
    Useful for running in text-only mode.
  * `--no-mic` disables the speech recognition. In this mode you enter text
    in the console and the system speaks back. Given that you need access to
    the console to type, this mode also activates `--no-gui`.
  * You can use the `-llm` parameter to select a path to a specific LLM.


Attributions
------------
The [static noise sound](https://commons.wikimedia.org/wiki/File:Gray_noise.ogg)
has been created by User `Omegatron` in Wikimedia 
and released in the public domain.

The [button clicking sound](https://freesound.org/people/OneKellyOrdered/sounds/624631/)
has been created by User `OneKellyOrdered` and released 
with a Creative Commons 0 license.
