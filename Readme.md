Radiobot
========
A project that simulates a radio for taking with a Large Language Model (LLM).

The system supports two modes, `chat` and `talk`. In `chat` mode you can talk
to the system, while `talk` mode lets the model generate infinite text.


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


Attributions
------------
The [static noise sound](https://commons.wikimedia.org/wiki/File:Gray_noise.ogg)
has been created by User `Omegatron` in Wikimedia 
and released in the public domain.

The [button clicking sound](https://freesound.org/people/OneKellyOrdered/sounds/624631/)
has been created by User `OneKellyOrdered` and released 
with a Creative Commons 0 license.
