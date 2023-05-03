
Installation
------------
Most Python dependencies are listed in the `requirements.txt` file.

The `libffi` library has to be installed with the following command
which may require the `libffi-dev` package:

```
pip install --force-reinstall --no-binary :all: cffi
```

The following non-Python dependencies are also needed: `ffmpeg`.