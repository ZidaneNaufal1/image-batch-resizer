# Security policy

Only the latest released version is supported. Keep Python and Pillow updated; review dependency updates and run the tests before adopting them.

The tool works offline and never uploads images. Outputs omit EXIF/text/ICC metadata, but visible image content and filenames can still be private. It processes trusted local folders and is not a sandbox for malicious files or concurrently modified directory trees. See the README for pixel limits and partial-batch behavior.

If GitHub offers **Security → Report a vulnerability**, use that private channel for suspected vulnerabilities. Otherwise open a minimal issue asking the maintainer for a private reporting channel without publishing an exploit, sensitive paths, or private images. A response time is not guaranteed.
