"""Safe, offline image batch resizing with a read-only preview by default."""
import argparse
import io
import json
import os
import sys
import warnings
from pathlib import Path

from PIL import Image, ImageOps

VERSION = "1.0.0"
INPUT_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
FORMATS = {"png": ("PNG", ".png"), "jpeg": ("JPEG", ".jpg"), "webp": ("WEBP", ".webp")}
MAX_PIXELS = 40_000_000


def within(path, directory):
    try:
        path.relative_to(directory)
        return True
    except ValueError:
        return False


def validate(input_dir, output_dir, width, height, quality, output_format):
    source, output = Path(input_dir).resolve(), Path(output_dir).resolve()
    if not source.is_dir():
        raise ValueError("Input must be an existing directory.")
    if within(output, source) or within(source, output):
        raise ValueError("Input and output directories must be separate and must not contain each other.")
    if output.exists() and not output.is_dir():
        raise ValueError("Output must be a directory path.")
    if any(type(value) is not int or not 1 <= value <= 16384 for value in (width, height)):
        raise ValueError("Width and height must be integers between 1 and 16384.")
    if type(quality) is not int or not 1 <= quality <= 100:
        raise ValueError("Quality must be an integer between 1 and 100.")
    if output_format not in FORMATS:
        raise ValueError("Output format must be png, jpeg, or webp.")
    return source, output


def target_size(size, width, height):
    scale = min(1.0, width / size[0], height / size[1])
    return (max(1, min(width, round(size[0] * scale))),
            max(1, min(height, round(size[1] * scale))))


def candidates(root, recursive):
    def unreadable(error):
        raise error
    for directory, directories, filenames in os.walk(root, followlinks=False, onerror=unreadable):
        directories[:] = sorted(d for d in directories if not (Path(directory) / d).is_symlink()) if recursive else []
        for name in sorted(filenames):
            path = Path(directory) / name
            if path.suffix.lower() in INPUT_EXTENSIONS:
                yield path


def safe_parent(target, output):
    # Refuse pre-existing redirected parents rather than trusting a suffix check.
    parent = target.parent
    while parent != output:
        if parent.is_symlink():
            raise ValueError("Output parent is a symlink; no file was written.")
        parent = parent.parent
    if not within(target.parent.resolve(), output):
        raise ValueError("Output target escapes its directory.")


def choose_target(base, output, reserved):
    safe_parent(base, output)
    existing = {p.name.casefold() for p in base.parent.iterdir()} if base.parent.exists() else set()
    index = 0
    while True:
        name = base.name if index == 0 else f"{base.stem}_{index}{base.suffix}"
        target = base.with_name(name)
        key = target.relative_to(output).as_posix().casefold()
        if name.casefold() not in existing and key not in reserved:
            reserved.add(key)
            return target
        index += 1


def clean_image(image, output_format):
    # Rebuild pixels so private EXIF/text/ICC metadata is not copied by encoders.
    rgba = image.convert("RGBA")
    clean = Image.frombytes("RGBA", rgba.size, rgba.tobytes())
    if output_format == "jpeg":
        background = Image.new("RGB", clean.size, "white")
        background.paste(clean, mask=clean.getchannel("A"))
        return background
    return clean


def resize_batch(input_dir, output_dir, width=1280, height=1280,
                 output_format="png", quality=85, recursive=False, apply=False):
    source, output = validate(input_dir, output_dir, width, height, quality, output_format)
    records, reserved = [], set()
    encoder, suffix = FORMATS[output_format]
    for path in candidates(source, recursive):
        relative = path.relative_to(source)
        item = {"source": relative.as_posix(), "status": "error"}
        try:
            if path.is_symlink() or not within(path.resolve(), source):
                raise ValueError("Symlink image inputs are not processed.")
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(path) as opened:
                    if opened.format not in {"JPEG", "PNG", "WEBP"}:
                        raise ValueError("Image content must be JPEG, PNG, or WebP.")
                    if opened.width * opened.height > MAX_PIXELS:
                        raise ValueError("Image exceeds the 40 million pixel limit.")
                    if getattr(opened, "n_frames", 1) != 1:
                        raise ValueError("Animated or multi-frame images are not supported.")
                    opened.load()
                    oriented = ImageOps.exif_transpose(opened)
                    size = target_size(oriented.size, width, height)
                    base = (output / relative).with_suffix(suffix)
                    target = choose_target(base, output, reserved)
                    item.update({"original_size": list(opened.size), "oriented_size": list(oriented.size),
                                 "output_size": list(size), "destination": target.relative_to(output).as_posix()})
                    if apply:
                        resized = oriented.resize(size, Image.Resampling.LANCZOS) if size != oriented.size else oriented
                        clean = clean_image(resized, output_format)
                        buffer = io.BytesIO()
                        options = {"quality": quality} if output_format in {"jpeg", "webp"} else {}
                        clean.save(buffer, format=encoder, **options)
                        safe_parent(target, output)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        while True:
                            try:
                                handle = target.open("xb")
                                break
                            except FileExistsError:
                                target = choose_target(base, output, reserved)
                        try:
                            with handle:
                                handle.write(buffer.getvalue())
                        except OSError:
                            # Only this call's exclusive-created incomplete output is removed.
                            target.unlink(missing_ok=True)
                            raise
                        item["destination"] = target.relative_to(output).as_posix()
                        item["status"] = "written"
                    else:
                        item["status"] = "planned"
        except (OSError, ValueError, SyntaxError, Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
            item["message"] = str(exc)
        records.append(item)
    errors = sum(item["status"] == "error" for item in records)
    return {"version": VERSION, "mode": "apply" if apply else "preview", "format": output_format,
            "max_size": [width, height], "images_found": len(records), "errors": errors,
            "ok": errors == 0, "items": records}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Resize image batches offline; preview is the default.")
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=1280)
    parser.add_argument("--format", choices=FORMATS, default="png", dest="output_format")
    parser.add_argument("--quality", type=int, default=85)
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--version", action="version", version=VERSION)
    args = parser.parse_args(argv)
    try:
        report = resize_batch(args.input, args.output, args.width, args.height,
                              args.output_format, args.quality, args.recursive, args.apply)
    except (OSError, ValueError) as exc:
        if args.json_output:
            print(json.dumps({"ok": False, "error": str(exc)}))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 2
    if args.json_output:
        print(json.dumps(report, indent=2))
    else:
        for item in report["items"]:
            detail = item.get("message", f'{item.get("oriented_size")} -> {item.get("output_size")} : {item.get("destination")}')
            print(f'{item["status"]}: {item["source"]}: {detail}')
        print(f'{report["mode"]}: {report["images_found"]} images, {report["errors"]} errors.')
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
