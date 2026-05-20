import re


def validate_bridge(line: str) -> str | None:

    line = line.strip()

    if not line:
        return None

    if line.startswith('obfs4 '):
        return 'obfs4'

    if line.startswith('webtunnel '):
        return 'webtunnel'

    if line.startswith('vanilla '):
        return 'vanilla'

    if line.startswith('snowflake '):
        return 'snowflake'

    # Некоторые источники дают vanilla-мосты просто как IP:PORT без префикса
    bare = re.match(r'^(\d{1,3}\.){3}\d{1,3}:\d+$', line)
    if bare:
        return 'vanilla'

    return None
