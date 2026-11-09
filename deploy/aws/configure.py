"""Create a private Compose configuration without exposing or replacing credentials."""
import os
import re
import secrets
import sys
from pathlib import Path


def configure(directory, domain, legacy):
    if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?', domain) or '.' not in domain or '..' in domain:
        raise ValueError('Supply a DNS hostname only, without https://, a port or /api.')
    target = directory / '.env'
    if target.exists():
        raise ValueError('Existing .env preserved. Edit it locally if configuration needs changing.')
    username = 'kun'
    password = secrets.token_hex(32)
    if legacy.exists():
        values = dict(line.split('=', 1) for line in legacy.read_text().splitlines() if '=' in line and not line.startswith('#'))
        username = values.get('APP_USERNAME', 'kun')
        password = values.get('APP_PASSWORD', '')
        # The earlier EC2 setup generated a hexadecimal password. Refuse ambiguous
        # dotenv syntax instead of silently changing an existing credential.
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', username) or not re.fullmatch(r'[A-Za-z0-9_-]{16,}', password):
            raise ValueError('Existing backend credentials need manual migration into the private .env file; they were not changed.')
    content = f'BACKEND_DOMAIN={domain}\nAPP_USERNAME={username}\nAPP_PASSWORD={password}\nMAX_UPLOAD_MB=100\nDATA_VOLUME=pickleball_data\n'
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
    print('Created private .env; existing backend credentials were reused when present. No password was printed.')
