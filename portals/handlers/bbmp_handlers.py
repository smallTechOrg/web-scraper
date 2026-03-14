# portals/handlers/bbmp_handlers.py
"""
BBMP/SmartOne Bangalore portal handlers.

This module contains the handler implementations for the BBMP (Bruhat Bengaluru Mahanagara Palike)
complaint portal (SmartOne BLR).
"""

from typing import Callable
from dataclasses import dataclass


# Store handler registrations
_handler_registrations: list[tuple] = []


def register_handler(source: str, portal: str, action_type: str, description: str = ""):
    """
    Decorator to register a handler function.
    
    Args:
        source: The source identifier (e.g., "GOV_ISSUE_PORTAL")
        portal: The portal identifier (e.g., "SMARTONEBLR")
        action_type: The action type (e.g., "TRACK_ISSUE", "REPORT_ISSUE")
        description: Optional description of what the handler does
    """
    def decorator(func: Callable):
        _handler_registrations.append((
            source, portal, action_type, func, description
        ))
        return func
    return decorator


def get_handlers() -> list[tuple]:
    """Returns all registered handler tuples."""
    return _handler_registrations.copy()


# Import portal service functions
from portals.complaint_scraper import fetch_complaint_status
from portals.bbmp_complaint import raise_complaint
from portals.events import fetch_events

# ----------------------------
# TRACK ISSUE HANDLER
# ----------------------------
@register_handler(
    source="GOV_ISSUE_PORTAL",
    portal="SMARTONEBLR",
    action_type="TRACK_ISSUE",
    description="Track complaint status by tracking ID"
)
def handle_track_issue(action_data: dict, context: dict) -> tuple[bool, dict]:
    """
    Handle track issue action - fetch complaint status by tracking ID.
    
    Args:
        action_data: Contains tracking_id
        context: Full request context (not used for track)
        
    Returns:
        tuple[bool, dict]: (success, result_dict)
        - On success: (True, {"data": {"status": ..., "meta_data": {...}}})
        - On failure: (False, {"error": error_message})
    """
    import re
    
    tracking_id = action_data.get("tracking_id")
    
    if not tracking_id:
        return False, {"error": "Missing tracking_id in action_data"}
    
    result = fetch_complaint_status(tracking_id)
    
    if not result.get("success", False):
        return False, {"error": result.get("error", "Failed to fetch complaint status")}
    
      
    # Extract meta_data from staff_details
    staff_details = result.get("staff_details", {})

    # Map complaint status to a standardized status
    status = staff_details["Grievance Status"]
    
    # Map staff fields
    meta_data = {}

    meta_data["remarks"] = staff_details["Staff Remarks"]
    
    # Extract staff name - look for common field names
    staff_name_fields = ["Staff Name", "Assigned To", "Handler", "Assigned Officer"]
    for field in staff_name_fields:
        if field in staff_details and staff_details[field]:
            meta_data["staff_name"] = staff_details[field]
            break

    meta_data["mobile_number"] = staff_details["Contact Details"]
    
    return True, {
        "data": {
            "status": status,
            "meta_data": meta_data
        }
    }


# ----------------------------
# REPORT ISSUE HANDLER
# ----------------------------
@register_handler(
    source="GOV_ISSUE_PORTAL",
    portal="SMARTONEBLR",
    action_type="REPORT_ISSUE",
    description="Report/submit a new complaint"
)
def handle_report_issue(action_data: dict, context: dict) -> tuple[bool, dict]:
    """
    Handle report issue action - submit a new complaint.
    
    Args:
        action_data: Contains category, sub_category, description, media_url, latitude, longitude
        context: Contains auth info (username, password)
        
    Returns:
        tuple[bool, dict]: (success, result_dict)
        - On success: (True, {"data": {"tracking_id": ...}})
        - On failure: (False, {"error": error_message})
    """
    # Get authentication credentials from context
    auth = context.get("auth", {})
    mobile = auth.get("username")
    password = auth.get("password")
    
    success, result = raise_complaint(
        category=action_data.get("category"),
        subcategory=action_data.get("sub_category"),
        description=action_data.get("description"),
        image_path=action_data.get("media_url"),
        latitude=action_data.get("latitude"),
        longitude=action_data.get("longitude"),
        mobile=mobile,
        password=password
    )
    
    if success:
        return True, {
            "data": {
                "tracking_id": str(result["complaint_id"])
            }
        }
    
    error_message = result if isinstance(result, str) else result.get("error", "Failed to raise complaint")
    return False, {"error": error_message}

@register_handler(
    source="EVENT_PORTAL",
    portal="TEAMEVEREST",
    action_type="FETCH_EVENTS",
    description="Fetch all in-person events from TeamEverest portal"
)
def handle_fetch_events(action_data: dict, context: dict) -> tuple[bool, dict]:
    category_filter = action_data.get("category_filter", "")
    event_filter = action_data.get("event_filter", "")
    result = fetch_events(category_filter=category_filter, event_filter=event_filter)
    if "error" in result:
        return False, {"error": result["error"]}
    return True, {"data": result}
 
