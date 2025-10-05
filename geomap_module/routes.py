from flask import render_template, jsonify, request
from . import geomap_bp  # Import the blueprint
from .models import VisitorLocation
from .helpers import get_ip, get_location
from database import db  # Import db from the shared database module
import logging


@geomap_bp.route("/visitors")
def visitors_map():
    """
    Main visitor map page - shows all visitor locations on an interactive map.
    """
    # Get total visitor count
    total_visitors = VisitorLocation.query.count()
    
    # Get unique visitor count (unique IPs)
    unique_visitors = db.session.query(VisitorLocation.ip_address).distinct().count()
    
    return render_template(
        "visitors.html",
        total_visitors=total_visitors,
        unique_visitors=unique_visitors
    )


@geomap_bp.route("/api/visitor-locations")
def get_visitor_locations():
    """
    API endpoint that returns all visitor location data as JSON.
    Used by the map to plot visitor locations.
    """
    try:
        # Get all visitor locations from the database
        locations = VisitorLocation.query.order_by(VisitorLocation.timestamp.desc()).all()
        
        # Convert to list of dictionaries
        locations_list = [loc.to_dict() for loc in locations]
        
        return jsonify(locations_list)
    except Exception as e:
        logging.error(f"Error fetching visitor locations: {e}")
        return jsonify({"error": "Failed to fetch visitor locations"}), 500


@geomap_bp.route("/api/visitor-stats")
def get_visitor_stats():
    """
    API endpoint that returns visitor statistics.
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
            "recent_visitors": [
                {
                    "city": v.city,
                    "region": v.region,
                    "country": v.country,
                    "visit_count": v.visit_count,
                    "first_visit": v.first_visit.isoformat() if v.first_visit else None,
                    "last_visit": v.last_visit.isoformat() if v.last_visit else None
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
        logging.error(f"Error fetching visitor stats: {e}")
        return jsonify({"error": "Failed to fetch visitor stats"}), 500
