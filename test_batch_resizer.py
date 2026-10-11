import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, PngImagePlugin
import batch_resizer as br


class BatchTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).parent / '.tmp-tests'
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'input'
        self.source.mkdir()
        self.output = self.root / 'output'

    def image(self, name='photo.png', size=(200, 100), color=(255, 0, 0, 128), **options):
        path = self.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        image = Image.new('RGBA', size, color)
        if path.suffix.lower() in {'.jpg', '.jpeg'}:
            image = image.convert('RGB')
        image.save(path, **options)
        return path

    def run_batch(self, **options):
        return br.resize_batch(self.source, self.output, **options)

    def test_landscape_and_portrait_bounds(self):
        for size, expected in [((200, 100), (80, 40)), ((100, 200), (30, 60))]:
            with self.subTest(size=size):
                self.assertEqual(br.target_size(size, 80, 60), expected)

    def test_rounding_and_extreme_ratio(self):
        self.assertEqual(br.target_size((101, 33), 50, 50), (50, 16))
        self.assertEqual(br.target_size((10000, 1), 20, 20), (20, 1))

    def test_small_image_not_upscaled(self):
        self.image(size=(20, 10))
        self.assertEqual(self.run_batch()['items'][0]['output_size'], [20, 10])

    def test_preview_reads_without_writing(self):
        path = self.image()
        original = path.read_bytes()
        report = self.run_batch(width=40, height=40)
        self.assertEqual(report['items'][0]['status'], 'planned')
        self.assertFalse(self.output.exists())
        self.assertEqual(path.read_bytes(), original)

    def test_apply_preserves_source_bytes_and_dimensions(self):
        path = self.image()
        original = path.read_bytes()
        report = self.run_batch(width=40, height=40, apply=True)
        self.assertEqual(report['items'][0]['status'], 'written')
        with Image.open(self.output / 'photo.png') as result:
            self.assertEqual(result.size, (40, 20))
        self.assertEqual(path.read_bytes(), original)

    def test_exif_orientation_and_private_metadata_removed(self):
        exif = Image.Exif()
        exif[274] = 6
        exif[315] = 'private author'
        self.image('rotated.jpg', size=(80, 40), exif=exif)
        item = self.run_batch(width=40, height=40, apply=True)['items'][0]
        self.assertEqual(item['oriented_size'], [40, 80])
        self.assertEqual(item['output_size'], [20, 40])
        with Image.open(self.output / 'rotated.png') as result:
            self.assertFalse(result.getexif())

    def test_png_text_metadata_removed(self):
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text('Author', 'private')
        self.image(pnginfo=metadata)
        self.run_batch(apply=True)
        with Image.open(self.output / 'photo.png') as result:
            self.assertNotIn('Author', result.info)

    def test_png_alpha_preserved(self):
        self.image(size=(5, 5), color=(0, 255, 0, 64))
        self.run_batch(apply=True)
        with Image.open(self.output / 'photo.png') as result:
            self.assertEqual(result.getpixel((2, 2))[3], 64)

    def test_jpeg_transparency_flattened_on_white(self):
        self.image(size=(5, 5), color=(255, 0, 0, 0))
        self.run_batch(apply=True, output_format='jpeg', quality=100)
        with Image.open(self.output / 'photo.jpg') as result:
            self.assertEqual(result.mode, 'RGB')
            self.assertTrue(all(channel >= 250 for channel in result.getpixel((2, 2))))

    def test_webp_dimensions_and_alpha(self):
        self.image(size=(10, 10), color=(0, 255, 0, 64))
        self.run_batch(apply=True, output_format='webp', width=5, height=5)
        with Image.open(self.output / 'photo.webp') as result:
            self.assertEqual(result.size, (5, 5))
            self.assertEqual(result.getpixel((2, 2))[3], 64)

    def test_same_stem_and_existing_case_insensitive_collision(self):
        self.image('photo.jpg')
        self.image('photo.png')
        self.output.mkdir()
        existing = self.output / 'PHOTO.PNG'
        existing.write_bytes(b'do not replace')
        report = self.run_batch(apply=True)
        self.assertEqual([x['destination'] for x in report['items']], ['photo_1.png', 'photo_2.png'])
        self.assertEqual(existing.read_bytes(), b'do not replace')

    def test_recursion_is_opt_in_and_preserves_relative_paths(self):
        self.image('top.png')
        self.image('nested/photo.png')
        self.assertEqual(self.run_batch()['images_found'], 1)
        report = self.run_batch(recursive=True, apply=True)
        self.assertEqual(report['images_found'], 2)
        self.assertTrue((self.output / 'nested/photo.png').is_file())

    def test_corrupt_image_does_not_stop_valid_images(self):
        (self.source / 'broken.png').write_bytes(b'not an image')
        self.image()
        report = self.run_batch(apply=True)
        self.assertEqual(report['errors'], 1)
        self.assertTrue((self.output / 'photo.png').exists())
        self.assertFalse((self.output / 'broken.png').exists())

    def test_wrong_content_rejected(self):
        Image.new('RGB', (5, 5)).save(self.source / 'fake.png', format='BMP')
        self.assertIn('content', self.run_batch()['items'][0]['message'])

    def test_animated_png_rejected(self):
        Image.new('RGB', (5, 5), 'red').save(self.source / 'animation.png',
            save_all=True, append_images=[Image.new('RGB', (5, 5), 'blue')], duration=100)
        self.assertIn('multi-frame', self.run_batch()['items'][0]['message'])

    def test_pixel_limit_rejected_before_output(self):
        self.image(size=(20, 20))
        with patch.object(br, 'MAX_PIXELS', 100):
            self.assertEqual(self.run_batch(apply=True)['errors'], 1)
        self.assertFalse(self.output.exists())

    def test_overlapping_directories_rejected(self):
        for target in (self.source, self.source / 'nested', self.root):
            with self.subTest(target=target), self.assertRaises(ValueError):
                br.resize_batch(self.source, target)

    def test_invalid_configuration_rejected(self):
        for config in ({'width': 0}, {'height': 16385}, {'width': True}, {'quality': 101}, {'output_format': 'gif'}):
            with self.subTest(config=config), self.assertRaises(ValueError):
                self.run_batch(**config)

    def test_missing_input_and_output_file_rejected(self):
        with self.assertRaises(ValueError):
            br.resize_batch(self.root / 'missing', self.output)
        self.output.write_text('existing file')
        with self.assertRaises(ValueError):
            self.run_batch()

    def test_symlink_file_refused(self):
        self.image()
        original = Path.is_symlink
        with patch.object(Path, 'is_symlink', lambda path: path.name == 'photo.png' or original(path)):
            self.assertIn('Symlink', self.run_batch()['items'][0]['message'])

    def test_redirected_output_parent_refused(self):
        self.image('nested/photo.png')
        original = Path.is_symlink
        with patch.object(Path, 'is_symlink', lambda path: path == self.output / 'nested' or original(path)):
            self.assertEqual(self.run_batch(recursive=True, apply=True)['errors'], 1)
        self.assertFalse(self.output.exists())

    def test_encoding_failure_leaves_no_output(self):
        self.image()
        with patch.object(Image.Image, 'save', side_effect=OSError('encoding failed')):
            self.assertEqual(self.run_batch(apply=True)['errors'], 1)
        self.assertFalse(self.output.exists())

    def test_cli_json_exit_codes(self):
        self.image()
        def call(extra=()):
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                code = br.main([str(self.source), str(self.output), '--json', *extra])
            return code, json.loads(stream.getvalue())
        self.assertEqual(call()[0], 0)
        (self.source / 'broken.png').write_bytes(b'broken')
        self.assertEqual(call()[0], 1)
        code, report = call(['--width', '0'])
        self.assertEqual(code, 2)
        self.assertFalse(report['ok'])

    def test_unreadable_directory_is_reported_not_silently_ignored(self):
        def inaccessible(*args, **kwargs):
            kwargs['onerror'](PermissionError('cannot read directory'))
            return iter(())
        with patch.object(br.os, 'walk', inaccessible), self.assertRaises(PermissionError):
            self.run_batch()

    def test_empty_directory_returns_success_without_creating_output(self):
        (self.source / 'notes.txt').write_text('ignored')
        self.assertEqual(self.run_batch()['images_found'], 0)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
