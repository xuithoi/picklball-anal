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

    def test_creates_private_configuration_without_login_credentials(self):
        module.configure(self.directory, 'pickleballmvp.run.place', self.legacy)
        target = self.directory / '.env'
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        self.assertNotIn('APP_PASSWORD', target.read_text())
        self.assertIn('DATA_VOLUME=pickleball_data', target.read_text())

    def test_legacy_credentials_do_not_enable_public_deployment_login(self):
        self.legacy.write_text('REQUIRE_AUTH=1\nAPP_USERNAME=kun\nAPP_PASSWORD=' + 'a' * 64 + '\n')
        module.configure(self.directory, 'pickleballmvp.run.place', self.legacy)
        self.assertNotIn('APP_PASSWORD', (self.directory / '.env').read_text())
        self.assertIn('APP_PASSWORD=' + 'a' * 64, self.legacy.read_text())

    def test_preserves_existing_config(self):
        (self.directory / '.env').write_text('existing settings')
        with self.assertRaisesRegex(ValueError, 'preserved'):
            module.configure(self.directory, 'pickleballmvp.run.place', self.legacy)
        self.assertEqual((self.directory / '.env').read_text(), 'existing settings')

    def test_legacy_password_is_not_required(self):
        self.legacy.write_text('APP_USERNAME=kun\n')
        module.configure(self.directory, 'pickleballmvp.run.place', self.legacy)
        self.assertTrue((self.directory / '.env').exists())

    def test_rejects_urls_and_invalid_domains(self):
        for value in ['https://example.com', 'host/api', '-bad.example', 'a..b.com', 'localhost', 'host:443']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                module.configure(self.directory, value, self.legacy)
