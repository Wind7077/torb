import re


def validate_bridge(line: str):

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

    return None
