import re

# Fallback без базы — определяем страну по диапазонам ASN-подсказкам из IP
# Для полноценной работы: pip install geoip2 + скачать GeoLite2-Country.mmdb
# https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-Country.mmdb

_GEOIP_READER = None
_GEOIP_AVAILABLE = False

try:
    import geoip2.database
    _DB_PATH = 'GeoLite2-Country.mmdb'
    import os
    if os.path.exists(_DB_PATH):
        _GEOIP_READER = geoip2.database.Reader(_DB_PATH)
        _GEOIP_AVAILABLE = True
except ImportError:
    pass


def get_country(ip: str) -> str:
    if not _GEOIP_AVAILABLE or not _GEOIP_READER:
        return 'XX'
    try:
        return _GEOIP_READER.country(ip).country.iso_code or 'XX'
    except:
        return 'XX'


def country_score(country: str) -> int:
    """
    Мосты из цензурирующих стран менее надёжны как точки входа.
    Мосты из нейтральных стран с хорошей инфраструктурой — предпочтительнее.
    """
    BAD = {'RU', 'CN', 'IR', 'BY', 'KP', 'CU', 'VE'}
    GOOD = {'DE', 'NL', 'CH', 'SE', 'NO', 'FI', 'IS', 'CA', 'US', 'FR', 'AT'}
    if country in BAD:
        return -25
    if country in GOOD:
        return 10
    return 0


def country_limit_ok(used_countries: dict, country: str, limit: int = 2) -> bool:
    return used_countries.get(country, 0) < limit
