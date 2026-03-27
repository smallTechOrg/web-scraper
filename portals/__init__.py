# portals/__init__.py
"""
Portal action handler registry.

This module provides a registry pattern for mapping source + portal + action_type
combinations to their respective handler functions. This eliminates the need for
if-else chains as new portals and actions are added.
"""

from typing import Callable, Optional
from dataclasses import dataclass


@dataclass
class ActionHandler:
    """Represents a registered action handler."""
    handler: Callable
    description: str


class ActionHandlerRegistry:
    """
    Registry for mapping (source, portal, action_type) to handler functions.
    
    Usage:
        registry = ActionHandlerRegistry()
        
        @registry.register(source="GOV_ISSUE_PORTAL", portal="SMARTONEBLR", action_type="TRACK_ISSUE")
        def track_issue_handler(action_data, context):
            # handle track issue
            pass
            
        # Later, dispatch:
        result = registry.dispatch(source, portal, action_type, action_data, context)
    """
    
    def __init__(self):
        self._handlers: dict[str, ActionHandler] = {}
    
    def _make_key(self, source: str, portal: str, action_type: str) -> str:
        """Create a unique key for the source + portal + action_type combination."""
        return f"{source}:{portal}:{action_type}"
    
    def register(self, source: str, portal: str, action_type: str, description: str = ""):
        """
        Decorator to register a handler for a specific source + portal + action_type.
        
        Args:
            source: The source identifier (e.g., "GOV_ISSUE_PORTAL")
            portal: The portal identifier (e.g., "SMARTONEBLR")
            action_type: The action type (e.g., "TRACK_ISSUE", "REPORT_ISSUE")
            description: Optional description of what the handler does
        """
        def decorator(func: Callable):
            key = self._make_key(source, portal, action_type)
            self._handlers[key] = ActionHandler(handler=func, description=description)
            return func
        return decorator
    
    def dispatch(
        self, 
        source: str, 
        portal: str, 
        action_type: str, 
        action_data: dict, 
        context: dict
    ) -> tuple[bool, dict]:
        """
        Dispatch to the appropriate handler based on source + portal + action_type.
        
        Args:
            source: The source identifier
            portal: The portal identifier
            action_type: The action type
            action_data: The action-specific data from the request
            context: The full context including auth info
            
        Returns:
            A tuple of (success: bool, result: dict)
            - On success: (True, {"data": ...})
            - On failure: (False, {"error": ...})
            
        Raises:
            ValueError: If no handler is registered for the combination
        """
        key = self._make_key(source, portal, action_type)
        
        if key not in self._handlers:
            raise ValueError(
                f"No handler registered for source='{source}', portal='{portal}', action_type='{action_type}'"
            )
        
        handler = self._handlers[key]
        return handler.handler(action_data, context)
    
    def is_registered(self, source: str, portal: str, action_type: str) -> bool:
        """Check if a handler is registered for the given combination."""
        key = self._make_key(source, portal, action_type)
        return key in self._handlers
    
    def get_registered_handlers(self) -> dict[str, str]:
        """Get a dictionary of all registered handlers and their descriptions."""
        return {
            key: handler.description 
            for key, handler in self._handlers.items()
        }


# Global registry instance
action_registry = ActionHandlerRegistry()


# Import and register handlers from portal modules
from portals.handlers import bbmp_handlers

# Register all handlers from the handlers module
for source, portal, action_type, handler_func, description in bbmp_handlers.get_handlers():
    action_registry.register(source, portal, action_type, description)(handler_func)
