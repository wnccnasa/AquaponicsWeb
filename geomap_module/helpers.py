from flask import request
import logging

PRIVATE_PREFIXES = ("10.", "172.", "192.168.", "127.", "169.254.")

def _is_private(ip: str) -> bool:
    if not ip:
        return True
    ip = ip.strip().lower()
    if ip == "localhost":
        return True
    return any(ip.startswith(p) for p in PRIVATE_PREFIXES)

def get_ip() -> str:
    """
    Prefer headers set by URL Rewrite / proxy, then fall back to REMOTE_ADDR / request.remote_addr.
    """
    hdr = request.headers.get
    for h in ("X-Real-Ip", "X-Real-IP", "X-Forwarded-For", "X-MS-Forwarded-Client-IP"):
        v = hdr(h)
        if v:
            return v.split(",")[0].strip()
    return request.environ.get("REMOTE_ADDR") or request.remote_addr

def get_location(ip: str):
    if _is_private(ip):
        logging.info("Skipping geolocation for private IP: %s", ip)
        return None
    try:
        import requests
        r = requests.get(f"https://ipapi.co/{ip}/json/", timeout=5)
        if r.status_code == 200:
            d = r.json()
            return {
                "lat": d.get("latitude"),
                "lon": d.get("longitude"),
                "city": d.get("city"),
                "region": d.get("region"),
                "country": d.get("country_name"),
            }
        logging.warning("Geolocation lookup returned %s for %s", r.status_code, ip)
    except Exception:
        logging.exception("Geolocation lookup failed for %s", ip)
    return None