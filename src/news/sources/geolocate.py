# src/news/sources/geolocate.py
# IP geolocation via neohiro/apis public connector.
# All services are free, no auth, no user data.
#
# neohiro/apis public connector endpoints:
#   GET /api/ip/<ip>              → ipinfo.io or ip-api.com
#   GET /api/ip/geo/<ip>          → extended with GeoLite2-style data
#
# If neohiro/apis is not deployed, falls back directly to public services.
# All responses are public data (IP location, ASN, org). No PII.

from __future__ import annotations

import json
import os
import socket
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError


from . import BaseSource, NewsItem, register_source


UA = "neohiro-news/1.0 (+https://github.com/neohiro/news)"


# neohiro/apis public connector base (set by neohiro/apis deployment)
_APIS_BASE = os.environ.get("NEWS_APIS_BASE", "")  # e.g. https://api.neohiro.io


# ─── Dataclass ──────────────────────────────────────────────────────────────

@dataclass
class GeoResult:
    ip: str
    lat: float | None
    lon: float | None
    city: str | None
    region: str | None
    country: str | None
    country_code: str | None
    isp: str | None
    org: str | None
    asn: str | None
    timezone: str | None
    fetched_at: str = ""
    source: str = ""

    def __post_init__(self):
        if not self.fetched_at:
            self.fetched_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "ip": self.ip,
            "lat": self.lat,
            "lon": self.lon,
            "city": self.city,
            "region": self.region,
            "country": self.country,
            "country_code": self.country_code,
            "isp": self.isp,
            "org": self.org,
            "asn": self.asn,
            "timezone": self.timezone,
            "fetched_at": self.fetched_at,
            "source": self.source,
        }


# ─── Free public geolocation services ───────────────────────────────────────

def _fetch_ipapi(ip: str) -> GeoResult | None:
    """ip-api.com — free, no key, 45 req/min. Returns lat/lon, city, country."""
    url = f"http://ip-api.com/json/{urllib.parse.quote(ip)}?fields=status,message,country,countryCode,region,regionName,city,lat,lon,isp,org,as,timezone"
    try:
        req = Request(url, headers={"User-Agent": UA})
        with urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (URLError, json.JSONDecodeError):
        return None
    if data.get("status") != "success":
        return None
    return GeoResult(
        ip=ip,
        lat=data.get("lat"),
        lon=data.get("lon"),
        city=data.get("city"),
        region=data.get("regionName"),
        country=data.get("country"),
        country_code=data.get("countryCode"),
        isp=data.get("org") or data.get("isp"),
        org=data.get("org"),
        asn=data.get("as"),
        timezone=data.get("timezone"),
        source="ip-api.com",
    )


def _fetch_ipinfo(ip: str) -> GeoResult | None:
    """ipinfo.io — free tier, no key for basic (city/country only)."""
    url = f"https://ipinfo.io/{urllib.parse.quote(ip)}/json"
    try:
        req = Request(url, headers={"User-Agent": UA})
        with urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (URLError, json.JSONDecodeError):
        return None
    if "bogon" in data:
        return None
    # ipinfo returns "loc": "lat,lon"
    loc = (data.get("loc") or "").split(",")
    lat = float(loc[0]) if len(loc) >= 1 and loc[0] else None
    lon = float(loc[1]) if len(loc) >= 2 and loc[1] else None
    return GeoResult(
        ip=ip,
        lat=lat,
        lon=lon,
        city=data.get("city"),
        region=data.get("region"),
        country=data.get("country"),
        country_code=None,
        isp=None,
        org=data.get("org"),
        asn=data.get("org"),
        timezone=data.get("timezone"),
        source="ipinfo.io",
    )


# ─── neohiro/apis connector ─────────────────────────────────────────────────

def _fetch_apis(ip: str) -> GeoResult | None:
    """Try neohiro/apis public connector first, then fall back."""
    if not _APIS_BASE:
        return None
    url = f"{_APIS_BASE}/api/ip/{urllib.parse.quote(ip)}"
    try:
        req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        with urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (URLError, json.JSONDecodeError):
        return None
    return GeoResult(
        ip=ip,
        lat=data.get("lat"),
        lon=data.get("lon"),
        city=data.get("city"),
        region=data.get("region"),
        country=data.get("country"),
        country_code=data.get("country_code"),
        isp=data.get("isp"),
        org=data.get("org"),
        asn=data.get("asn"),
        timezone=data.get("timezone"),
        source="neohiro/apis",
    )


# ─── Main API ───────────────────────────────────────────────────────────────

def geolocate(ip: str) -> GeoResult | None:
    """Geolocate an IP address. Tries neohiro/apis → ip-api.com → ipinfo.io."""
    if not ip or ip in ("", "127.0.0.1", "::1", "localhost"):
        return None
    # Try neohiro/apis first
    r = _fetch_apis(ip)
    if r:
        return r
    # Fall back to ip-api.com
    r = _fetch_ipapi(ip)
    if r:
        return r
    # Last resort: ipinfo.io
    return _fetch_ipinfo(ip)


def geolocate_self() -> GeoResult | None:
    """Geolocate the machine this script runs on."""
    ip = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except OSError:
        pass
    if not ip:
        return None
    return geolocate(ip)


def reverse_geocode(lat: float, lon: float) -> str | None:
    """Get a country/region label from lat/lon using a free reverse geocoder."""
    # Nominatim (OpenStreetMap) — free, no key, 1 req/sec max
    url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&zoom=3"
    try:
        req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        with urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (URLError, json.JSONDecodeError):
        return None
    addr = data.get("address") or {}
    parts = []
    for key in ("city", "state", "country"):
        v = addr.get(key)
        if v:
            parts.append(v)
    return ", ".join(parts) if parts else addr.get("country")


# ─── Source class (for CLI integration) ─────────────────────────────────────

@register_source
class GeolocateSource(BaseSource):
    name = "geolocate"

    def fetch(self) -> list[dict]:
        """Fetch geolocation of self + public IPs."""
        results: list[dict] = []
        # Self
        r = geolocate_self()
        if r:
            results.append(r.to_dict())
        return results
