"""
Debugging utilities for the pricing engine.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from utils.logging import setup_logger
import inspect
import traceback
from typing import Callable, Dict, Any, List

logger = setup_logger(__name__)


async def debug_routes_middleware(request: Request, call_next):
    """
    Middleware that provides detailed debugging information for 404 errors.

    Args:
        request: The incoming request
        call_next: The next middleware/handler in the chain

    Returns:
        Response: The original response or enhanced debug response
    """
    # Process the request first
    response = await call_next(request)

    # Only add debug info for 404 errors
    if response.status_code == 404:
        logger.warning(f"404 Not Found: {request.method} {request.url.path}")

        # Log all registered routes
        routes_info = extract_routes_info(request.app)

        # Find similar routes
        similar_routes = find_similar_routes(request.url.path, routes_info)

        if similar_routes:
            logger.info(f"Similar routes that might match: {similar_routes}")

            # Optionally enhance response in development mode
            if "development" == "development":  # Replace with config check
                return JSONResponse(
                    status_code=404,
                    content={
                        "error": f"Route not found: {request.url.path}",
                        "similar_routes": similar_routes,
                        "message": "Check similar routes that might match your request"
                    }
                )

    return response


def extract_routes_info(app) -> List[str]:
    """
    Extract information about all routes in the application.

    Args:
        app: The FastAPI application

    Returns:
        List[str]: List of route information strings
    """
    routes_info = []

    # Process direct routes
    for route in app.routes:
        if hasattr(route, "path"):
            methods = getattr(route, "methods", set())
            methods_str = ", ".join(methods) if methods else "GET"
            routes_info.append(f"{route.path} ({methods_str})")

        # Process router routes
        if hasattr(route, "routes"):
            prefix = getattr(route, "prefix", "")
            for r in route.routes:
                if hasattr(r, "path"):
                    methods = getattr(r, "methods", set())
                    methods_str = ", ".join(methods) if methods else "GET"
                    routes_info.append(f"{prefix}{r.path} ({methods_str})")

                # Nested routers
                if hasattr(r, "routes"):
                    nested_prefix = getattr(r, "prefix", "")
                    for nr in r.routes:
                        if hasattr(nr, "path"):
                            methods = getattr(nr, "methods", set())
                            methods_str = ", ".join(methods) if methods else "GET"
                            routes_info.append(
                                f"{prefix}{nested_prefix}{nr.path} ({methods_str})"
                            )

    return routes_info


def find_similar_routes(path: str, routes_info: List[str]) -> List[str]:
    """
    Find routes similar to the requested path.

    Args:
        path: The requested path
        routes_info: List of route information strings

    Returns:
        List[str]: List of similar routes
    """
    similar_routes = []
    path_parts = path.split("/")

    for route_str in routes_info:
        route_path = route_str.split(" ")[0]
        route_parts = route_path.split("/")

        # Check similarity - matching at least half the path components
        # or at least 2 components for short paths
        min_matches = max(len(path_parts) // 2, 2)
        matches = sum(1 for p1, p2 in zip(path_parts, route_parts) if p1 == p2)

        if matches >= min_matches:
            similar_routes.append(route_str)

    return similar_routes


async def debug_routes_handler(request: Request) -> Dict[str, Any]:
    """
    Handler function for the debug routes endpoint.

    Args:
        request: The incoming request

    Returns:
        Dict[str, Any]: Debug information about routes
    """
    app = request.app

    # Extract route information
    routes_info = extract_routes_info(app)

    # Organize routes by module
    routes_by_module = {}
    for route in app.routes:
        if hasattr(route, "endpoint"):
            module = inspect.getmodule(route.endpoint).__name__
            if module not in routes_by_module:
                routes_by_module[module] = []

            methods = getattr(route, "methods", set())
            methods_str = ", ".join(methods) if methods else "GET"
            routes_by_module[module].append(
                {"path": route.path, "methods": methods_str}
            )

    return {
        "routes": routes_info,
        "routes_by_module": routes_by_module,
        "router_structure": {
            "app_root": "/",
            "combined_router_prefix": "/api"
        }
    }