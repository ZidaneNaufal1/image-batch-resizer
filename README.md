# Image Batch Resizer

[![Tests](https://github.com/ZidaneNaufal1/image-batch-resizer/actions/workflows/tests.yml/badge.svg)](https://github.com/ZidaneNaufal1/image-batch-resizer/actions/workflows/tests.yml)

Resize folders of photographs and transparent graphics offline, with a read-only preview before writing. Useful for content creators preparing images for websites and social posts.

## Quick start

Requires Python 3.10+ and Pillow. Tested in CI on Python 3.10, 3.12, and 3.14 on Ubuntu and Windows.

```sh
git clone https://github.com/ZidaneNaufal1/image-batch-resizer.git
cd image-batch-resizer
python -m venv .venv
```

Activate the environment with `.venv\Scripts\Activate.ps1` in PowerShell or `source .venv/bin/activate` on Linux/macOS. Then:

```sh
python -m pip install -r requirements.txt
python batch_resizer.py "photos" "resized" --width 1280 --height 720
python batch_resizer.py "photos" "resized" --width 1280 --height 720 --apply
```

`photos` must exist. `resized` is a separate destination and is created only during apply. The first command reports planned dimensions and filenames; the second writes new images. No upload, API key, or online service is required after installing dependencies.

## Behavior

- JPEG, PNG, and WebP input; PNG (default), JPEG, or WebP output.
- Fit inside maximum width/height, maintain aspect ratio within integer-pixel rounding, and never upscale. A 2000 × 1000 image within 1280 × 720 becomes 1280 × 640.
- Apply EXIF orientation before calculating size. Resize with the LANCZOS filter.
- Preserve transparency in PNG/WebP. JPEG flattens transparency onto white.
- Strip EXIF, text, and ICC metadata from outputs by rebuilding pixels. Source files are never edited. Without ICC conversion, color-managed images may look different in some viewers.
- Add `_1`, `_2`, etc. when output filenames collide. Existing files and directories are not overwritten; name checks are case-insensitive across platforms.
- Recursion is opt-in and retains relative subdirectories. Symlink image files are reported as errors; symlink input subdirectories are skipped; redirected output subdirectories are refused.
- Report corrupt, oversized, unsupported-content, and animated/multi-frame images individually, then continue with valid images.

```sh
python batch_resizer.py "photos" "web-images" --recursive --format webp --quality 85 --apply --json
```

| Option | Default | Meaning |
| --- | --- | --- |
| `--width`, `--height` | 1280 each | Maximum dimensions; integers 1–16384 |
| `--format` | png | png, jpeg, webp |
| `--quality` | 85 | 1–100 for JPEG/WebP; ignored for PNG |
| `--recursive` | off | Include ordinary subdirectories |
| `--apply` | off | Write outputs; otherwise preview only |
| `--json` | off | Machine-readable report on stdout |
| `--version` | — | Print version and exit |

JSON items include source, destination, original/oriented/output dimensions, status, and an error message if needed. Status is `planned`, `written`, or `error`. Exit codes: **0** success (also an empty/unsupported-extension-only folder), **1** one or more image errors, **2** invalid configuration or directory traversal failure. Argument syntax errors use argparse's exit code 2 and text output.

## Safety and limitations

Input/output may not be the same directory or contain each other. Preview decodes inputs to validate them but creates no output directory. Apply encodes each image before opening its destination exclusively; an encoding failure leaves no output file. A batch is not transactional: valid images may already have been written when another image fails. A filesystem write failure removes that call's incomplete file when possible; permission failures can prevent cleanup.

Use stable, trusted local folders. These checks do not defend against another process maliciously changing directory symlinks during execution. Files above 40 million pixels and Pillow decompression-bomb warnings/errors are rejected; this is not a strict memory cap. Full decoding still uses memory, so very large folders should be processed in manageable batches. Animated images, SVG, GIF, HEIC, RAW, custom crops, upscaling, ICC conversion, and metadata retention are outside v1.0. Compression may produce a file larger than the source; resizing does not guarantee byte savings. A preview filename may change if another process creates it before apply.

## Verification and demo

```sh
python -m unittest -v
python examples/run_demo.py
```

The 25 tests cover dimensions, no-upscale, EXIF, metadata removal, transparency, all output formats, collisions, recursion, corrupt and animated inputs, pixel limits, path guards, encoding failures, directory errors, source preservation, and JSON exit codes. Symlink guard unit tests simulate flags to work without Windows symlink privileges; they do not certify hostile concurrent filesystem behavior.

The demo creates synthetic images in a temporary workspace, verifies a preview writes nothing, resizes an 800 × 400 transparent banner to 200 × 100 and an EXIF-rotated portrait to 100 × 200, checks unchanged source bytes, and cleans up. No personal image assets are bundled. [CI results](https://github.com/ZidaneNaufal1/image-batch-resizer/actions) are the cross-platform evidence.

## Ringkasan Bahasa Indonesia

Alat ini mengecilkan banyak gambar sambil menjaga proporsi, memperbaiki orientasi foto, dan menyimpan hasil ke folder terpisah. Jalankan tanpa `--apply` untuk melihat rencana terlebih dahulu; tambahkan `--apply` untuk menyimpan. Gambar asli tidak diubah. Nama bentrok mendapat akhiran angka, gambar rusak dilaporkan, dan gambar valid tetap diproses. Dokumentasi utama menggunakan English agar dapat digunakan serta dikembangkan oleh kontributor internasional.

## Maintenance and ownership

Project owner and maintainer: Muhammad Zidane Naufal Azzam ([ZidaneNaufal1](https://github.com/ZidaneNaufal1)). Developed with AI assistance from Ciel (OpenAI Codex) for implementation, tests, and documentation. Automated checks demonstrate specific behavior; independent review and real user feedback remain welcome. See [CONTRIBUTING](CONTRIBUTING.md), [SECURITY](SECURITY.md), [CHANGELOG](CHANGELOG.md), and [open issues](https://github.com/ZidaneNaufal1/image-batch-resizer/issues).

Licensed under MIT. Pillow and generated demo assets are documented in [THIRD_PARTY](THIRD_PARTY.md). Technical references: [Pillow ImageOps](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html) and [Image](https://pillow.readthedocs.io/en/stable/reference/Image.html).
