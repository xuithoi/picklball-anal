import os
import tempfile

_storage = tempfile.TemporaryDirectory(prefix='kun-ai-tests-')
os.environ.setdefault('DATA_DIR', _storage.name)
