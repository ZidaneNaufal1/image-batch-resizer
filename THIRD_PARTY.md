# Third-party software and assets

- **Pillow 12.3.0**: image decoding, EXIF orientation, resizing, and encoding. Installed separately using `requirements.txt`, not copied into this repository. The current upstream license identifies the MIT-CMU License; distributions include notices for bundled codecs and other components. [Official license](https://github.com/python-pillow/Pillow/blob/main/LICENSE). Preserve the notices shipped with the exact distribution if redistributing Pillow or its binaries.
- **Python**: runtime and standard library, under the Python Software Foundation license. Not bundled. [License](https://docs.python.org/3/license.html).
- **Demo/test pictures**: generated in memory by this repository's code using solid colors. No downloaded photographs, fonts, or third-party image assets.
- **GitHub Actions**: `actions/checkout` and `actions/setup-python` are CI integrations, not runtime dependencies.

The project's MIT license covers its original source, tests, and documentation; it does not replace dependency licenses.
