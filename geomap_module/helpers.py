from flask import request
import logging

def get_ip():
    """
    Get the visitor's real IP address.
    Checks X-Forwarded-For header first (for reverse proxy setups like IIS).
    """
    # Check X-Forwarded-For header (IIS/reverse proxy)
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        return ip
    
    # Check X-Real-IP header
    if request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP').strip()
    
    # Fallback to direct connection IP
    return request.remote_addr

def get_location(ip):
    """
    Get geolocation data for an IP address.
    Returns None for localhost/private IPs or on error.
    """
    # Skip localhost/private IPs
    if ip in ['127.0.0.1', 'localhost'] or ip.startswith('192.168.') or ip.startswith('10.') or ip.startswith('172.'):
        logging.info(f"Skipping geolocation for private IP: {ip}")
        return None
    
    try:
        import requests
        response = requests.get(f'https://ipapi.co/{ip}/json/', timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                "lat": data.get("latitude"),
                "lon": data.get("longitude"),
                "city": data.get("city"),
                "region": data.get("region"),
                "country": data.get("country_name")
            }
    except Exception as e:
        logging.error(f"Error fetching location for {ip}: {e}")
    
    return None