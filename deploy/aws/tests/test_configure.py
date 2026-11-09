import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('configure', Path(__file__).parents[1] / 'configure.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ConfigureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.legacy = self.directory / 'old.env'

    def test_creates_private_configuration_with_generated_password(self):
        module.configure(self.directory, 'pickleballmvp.run.place', self.legacy)
        target = self.directory / '.env'
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        self.assertRegex(target.read_text(), r'APP_PASSWORD=[a-f0-9]{64}\n')
        self.assertIn('DATA_VOLUME=pickleball_data', target.read_text())

    def test_reuses_existing_ec2_password(self):
        self.legacy.write_text('REQUIRE_AUTH=1\nAPP_USERNAME=kun\nAPP_PASSWORD=' + 'a' * 64 + '\n')
        module.configure(self.directory, 'pickleballmvp.run.place', self.legacy)
        self.assertIn('APP_PASSWORD=' + 'a' * 64, (self.directory / '.env').read_text())

    def test_preserves_existing_config(self):
        (self.directory / '.env').write_text('existing settings')
        with self.assertRaisesRegex(ValueError, 'preserved'):
            module.configure(self.directory, 'pickleballmvp.run.place', self.legacy)
        self.assertEqual((self.directory / '.env').read_text(), 'existing settings')

    def test_rejects_missing_legacy_password_without_creating_configuration(self):
        self.legacy.write_text('APP_USERNAME=kun\n')
        with self.assertRaisesRegex(ValueError, 'manual migration'):
            module.configure(self.directory, 'pickleballmvp.run.place', self.legacy)
        self.assertFalse((self.directory / '.env').exists())

    def test_rejects_urls_and_invalid_domains(self):
        for value in ['https://example.com', 'host/api', '-bad.example', 'a..b.com', 'localhost', 'host:443']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                module.configure(self.directory, value, self.legacy)
