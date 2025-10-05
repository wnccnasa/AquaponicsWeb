#!/usr/bin/env python3
"""
Flask web application that shows two live MJPEG camera streams:
 - Fish Tank (camera 0)
 - Plant Bed (camera 2 mapped as /stream1.mjpg on the Pi side)

Designed with clear comments for learners.
This version keeps:
 - Clean structure
 - Rotating log files (no noisy debug routes)
 - Simple relay caching for efficiency

Does NOT include extra debug endpoints or complex UI logic.
"""

from flask import Flask, render_template, request, url_for, Response
from flask_sqlalchemy import SQLAlchemy
import os
import logging
import logging.handlers
import threading
import time
from typing import Dict
from datetime import datetime, timedelta, timezone

# Simple Mountain timezone (MDT = UTC-6, MST = UTC-7)
# Use MDT for now - adjust manually for winter if needed
MOUNTAIN_TZ = timezone(timedelta(hours=-6))  # Mountain Daylight Time

# Local modules that handle pulling frames from upstream cameras
from cached_relay import CachedMediaRelay

# Database and visitor tracking
from database import db  # <-- db is already created in database.py
from geomap_module import geomap_bp
from geomap_module.models import VisitorLocation
from geomap_module.helpers import get_ip, get_location

# ---------------------------------------------------------------------------
# LOGGING SETUP
# ---------------------------------------------------------------------------
# We log to files so we can review what happened later (errors, starts, etc.)
# LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
# os.makedirs(LOG_DIR, exist_ok=True)
#
# LOG_FILE = os.path.join(LOG_DIR, "main_app")
#
# handler = logging.handlers.TimedRotatingFileHandler(
#     LOG_FILE, when="midnight", interval=1, backupCount=7, encoding="utf-8"
# )
# handler.suffix = "%Y-%m-%d.log"
# handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))

# Change logging file name to use explicit "main_app.log" base and cleaner rotated suffix
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "main_app.log")

handler = logging.handlers.TimedRotatingFileHandler(
    LOG_FILE, when="midnight", interval=1, backupCount=7, encoding="utf-8"
)
# rotated files will be: main_app.log.2025-09-27 (no duplicate .log)
handler.suffix = "%Y-%m-%d"
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))

# Root logger (shared across modules)
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)
logging.info("Application start")

# ---------------------------------------------------------------------------
# FLASK APP SETUP
# ---------------------------------------------------------------------------
# static_url_path lets static files be served under /aquaponics/static
app = Flask(__name__, static_url_path="/aquaponics/static")

# APPLICATION_ROOT allows IIS or reverse proxy to mount at /aquaponics
app.config["APPLICATION_ROOT"] = os.environ.get("APPL_VIRTUAL_PATH", "/")

# ---------------------------------------------------------------------------
# DATABASE SETUP (moved to static/db directory)
# ---------------------------------------------------------------------------
# Use absolute path instead of app.static_folder to avoid initialization order issues
DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "db")
os.makedirs(DB_DIR, exist_ok=True)
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(DB_DIR, 'visitors.db')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the database with this app (don't create a new SQLAlchemy instance)
db.init_app(app)

# Register the geomap blueprint for visitor tracking
app.register_blueprint(geomap_bp, url_prefix="/aquaponics")

# Create database tables if they don't exist
with app.app_context():
    db.create_all()
    logging.info("Database tables created/verified")

# ---------------------------------------------------------------------------
# VISITOR TRACKING MIDDLEWARE
# ---------------------------------------------------------------------------
# TEMPORARILY DISABLED FOR DEBUGGING
# @app.before_request
# def track_visitor():
#     """Visitor tracking temporarily disabled"""
#     pass

@app.before_request
def track_visitor():
    """
    Middleware to track visitor IP locations on each request.
    Runs before every request to log visitor information.
    Increments visit counter for returning visitors.
    """
    # Skip tracking for static files, API endpoints, and health checks
    if (request.path.startswith('/aquaponics/static/') or 
        request.path.startswith('/aquaponics/api/') or
        request.path in ['/aquaponics/health', '/aquaponics/server_info', '/aquaponics/waitress_info'] or
        request.path == '/aquaponics/stream_proxy'):
        return
    
    # Use timezone-aware conversion to Mountain Time
    now_utc = datetime.now(timezone.utc)
    now_mdt = now_utc.astimezone(MOUNTAIN_TZ)
    logging.info(f"[{now_mdt.strftime('%Y-%m-%d %H:%M:%S %Z')}] Visitor tracking triggered for path: {request.path}")
    
    try:
        # Get visitor's IP address
        ip = get_ip()
        logging.info(f"Detected IP: {ip}")
        
        # Check if we've already tracked this IP
        existing_visitor = VisitorLocation.query.filter_by(ip_address=ip).first()
        
        if existing_visitor:
            # Check if we should update (cooldown: 1 hour)
            # Ensure last_visit is timezone-aware for comparison
            last_visit = existing_visitor.last_visit
            if last_visit and last_visit.tzinfo is None:
                last_visit = last_visit.replace(tzinfo=timezone.utc)
            
            recent_cutoff = now_utc - timedelta(hours=1)
            if last_visit and last_visit > recent_cutoff:
                # Already tracked recently, skip
                logging.info(f"Visitor {ip} tracked recently, skipping")
                return
            
            # Update existing visitor: increment counter and update timestamps
            existing_visitor.increment_visit(
                page_visited=request.path,
                user_agent=request.headers.get('User-Agent', '')[:255]
            )
            db.session.commit()
            logging.info(f"Updated visitor from {ip} - Visit #{existing_visitor.visit_count}")
        else:
            # New visitor - get location data
            logging.info(f"New visitor {ip}, fetching location data...")
            location_data = get_location(ip)
            logging.info(f"Location data received: {location_data}")
            
            if location_data:
                # Create new visitor location record
                visitor = VisitorLocation(
                    ip_address=ip,
                    lat=location_data["lat"],
                    lon=location_data["lon"],
                    city=location_data.get("city"),
                    region=location_data.get("region"),
                    country=location_data.get("country"),
                    user_agent=request.headers.get('User-Agent', '')[:255],
                    page_visited=request.path
                )
                
                db.session.add(visitor)
                db.session.commit()
                logging.info(f"Successfully tracked new visitor from {ip} - {location_data.get('city', 'Unknown')}, {location_data.get('region', '')}")
            else:
                logging.warning(f"No location data returned for IP: {ip}")
    except Exception as e:
        # Don't let visitor tracking errors break the application
        logging.error(f"Error tracking visitor: {e}", exc_info=True)
        # Rollback any failed database transaction
        db.session.rollback()

# ---------------------------------------------------------------------------
# CAMERA CONFIGURATION
# ---------------------------------------------------------------------------
# These values describe where the upstream Raspberry Pi (or server) streams live.
# If the Pi's IP changes on the network, update DEFAULT_STREAM_HOST.
DEFAULT_STREAM_HOST = "10.0.0.2"
DEFAULT_STREAM_PORT = 8000

# Paths exposed by the Raspberry Pi streaming script:
#   /stream0.mjpg  -> physical camera index 0 (fish)
#   /stream1.mjpg  -> physical camera index 2 (plants) mapped by your Pi script
DEFAULT_STREAM_PATH_0 = "/stream0.mjpg"  # Fish tank
DEFAULT_STREAM_PATH_1 = "/stream1.mjpg"  # Plant bed

# ---------------------------------------------------------------------------
# RELAY / STREAMING TUNING
# ---------------------------------------------------------------------------
# The relay creates ONE upstream connection per unique camera URL and shares
# frames with all connected viewers. This saves bandwidth and CPU.
WIRELESS_CACHE_DURATION = 15.0   # Seconds of frames to retain (smoothing hiccups)
WIRELESS_SERVE_DELAY = 2.0       # Delay used by CachedMediaRelay to stabilize order
WARMUP_TIMEOUT = 15              # Seconds to wait for first frame before giving up
MAX_CONSECUTIVE_TIMEOUTS = 10    # If client sees this many empty waits, disconnect
QUEUE_TIMEOUT = 15               # Seconds each client waits for a frame before retry

# Dictionary that holds active relay objects keyed by the full upstream URL
_media_relays: Dict[str, CachedMediaRelay] = {}
_media_lock = threading.Lock()

def get_media_relay(stream_url: str) -> CachedMediaRelay:
    with _media_lock:
        relay = _media_relays.get(stream_url)
        if relay is None:
            relay = CachedMediaRelay(
                stream_url,
                cache_duration=WIRELESS_CACHE_DURATION,
                serve_delay=WIRELESS_SERVE_DELAY,
            )
            relay.start()
            _media_relays[stream_url] = relay
            logging.info(f"[CachedRelayFactory] Created {stream_url}")
        return relay

# ---------------------------------------------------------------------------
# ROUTES: WEB PAGES
# ---------------------------------------------------------------------------
@app.route("/aquaponics", methods=["GET", "POST"])
def index():
    """
    Main page. Builds two proxy URLs (one per camera) and passes them
    to the template. A timestamp param helps defeat browser caching.
    """
    host = DEFAULT_STREAM_HOST
    port = DEFAULT_STREAM_PORT

    # Build fish camera proxy URL (still goes through this Flask app)
    fish_stream_url = url_for(
        "stream_proxy",
        host=host,
        port=port,
        path=DEFAULT_STREAM_PATH_0
    )

    # Build plant camera proxy URL
    plants_stream_url = url_for(
        "stream_proxy",
        host=host,
        port=port,
        path=DEFAULT_STREAM_PATH_1
    )

    return render_template(
        "index.html",
        fish_stream_url=fish_stream_url,
        plants_stream_url=plants_stream_url,
        host=host,
        port=port,
        timestamp=int(time.time())  # basic cache-buster
    )

# Champions page route
@app.route("/aquaponics/champions")
def champions():
    """Page recognizing Aquaponics Champions."""
    return render_template("champions.html")

@app.route("/aquaponics/about")
def about():
    """Static About page."""
    return render_template("about.html")

@app.route("/aquaponics/contact")
def contact():
    """Static Contact page."""
    return render_template("contact.html")

@app.route("/aquaponics/sensors")
def sensors():
    """Sensor dashboard page (template only here)."""
    return render_template("sensors.html")

@app.route("/aquaponics/photos")
def photos():
    """Photo gallery page."""
    return render_template("photos.html")

@app.route("/aquaponics/stats")
def stats_page():
    """HTML page that displays waitress/server streaming statistics."""
    return render_template("waitress_stats.html")

# ---------------------------------------------------------------------------
# STREAM PROXY ENDPOINT
# ---------------------------------------------------------------------------
@app.route("/aquaponics/stream_proxy")
def stream_proxy():
    """
    Proxies an upstream MJPEG stream through this server.
    Steps:
      1. Read query parameters (host, port, path).
      2. Construct full upstream URL (e.g. http://172.16.1.200:8000/stream0.mjpg).
      3. Get or create a relay for that URL.
      4. Attach this browser as a client (queue).
      5. Yield frame chunks to the browser in a multipart MJPEG response.
    The browser <img> tag renders the stream continuously.
    """
    # Get parameters or fall back to defaults
    host = request.args.get("host", DEFAULT_STREAM_HOST)
    port = int(request.args.get("port", DEFAULT_STREAM_PORT))
    path = request.args.get("path", DEFAULT_STREAM_PATH_0)

    # Build complete upstream URL
    stream_url = f"http://{host}:{port}{path}"

    relay = get_media_relay(stream_url)
    client_queue = relay.add_client()

    def generate():
        waited = 0.0
        # Wait for first frame
        while relay.last_frame is None and waited < WARMUP_TIMEOUT and relay.running:
            time.sleep(0.2)
            waited += 0.2
        if relay.last_frame is None:
            relay.remove_client(client_queue)
            return
        consecutive_timeouts = 0
        try:
            while relay.running:
                try:
                    chunk = client_queue.get(timeout=QUEUE_TIMEOUT)
                    consecutive_timeouts = 0
                    if chunk is None:  # Shutdown signal
                        break
                    yield chunk
                except Exception:  # Queue timeout
                    consecutive_timeouts += 1
                    if consecutive_timeouts >= MAX_CONSECUTIVE_TIMEOUTS or not relay.running:
                        break
        finally:
            relay.remove_client(client_queue)

    return Response(
        generate(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )

@app.route("/aquaponics/health")
def health():
    """
    Simple health check used by monitoring or load balancers.
    Returns JSON if the app is alive.
    """
    return {"status": "ok"}

@app.route("/aquaponics/server_info")
def server_info():
    import threading
    return {
        "server": request.environ.get("SERVER_SOFTWARE", "unknown"),
        "active_threads": len(threading.enumerate()),
        "media_relays": list(getattr(globals(), "_media_relays", {}).keys())
    }

@app.route("/aquaponics/waitress_info")
def waitress_info():
    """
    Runtime diagnostics focused on Waitress + streaming load.
    Gives a quick view of thread usage and camera client counts.
    """
    import threading, platform, sys, time
    all_threads = threading.enumerate()
    thread_names = [t.name for t in all_threads]
    waitress_threads = [n for n in thread_names if "waitress" in n.lower()]
    relay_stats = {}
    with _media_lock:
        for url, relay in _media_relays.items():
            with relay.lock:
                relay_stats[url] = {
                    "clients": len(relay.clients),
                    "has_frame": relay.last_frame is not None,
                    "running": relay.running,
                }

    return {
        "server_software": request.environ.get("SERVER_SOFTWARE", "unknown"),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "utc_epoch": int(time.time()),
        "threads_total": len(all_threads),
        "threads_waitress": len(waitress_threads),
        "waitress_thread_names_sample": waitress_threads[:10],
        "threads_other": len(all_threads) - len(waitress_threads),
        "relays": relay_stats
    }

@app.route("/aquaponics/debug/visitors")
def debug_visitors():
    """Debug endpoint to check visitor data (timestamps in Mountain Time)."""
    try:
        visitors = VisitorLocation.query.order_by(VisitorLocation.first_visit.desc()).limit(20).all()
        
        def to_mountain(utc_dt):
            if utc_dt is None:
                return None
            # Handle both naive and timezone-aware datetimes
            if utc_dt.tzinfo is None:
                utc_dt = utc_dt.replace(tzinfo=timezone.utc)
            return utc_dt.astimezone(MOUNTAIN_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')
        
        return {
            "total_count": VisitorLocation.query.count(),
            "timezone": "America/Denver (Mountain Time with DST)",
            "recent_visitors": [
                {
                    "ip": v.ip_address,
                    "city": v.city,
                    "region": v.region,
                    "country": v.country,
                    "lat": v.lat,
                    "lon": v.lon,
                    "visits": v.visit_count,
                    "last_visit": to_mountain(v.last_visit),
                    "first_visit": to_mountain(v.first_visit)
                }
                for v in visitors
            ]
        }
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}, 500

@app.route("/aquaponics/debug/request_info")
def debug_request_info():
    """Return headers and environ to help verify forwarded IPs under IIS."""
    from geomap_module.helpers import get_ip
    return {
        "detected_ip": get_ip(),
        "remote_addr": request.remote_addr,
        "environ_remote_addr": request.environ.get("REMOTE_ADDR"),
        "headers": {k: v for k, v in request.headers.items()},
        "x_forwarded_for": request.headers.get("X-Forwarded-For"),
        "x_real_ip": request.headers.get("X-Real-IP"),
    }

# ---------------------------------------------------------------------------
# TEMPLATE CONTEXT
# ---------------------------------------------------------------------------
@app.context_processor
def inject_urls():
    """
    Makes app_root available in all templates if needed for building links.
    """
    return dict(app_root=app.config["APPLICATION_ROOT"])

# ---------------------------------------------------------------------------
# CLEANUP LOGIC
# ---------------------------------------------------------------------------
def cleanup_relays():
    """
    Called at shutdown to stop all relay threads cleanly.
    Prevents orphan background threads after server exit.
    """
    with _media_lock:
        for relay in _media_relays.values():
            relay.stop()
        _media_relays.clear()
    logging.info("Cached relays cleaned up")

# ---------------------------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import atexit
    atexit.register(cleanup_relays)
    print("Development mode ONLY (use waitress_app.py in production).")
    # DO NOT use debug=True in production behind IIS
    app.run(host="127.0.0.1", port=5000, debug=False)
