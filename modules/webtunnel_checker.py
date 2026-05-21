import asyncio
import tempfile
import os
import re
import shutil

URL_RE = re.compile(r'url=([^\s]+)')
FP_RE = re.compile(r'\b([A-F0-9]{40})\b', re.I)
VER_RE = re.compile(r'ver=(\d+)\.(\d+)\.(\d+)')


def validate_webtunnel_line(line: str) -> bool:

    if not URL_RE.search(line):
        return False

    if not FP_RE.search(line):
        return False

    if not VER_RE.search(line):
        return False

    return True


async def tor_bootstrap_webtunnel(
    bridge_line: str,
    timeout: int = 90
) -> bool:

    temp_dir = tempfile.mkdtemp(prefix='tor_wt_')

    torrc = f'''
UseBridges 1
ClientTransportPlugin webtunnel exec /usr/bin/lyrebird
Bridge {bridge_line}
SocksPort auto
DataDirectory {temp_dir}
Log notice stdout
'''

    torrc_path = os.path.join(temp_dir, 'torrc')

    with open(torrc_path, 'w', encoding='utf-8') as f:
        f.write(torrc)

    try:

        proc = await asyncio.create_subprocess_exec(
            'tor',
            '-f',
            torrc_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )

        try:

            while True:

                line = await asyncio.wait_for(
                    proc.stdout.readline(),
                    timeout=timeout
                )

                if not line:
                    break

                text = line.decode(errors='ignore')

                if 'Bootstrapped 100%' in text:
                    proc.kill()
                    return True

                lower = text.lower()

                bad = [
                    'failed',
                    'timeout',
                    'connection refused',
                    'bridge unreachable',
                    'general socks server failure',
                    'proxy client failed',
                    'handshake',
                    'websocket',
                    'tls error',
                ]

                if any(x in lower for x in bad):
                    proc.kill()
                    return False

        except asyncio.TimeoutError:
            proc.kill()
            return False

    except:
        return False

    finally:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )

    return False


async def reliable_webtunnel_check(
    line: str,
    retries: int = 1
) -> int | None:

    if not validate_webtunnel_line(line):
        return None

    for _ in range(retries):

        ok = await tor_bootstrap_webtunnel(line)

        if ok:
            return 1

    return None
