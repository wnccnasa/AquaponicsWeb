from flask import request
import logging
from functools import lru_cache
import os

# Load ipgeolocation API key from file or environment (do NOT hardcode here)
def _load_api_key():
    # 1) environment variable
    key = os.environ.get("GEOIP_LICENSE")
    if key and key.strip():
        return key.strip()
    # 2) file at project root: geoip_license.txt
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    license_path = os.path.join(root, "geoip_license.txt")
    try:
        if os.path.exists(license_path):
            with open(license_path, "r", encoding="utf-8") as f:
                k = f.read().strip()
                if k:
                    return k
    except Exception:
        logging.exception("Failed to read geoip_license.txt")
    return None

IPGEOLOCATION_API_KEY = _load_api_key()
GEOIP_DB_PATH = r"C:\inetpub\aquaponics\geoip\GeoLite2-City.mmdb"
PRIVATE_PREFIXES = ("10.", "172.", "192.168.", "127.", "169.254.")

def _is_private(ip: str) -> bool:
    if not ip:
        return True
    ip = ip.strip().lower()
    if ip == "localhost":
        return True
    return any(ip.startswith(p) for p in PRIVATE_PREFIXES)

def get_ip() -> str:
    hdr = request.headers.get
    for h in ("X-Real-Ip", "X-Real-IP", "X-Forwarded-For", "X-MS-Forwarded-Client-IP", "X-Original-Remote-Addr"):
        v = hdr(h)
        if v:
            return v.split(",")[0].strip()
    return request.environ.get("REMOTE_ADDR") or request.remote_addr

@lru_cache(maxsize=10000)
def _geoip2_lookup_local(ip: str):
    """Try local GeoLite2 database via geoip2 (fast, first priority)."""
    try:
        import geoip2.database
        reader = geoip2.database.Reader(GEOIP_DB_PATH)
        rec = reader.city(ip)
        reader.close()
        return {
            "lat": rec.location.latitude,
            "lon": rec.location.longitude,
            "city": rec.city.name,
            "region": rec.subdivisions.most_specific.name,
            "country": rec.country.name,
            "country_code": rec.country.iso_code,
            "continent": getattr(rec.continent, "name", None),
            "zipcode": rec.postal.code if hasattr(rec, "postal") else None,
            "isp": None,
            "organization": None,
            "timezone": getattr(rec.location, "time_zone", None),
            "currency": None,
        }
    except Exception:
        logging.debug("Local GeoLite2 lookup not available or failed for %s", ip, exc_info=False)
        return None

def _norm(v):
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None

@lru_cache(maxsize=10000)
def get_location(ip: str):
    """
    Resolve IP -> geolocation dict.
    Priority:
      1) Local GeoLite2 DB (geoip2)
      2) ipgeolocation.io (provided API key)
      3) ipapi.co fallback
      4) reverse DNS minimal info
    Returns dict or None.
    """
    if _is_private(ip):
        logging.info("Skipping geolocation for private IP: %s", ip)
        return None

    # 1) local GeoLite2
    try:
        local = _geoip2_lookup_local(ip)
        if local:
            return {k: _norm(v) if k not in ("lat","lon") else (float(v) if v is not None else None)
                    for k,v in local.items()}
    except Exception:
        logging.exception("Local GeoLite2 lookup failed for %s", ip)

    # 2) ipgeolocation.io
    try:
        if IPGEOLOCATION_API_KEY:
            import requests
            url = f"https://api.ipgeolocation.io/ipgeo?apiKey={IPGEOLOCATION_API_KEY}&ip={ip}"
            r = requests.get(url, timeout=5)
            if r.ok:
                d = r.json()
                return {
                    "lat": float(d.get("latitude")) if d.get("latitude") else None,
                    "lon": float(d.get("longitude")) if d.get("longitude") else None,
                    "city": _norm(d.get("city")),
                    "region": _norm(d.get("state_prov")),
                    "country": _norm(d.get("country_name")),
                    "country_code": _norm(d.get("country_code2")),
                    "continent": _norm(d.get("continent_name")),
                    "zipcode": _norm(d.get("zipcode")),
                    "isp": _norm(d.get("isp")),
                    "organization": _norm(d.get("organization")),
                    "timezone": (d.get("time_zone") or {}).get("name") if isinstance(d.get("time_zone"), dict) else _norm(d.get("time_zone")),
                    "currency": (d.get("currency") or {}).get("code") if isinstance(d.get("currency"), dict) else None,
                }
            else:
                logging.warning("ipgeolocation lookup failed %s for %s: %s", r.status_code, ip, r.text)
        else:
            logging.debug("IP geolocation API key not available; skipping ipgeolocation.io lookup")
    except Exception:
        logging.exception("ipgeolocation lookup error for %s", ip)

    # 3) ipapi.co fallback
    try:
        import requests
        r = requests.get(f"https://ipapi.co/{ip}/json/", timeout=4)
        if r.ok:
            d = r.json()
            return {
                "lat": d.get("latitude") or d.get("lat"),
                "lon": d.get("longitude") or d.get("lon"),
                "city": _norm(d.get("city")),
                "region": _norm(d.get("region")),
                "country": _norm(d.get("country_name") or d.get("country")),
                "country_code": _norm(d.get("country_code")),
                "timezone": _norm(d.get("timezone")),
                "isp": _norm(d.get("org") or d.get("asn")) or None,
            }
    except Exception:
        logging.exception("ipapi lookup failed for %s", ip)

    # 4) reverse DNS minimal fallback
    try:
        import socket
        try:
            name = socket.gethostbyaddr(ip)[0]
        except Exception:
            name = None
        return {
            "lat": None,
            "lon": None,
            "city": None,
            "region": None,
            "country": None,
            "country_code": None,
            "continent": None,
            "zipcode": None,
            "isp": None,
            "organization": _norm(name),
            "timezone": None,
            "currency": None,
        }
    except Exception:
        logging.exception("reverse DNS fallback failed for %s", ip)
        return None