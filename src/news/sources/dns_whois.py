# src/news/sources/dns_whois.py
# DNS + WHOIS via neohiro/apis public connector.
# All services are free public APIs. Zero user data.
#
# neohiro/apis public connector endpoints:
#   GET /api/dns/<domain>         → Cloudflare 1.1.1.1 resolver
#   GET /api/whois/<domain>        → RDAP (publicrdap.org, no key)
#   GET /api/dns/reverse/<ip>      → PTR lookup
#
# If neohiro/apis not deployed, falls back to direct public services.

from __future__ import annotations

import json
import os
import socket
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError


UA = "neohiro-news/1.0 (+https://github.com/neohiro/news)"
_APIS_BASE = os.environ.get("NEWS_APIS_BASE", "")


# ─── Dataclasses ────────────────────────────────────────────────────────────

@dataclass
class DNSResult:
    domain: str
    records: dict[str, list[str]] = field(default_factory=dict)
    fetched_at: str = ""
    source: str = ""
    error: str | None = None

    def __post_init__(self):
        if not self.fetched_at:
            self.fetched_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "records": self.records,
            "fetched_at": self.fetched_at,
            "source": self.source,
            "error": self.error,
        }


@dataclass
class WHOISResult:
    domain: str
    registrar: str | None = None
    created: str | None = None
    expires: str | None = None
    nameservers: list[str] = field(default_factory=list)
    status: str | None = None
    org: str | None = None
    country: str | None = None
    fetched_at: str = ""
    source: str = ""

    def __post_init__(self):
        if not self.fetched_at:
            self.fetched_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "registrar": self.registrar,
            "created": self.created,
            "expires": self.expires,
            "nameservers": self.nameservers,
            "status": self.status,
            "org": self.org,
            "country": self.country,
            "fetched_at": self.fetched_at,
            "source": self.source,
        }


# ─── DNS ────────────────────────────────────────────────────────────────────

def dns_lookup(domain: str, qtype: str = "A") -> list[str]:
    """Resolve a DNS record. Uses socket.getaddrinfo (system resolver) + Cloudflare."""
    # Try system resolver first
    try:
        results = socket.getaddrinfo(domain, None, socket.AF_INET if qtype == "A" else socket.AF_INET6)
        return list(dict.fromkeys(r[4][0] for r in results))
    except socket.gaierror:
        pass
    # Fall back to 1.1.1.1 via HTTPS
    url = f"https://cloudflare-dns.com/dns-query?name={urllib.parse.quote(domain)}&type={qtype}"
    try:
        req = Request(url, headers={"Accept": "application/dns-json", "User-Agent": UA})
        with urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        answers = data.get("Answer", []) or []
        return [a["data"] for a in answers if a.get("data")]
    except (URLError, json.JSONDecodeError):
        return []


def dns_reverse(ip: str) -> str | None:
    """PTR lookup for an IP."""
    try:
        return socket.gethostbyaddr(ip)[0]
    except (socket.herror, OSError):
        return None


def _fetch_apis_dns(domain: str, qtype: str = "A") -> list[str]:
    if not _APIS_BASE:
        return []
    url = f"{_APIS_BASE}/api/dns/{urllib.parse.quote(domain)}?type={qtype}"
    try:
        req = Request(url, headers={"User-Agent": UA})
        with urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("answers", [])
    except (URLError, json.JSONDecodeError):
        return []


def dns_all(domain: str) -> DNSResult:
    """Run A, AAAA, MX, TXT, NS lookups for a domain."""
    result = DNSResult(domain=domain, source="neohiro/apis")
    # Try via neohiro/apis
    api_base = _APIS_BASE
    if api_base:
        url = f"{api_base}/api/dns/{urllib.parse.quote(domain)}"
        try:
            req = Request(url, headers={"User-Agent": UA})
            with urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            result.records = data.get("records", {})
            result.source = "neohiro/apis"
            return result
        except (URLError, json.JSONDecodeError):
            pass
    # Fall back: direct lookups
    for qtype in ("A", "AAAA", "MX", "TXT", "NS"):
        records = dns_lookup(domain, qtype)
        if records:
            result.records[qtype] = records
    result.source = "direct"
    return result


# ─── WHOIS / RDAP ───────────────────────────────────────────────────────────

def whois_rdap(domain: str) -> WHOISResult:
    """RDAP lookup — no key required, standard protocol."""
    # RDAP bootstrap: try publicrdap.org
    result = WHOISResult(domain=domain, source="publicrdap.org")
    url = f"https://rdap.publicrdap.org/rdap/rdap64/domain/{urllib.parse.quote(domain)}"
    try:
        req = Request(url, headers={"User-Agent": UA})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (URLError, json.JSONDecodeError):
        result.error = "lookup failed"
        return result

    def _val(key: str) -> str | None:
        v = data.get(key)
        return str(v) if v else None

    result.registrar = _val("registrarName") or _val("registrar")
    result.created = _val("eventsRegistrationDate") or _val("createdDate")
    result.expires = _val("eventsExpirationDate") or _val("expiryDate")
    result.status = _val("status")
    result.nameservers = [n.get("ldhName") or n.get("unicodeName", "") for n in data.get("nameservers") or [] if n]

    # Extract org/country from entities
    for entity in data.get("entities") or []:
        roles = entity.get("roles") or []
        if "registrant" in roles or "admin" in roles or "tech" in roles:
            for post in entity.get("postcodeAddresses") or []:
                result.country = post.get("country")
            for remark in entity.get("remarks") or []:
                desc = (remark.get("description") or [""])[0]
                if not result.org:
                    result.org = desc
    return result


# ─── Source class (for CLI integration) ─────────────────────────────────────

from . import BaseSource, NewsItem, register_source

@register_source
class DNSSource(BaseSource):
    name = "dns"

    def fetch(self) -> list[dict]:
        results: list[dict] = []
        # Default: check own hostname's DNS
        hostname = socket.gethostname()
        r = dns_all(hostname)
        results.append(r.to_dict())
        return results
