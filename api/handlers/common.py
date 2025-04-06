"""
Common utilities for API handlers (serverless functions).
"""

import json
from typing import Dict, Any, Optional, Union
import traceback
from utils.logging import setup_logger

logger = setup_logger(__name__)


def parse_request_body(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse request body from a serverless function event.

    Args:
        event: The event object from the serverless function

    Returns:
        Dict[str, Any]: Parsed body as a dictionary
    """
    body = event.get("body", "{}")

    if isinstance(body, str):
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            logger.warning("Failed to parse request body as JSON")
            return {}
    elif isinstance(body, dict):
        return body
    else:
        logger.warning(f"Unexpected body type: {type(body)}")
        return {}


def create_response(
    status_code: int = 200,
    body: Union[Dict[str, Any], str] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Create a standardized response object for serverless functions.

    Args:
        status_code: HTTP status code
        body: Response body (dict will be converted to JSON)
        headers: Optional response headers

    Returns:
        Dict[str, Any]: Response object for the serverless function
    """
    if headers is None:
        headers = {"Content-Type": "application/json"}

    # Convert dict to JSON string
    if isinstance(body, dict):
        body = json.dumps(body)

    return {"statusCode": status_code, "headers": headers, "body": body}


def handle_exception(e: Exception, context: str = "handler") -> Dict[str, Any]:
    """
    Handle exceptions in serverless functions.

    Args:
        e: The exception
        context: Context string for logging

    Returns:
        Dict[str, Any]: Error response object
    """
    error_msg = str(e)
    logger.error(f"Error in {context}: {error_msg}")
    logger.debug(traceback.format_exc())

    return create_response(status_code=500, body={"success": False, "error": error_msg})
