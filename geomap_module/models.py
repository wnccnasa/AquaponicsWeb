from database import db  # Import the shared db instance
from datetime import datetime, timezone


class VisitorLocation(db.Model):
    """Model to store visitor IP location data."""
    __tablename__ = 'visitor_location'
    
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), unique=True, nullable=False)
    lat = db.Column(db.Float, nullable=False, default=0.0)
    lon = db.Column(db.Float, nullable=False, default=0.0)
    city = db.Column(db.String(100))
    region = db.Column(db.String(100))
    country = db.Column(db.String(100))
    
    # New fields from ipgeolocation.io
    country_code = db.Column(db.String(10))
    continent = db.Column(db.String(50))
    zipcode = db.Column(db.String(20))
    isp = db.Column(db.String(200))
    organization = db.Column(db.String(200))
    timezone = db.Column(db.String(50))
    currency = db.Column(db.String(10))
    
    visit_count = db.Column(db.Integer, default=1)
    first_visit = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_visit = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    user_agent = db.Column(db.String(255))
    page_visited = db.Column(db.String(255))

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

    def __repr__(self):
        return f'<VisitorLocation {self.ip_address} from {self.city}, {self.country}>'
