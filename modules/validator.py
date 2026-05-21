import re

URL_RE = re.compile(r'url=([^\s]+)')
FP_RE = re.compile(r'\b([A-F0-9]{40})\b', re.I)
VER_RE = re.compile(r'ver=(\d+)\.(\d+)\.(\d+)')


def normalize(line: str) -> str:
    line = line.replace('\ufeff', '')
    line = line.replace('\u200b', '')
    line = line.replace('\t', ' ')
    line = re.sub(r'\s+', ' ', line)
    return line.strip()


def valid_webtunnel(line: str) -> bool:

    if not URL_RE.search(line):
        return False

    if not FP_RE.search(line):
        return False

    m = VER_RE.search(line)

    if not m:
        return False

    version = tuple(map(int, m.groups()))

    # выкидываем старый webtunnel
    if version <= (0, 0, 1):
        return False

    return True


def validate_bridge(line: str) -> str | None:

    line = normalize(line)

    if line.lower().startswith('bridge '):
        line = line[7:].strip()

    lower = line.lower()

    if lower.startswith('obfs4 '):
        return 'obfs4'

    if lower.startswith('webtunnel '):

        if not valid_webtunnel(line):
            return None

        return 'webtunnel'

    if lower.startswith('vanilla '):
        return 'vanilla'

    if lower.startswith('snowflake '):
        return 'snowflake'

    if re.match(r'^\d{1,3}(?:\.\d{1,3}){3}:\d+', line):
        return 'vanilla'

    return None
