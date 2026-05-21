import re


def normalize(line: str) -> str:
    line = line.replace('\ufeff', '')
    line = line.replace('\u200b', '')
    line = line.replace('\t', ' ')
    line = re.sub(r'\s+', ' ', line)
    return line.strip()


def validate_bridge(line: str) -> str | None:
    line = normalize(line)

    # Убираем префикс "Bridge " (torrc-формат)
    if line.lower().startswith('bridge '):
        line = line[7:].strip()

    lower = line.lower()

    if lower.startswith('obfs4 '):
        return 'obfs4'
    if lower.startswith('webtunnel '):
        return 'webtunnel'
    if lower.startswith('vanilla '):
        return 'vanilla'
    if lower.startswith('snowflake '):
        return 'snowflake'

    # Vanilla без префикса: просто IP:PORT или IP:PORT FINGERPRINT
    if re.match(r'^\d{1,3}(?:\.\d{1,3}){3}:\d+', line):
        return 'vanilla'

    return None
