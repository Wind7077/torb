import re

OBFS4_RE = re.compile(
    r'^obfs4\s+'
    r'([^\s:]+):(\d+)\s+'
    r'([A-F0-9]{40})\s+'
    r'cert=.+'
)

WEBTUNNEL_RE = re.compile(
    r'^webtunnel\s+'
    r'([^\s:]+):(\d+)\s+'
    r'([A-F0-9]{40}).+'
)

SNOWFLAKE_RE = re.compile(
    r'^snowflake\s+'
)

VANILLA_RE = re.compile(
    r'^vanilla\s+'
)

def validate_bridge(line: str):
    line = line.strip()

    if OBFS4_RE.match(line):
        return 'obfs4'

    if WEBTUNNEL_RE.match(line):
        return 'webtunnel'

    if SNOWFLAKE_RE.match(line):
        return 'snowflake'

    if VANILLA_RE.match(line):
        return 'vanilla'

    return None
