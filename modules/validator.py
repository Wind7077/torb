import re


def normalize(line: str):

    line = line.replace(
        '\ufeff',
        ''
    )

    line = line.replace(
        '\u200b',
        ''
    )

    line = line.replace(
        '\t',
        ' '
    )

    line = re.sub(
        r'\s+',
        ' ',
        line
    )

    return line.strip()


def validate_bridge(line: str):

    line = normalize(line)

    lower = line.lower()

    if lower.startswith('obfs4 '):
        return 'obfs4'

    if lower.startswith('webtunnel '):
        return 'webtunnel'

    if lower.startswith('vanilla '):
        return 'vanilla'

    if lower.startswith('snowflake '):
        return 'snowflake'

    return None
