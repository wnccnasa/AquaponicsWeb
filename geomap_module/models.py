from database import db  # Import the shared db instance
from datetime import datetime, timezone


class VisitorLocation(db.Model):
    """Model to store visitor IP location data."""
    __tablename__ = 'visitor_locations'
    
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), nullable=False, unique=True, index=True)  # IPv6 can be up to 45 chars
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    city = db.Column(db.String(100))
    region = db.Column(db.String(100))
    country = db.Column(db.String(100))
    visit_count = db.Column(db.Integer, default=1, nullable=False)  # Counter for number of visits
    first_visit = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)  # First visit timestamp
    last_visit = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)  # Most recent visit timestamp
    user_agent = db.Column(db.String(255))
    page_visited = db.Column(db.String(255))  # Last page visited

    def __init__(self, ip_address, lat, lon, city=None, region=None, country=None, user_agent=None, page_visited=None):
        self.ip_address = ip_address
        self.lat = lat
        self.lon = lon
        self.city = city
        self.region = region
        self.country = country
        self.visit_count = 1
        self.first_visit = datetime.now(timezone.utc)
        self.last_visit = datetime.now(timezone.utc)
        self.user_agent = user_agent
        self.page_visited = page_visited

    def increment_visit(self, page_visited=None, user_agent=None):
        """Increment the visit counter and update last visit timestamp."""
        self.visit_count += 1
        self.last_visit = datetime.now(timezone.utc)
        if page_visited:
            self.page_visited = page_visited
        if user_agent:
            self.user_agent = user_agent

    def to_dict(self):
        """Convert model to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'ip_address': self.ip_address,
            'lat': self.lat,
            'lon': self.lon,
            'city': self.city,
            'region': self.region,
            'country': self.country,
            'visit_count': self.visit_count,
            'first_visit': self.first_visit.isoformat() if self.first_visit else None,
            'last_visit': self.last_visit.isoformat() if self.last_visit else None,
            'user_agent': self.user_agent,
            'page_visited': self.page_visited
        }
