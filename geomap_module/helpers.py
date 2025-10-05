from flask import request
import requests
import logging

def get_ip():
    """
    Gets the user's real IP address from behind a proxy or load balancer.
    Handles X-Forwarded-For header which is commonly used by IIS and reverse proxies.
    """
    # Check for X-Forwarded-For header (used by proxies/load balancers)
    if request.headers.getlist("X-Forwarded-For"):
        # Get the first IP in the chain (the original client IP)
        ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
    else:
        # Fall back to direct connection IP
        ip = request.remote_addr or "0.0.0.0"
    return ip

def get_location(ip_address):
    """
    Gets geolocation data from an IP address using the ipinfo.io API.
    Returns a dictionary with lat, lon, city, region, and country information.
    """
    # Handle localhost and private IP addresses
    if ip_address in ["127.0.0.1", "::1", "0.0.0.0"] or ip_address.startswith("192.168.") or ip_address.startswith("10."):
        # Default location for local/private IPs (WNCC location in Nebraska)
        return {
            "lat": 41.4925,
            "lon": -99.9018,
            "city": "Broken Bow",
            "region": "Nebraska",
            "country": "United States"
        }
    
    try:
        # Call ipinfo.io API for geolocation data
        # Note: Free tier allows 50,000 requests per month
        response = requests.get(f'https://ipinfo.io/{ip_address}/json', timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # Extract location data if available
        if 'loc' in data:
            lat, lon = data['loc'].split(',')
            return {
                "lat": float(lat),
                "lon": float(lon),
                "city": data.get('city', 'Unknown'),
                "region": data.get('region', 'Unknown'),
                "country": data.get('country', 'Unknown')
            }
        else:
            logging.warning(f"No location data found for IP {ip_address}")
            
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching location for IP {ip_address}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error getting location for IP {ip_address}: {e}")
    
    return None