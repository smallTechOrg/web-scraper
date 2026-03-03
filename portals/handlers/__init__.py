# portals/handlers/__init__.py
"""
Handler implementations for various portal actions.

This module contains the handler functions for each (source, portal, action_type) combination.
Handlers are registered with the action_registry in the parent portals module.
"""

from typing import Callable
from dataclasses import dataclass


@dataclass
class HandlerRegistration:
    """Represents a handler registration tuple."""
    source: str
    portal: str
    action_type: str
    handler: Callable
    description: str


def get_all_handlers() -> list[tuple]:
    """
    Returns a list of all handler registrations.
    
    Each tuple contains: (source, portal, action_type, handler_func, description)
    """
    handlers = []
    
    # Import and register each handler module
    from portals.handlers import bbmp_handlers
    
    handlers.extend(bbmp_handlers.get_handlers())
    
    return handlers


# Import all handler modules to ensure they register themselves
from portals.handlers import bbmp_handlers
