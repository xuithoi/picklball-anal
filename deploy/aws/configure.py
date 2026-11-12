"""Create private settings for the public EC2 deployment."""
import os
import re
import sys
from pathlib import Path


def configure(directory, domain, legacy):
    if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?', domain) or '.' not in domain or '..' in domain:
        raise ValueError('Supply a DNS hostname only, without https://, a port or /api.')
    target = directory / '.env'
    if target.exists():
        raise ValueError('Existing .env preserved. Edit it locally if configuration needs changing.')
    content = f'BACKEND_DOMAIN={domain}\nMAX_UPLOAD_MB=100\nDATA_VOLUME=pickleball_data\n'
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(content)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit('Usage: bash configure.sh pickleballmvp.run.place')
    try:
        configure(Path(__file__).resolve().parent, sys.argv[1], Path.home() / 'pickleball-backend.env')
    except (ValueError, OSError) as exc:
        sys.exit(str(exc))
    print('Created private .env for public access; no login credentials are required.')
