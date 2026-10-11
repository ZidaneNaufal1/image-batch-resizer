# Contributing

Bug reports, documentation improvements, and focused code contributions are welcome. Search existing issues first. Use English where possible; Indonesian reports are also welcome.

## Development

1. Fork and clone the repository; use Python 3.10+.
2. Create a virtual environment and install `python -m pip install -r requirements.txt`.
3. Make one focused change on a branch.
4. Run `python -m unittest -v` and `python examples/run_demo.py`.
5. Open a pull request describing the problem, behavior change, and verification.

Add a regression test when fixing behavior. Keep the read-only default, unchanged source files, independent output directory, and exclusive-write collision policy. Use synthetic images in tests; do not commit personal photos, credentials, or private EXIF data. Document intentional limitations and any license implications of new dependencies. CI must pass on both supported operating systems.

## Useful reports

Provide Python/Pillow version, OS, exact command, expected/actual behavior, and a small synthetic reproduction. JSON reports can contain filenames: remove private paths before sharing. Do not attach private photos. Security reports follow [SECURITY.md](SECURITY.md).

Be respectful, provide evidence, and give maintainers time to review. No external feedback or merged community contributions are claimed until they actually occur.
