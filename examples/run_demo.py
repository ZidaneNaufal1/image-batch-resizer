"""Reproducible synthetic demo; never reads personal photographs."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image
from batch_resizer import resize_batch


def main():
    scratch = Path(__file__).resolve().parents[1] / '.tmp-tests'
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as temporary:
        root = Path(temporary)
        source, output = root / 'source', root / 'output'
        source.mkdir()
        Image.new('RGBA', (800, 400), (40, 140, 230, 100)).save(source / 'banner.png')
        exif = Image.Exif()
        exif[274] = 6
        Image.new('RGB', (300, 150), 'orange').save(source / 'portrait.jpg', exif=exif)
        before = {p.name: p.read_bytes() for p in source.iterdir()}
        preview = resize_batch(source, output, width=200, height=200)
        assert preview['ok'] and not output.exists()
        applied = resize_batch(source, output, width=200, height=200, apply=True)
        assert applied['ok']
        with Image.open(output / 'banner.png') as banner:
            assert banner.size == (200, 100) and banner.getpixel((0, 0))[3] == 100
        with Image.open(output / 'portrait.png') as portrait:
            assert portrait.size == (100, 200)
        assert before == {p.name: p.read_bytes() for p in source.iterdir()}
        print(json.dumps(applied, indent=2))
        print('PASS: preview wrote nothing; sizes/orientation/alpha verified; source bytes unchanged.')


if __name__ == '__main__':
    main()
