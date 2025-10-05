from flask import request
import logging

PRIVATE_PREFIXES = ("10.", "172.", "192.168.", "127.", "169.254.")
IPGEOLOCATION_API_KEY = "8b968673a16d49109006c5c40a0b6d84"

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
    """
    Get geolocation data for an IP address using ipgeolocation.io API.
    Returns dict with comprehensive location data or None if lookup fails.
    """
    if _is_private(ip):
        logging.info("Skipping geolocation for private IP: %s", ip)
        return None
    
    try:
        import requests
        url = f"https://api.ipgeolocation.io/ipgeo?apiKey={IPGEOLOCATION_API_KEY}&ip={ip}"
        r = requests.get(url, timeout=5)
        
        if r.status_code == 200:
            d = r.json()
            return {
                "lat": float(d.get("latitude")) if d.get("latitude") else None,
                "lon": float(d.get("longitude")) if d.get("longitude") else None,
                "city": d.get("city"),
                "region": d.get("state_prov"),
                "country": d.get("country_name"),
                "country_code": d.get("country_code2"),
                "continent": d.get("continent_name"),
                "zipcode": d.get("zipcode"),
                "isp": d.get("isp"),
                "organization": d.get("organization"),
                "timezone": d.get("time_zone", {}).get("name"),
                "currency": d.get("currency", {}).get("code"),
            }
        else:
            logging.warning("Geolocation lookup returned %s for %s: %s", r.status_code, ip, r.text)
    except Exception:
        logging.exception("Geolocation lookup failed for %s", ip)
    
    return None