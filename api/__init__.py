from .bbmpcomplaint import complaint_bp as complaint_bp
from .bbmp_complaint_report import complaint_report_bp as complaint_report_bp
from .health import health_bp as health_bp
from .bbmplogin import login_bp as login_bp
from .web_scrap import scrape_bp as scrape_bp

__all__ = ["complaint_bp", "complaint_report_bp", "health_bp", "login_bp", "scrape_bp"]