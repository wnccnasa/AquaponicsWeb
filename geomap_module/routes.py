from flask import render_template, jsonify, request
from . import geomap_bp  # Import the blueprint
from .models import VisitorLocation
from .helpers import get_ip, get_location
from database import db  # Import db from the shared database module
import logging
from datetime import datetime, timezone, timedelta

# Try to use proper timezone support with DST awareness
try:
    from zoneinfo import ZoneInfo
    MOUNTAIN_TZ = ZoneInfo("America/Denver")
    TIMEZONE_NAME = "Mountain Time (MST/MDT)"
except (ImportError, Exception):
    # Fallback to fixed offset if zoneinfo/tzdata not available
    # Note: This won't handle DST transitions automatically
    MOUNTAIN_TZ = timezone(timedelta(hours=-6))  # MDT offset
    TIMEZONE_NAME = "Mountain Time (UTC-6, no DST)"
    logging.warning("zoneinfo not available, using fixed UTC-6 offset. Install tzdata for DST support.")


def to_mountain_time(utc_dt):
    """
    Convert UTC datetime to Mountain Time (with DST awareness if available).
    Returns formatted string or None.
    """
    if utc_dt is None:
        return None
    try:
        # Ensure datetime is timezone-aware UTC
        if utc_dt.tzinfo is None:
            utc_dt = utc_dt.replace(tzinfo=timezone.utc)
        # Convert to Mountain Time
        mt_dt = utc_dt.astimezone(MOUNTAIN_TZ)
        return mt_dt.strftime('%Y-%m-%d %I:%M:%S %p %Z')
    except Exception as e:
        logging.error(f"Error converting time to Mountain: {e}")
        return str(utc_dt)


@geomap_bp.route("/visitors")
def visitors_map():
    """
    Main visitor map page - shows all visitor locations on an interactive map.
    Converts UTC timestamps to Mountain Time for display.
    """
    try:
        # Get all visitors ordered by last visit
        visitors_query = VisitorLocation.query.order_by(VisitorLocation.last_visit.desc()).all()
        
        # Convert timestamps for each visitor
        visitor_data = []
        for v in visitors_query:
            visitor_data.append({
                'ip': v.ip_address,
                'lat': float(v.lat) if v.lat else 0.0,
                'lon': float(v.lon) if v.lon else 0.0,
                'city': v.city or 'Unknown',
                'region': v.region or '',
                'country': v.country or 'Unknown',
                'visits': v.visit_count or 0,
                'first_visit': to_mountain_time(v.first_visit),
                'last_visit': to_mountain_time(v.last_visit),
                'user_agent': v.user_agent or '',
                'page_visited': v.page_visited or '/',
                'isp': v.isp or '',
                'organization': v.organization or ''
            })
        
        # Get total visitor count
        total_visitors = len(visitor_data)
        
        # Get unique visitor count (should be same as total since IP is unique)
        unique_visitors = total_visitors
        
        return render_template(
            "visitors.html",
            visitors=visitor_data,
            total_visitors=total_visitors,
            unique_visitors=unique_visitors,
            timezone_display=TIMEZONE_NAME
        )
    except Exception as e:
        logging.exception("Error loading visitors page")
        return render_template(
            "visitors.html",
            visitors=[],
            total_visitors=0,
            unique_visitors=0,
            timezone_display=TIMEZONE_NAME,
            error=str(e)
        )


@geomap_bp.route("/api/visitor-locations")
def get_visitor_locations():
    """
    API endpoint that returns all visitor location data as JSON.
    Timestamps are converted from UTC to Mountain Time.
    """
    try:
        # Get all visitor locations from the database, ordered by last visit
        locations = VisitorLocation.query.order_by(VisitorLocation.last_visit.desc()).all()
        
        # Convert to list of dictionaries with Mountain Time timestamps
        locations_list = []
        for loc in locations:
            locations_list.append({
                'ip': loc.ip_address,
                'lat': float(loc.lat) if loc.lat else 0.0,
                'lon': float(loc.lon) if loc.lon else 0.0,
                'city': loc.city or 'Unknown',
                'region': loc.region or '',
                'country': loc.country or 'Unknown',
                'visit_count': loc.visit_count or 0,
                'first_visit': to_mountain_time(loc.first_visit),
                'last_visit': to_mountain_time(loc.last_visit),
                'first_visit_utc': loc.first_visit.isoformat() if loc.first_visit else None,
                'last_visit_utc': loc.last_visit.isoformat() if loc.last_visit else None
            })
        
        return jsonify(locations_list)
    except Exception as e:
        logging.exception("Error fetching visitor locations")
        return jsonify({"error": str(e)}), 500


@geomap_bp.route("/api/visitor-stats")
def get_visitor_stats():
    """
    API endpoint that returns visitor statistics.
    Timestamps are converted from UTC to Mountain Time.
    """
    try:
        unique_visitors = VisitorLocation.query.count()
        
        # Calculate total visits by summing all visit_count values
        from sqlalchemy import func
        total_visits_result = db.session.query(func.sum(VisitorLocation.visit_count)).scalar()
        total_visitors = total_visits_result or 0
        
        # Get recent visitors (last 10) ordered by last visit
        recent_visitors = VisitorLocation.query.order_by(
            VisitorLocation.last_visit.desc()
        ).limit(10).all()
        
        # Get top visitors (most visits)
        top_visitors = VisitorLocation.query.order_by(
            VisitorLocation.visit_count.desc()
        ).limit(10).all()
        
        return jsonify({
            "total_visitors": total_visitors,
            "unique_visitors": unique_visitors,
            "timezone": TIMEZONE_NAME,
            "recent_visitors": [
                {
                    "city": v.city,
                    "region": v.region,
                    "country": v.country,
                    "visit_count": v.visit_count,
                    "first_visit": to_mountain_time(v.first_visit),
                    "last_visit": to_mountain_time(v.last_visit)
                }
                for v in recent_visitors
            ],
            "top_visitors": [
                {
                    "city": v.city,
                    "region": v.region,
                    "country": v.country,
                    "visit_count": v.visit_count
                }
                for v in top_visitors
            ]
        })
    except Exception as e:
        logging.exception("Error fetching visitor stats")
        return jsonify({"error": str(e)}), 500
