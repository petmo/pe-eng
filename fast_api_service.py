"""
Enhanced local development server for the pricing engine API with better debugging.
"""

import os
import json
import logging
from flask import Flask, request, jsonify, Response
from dotenv import load_dotenv
from functools import wraps

# Load environment variables
load_dotenv()

# Import API endpoints
from api.endpoints import check_violations, optimize_prices

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Simple API key authentication
API_KEY = os.environ.get("API_KEY", "dev_api_key_123")


def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Log all headers for debugging
        logger.debug("Request headers: %s", dict(request.headers))

        # Get API key from header
        api_key = request.headers.get("X-API-Key")
        logger.debug("Received API key: %s", api_key[:3] + "..." if api_key else None)

        # Check if API key is valid
        if api_key != API_KEY:
            logger.warning("Invalid API key provided")
            return jsonify({"success": False, "error": "Invalid API key"}), 401

        return f(*args, **kwargs)

    return decorated_function


@app.route("/api/check-violations", methods=["POST"])
@require_api_key
def api_check_violations():
    logger.info("Received request to /api/check-violations")

    # Log the request body
    try:
        body = request.get_json()
        logger.debug("Request body: %s", body)
    except Exception as e:
        logger.error("Failed to parse JSON body: %s", e)
        return jsonify({"success": False, "error": "Invalid JSON body"}), 400

    # Create mock event object
    event = {"body": json.dumps(body)}

    # Call the endpoint function
    logger.debug("Calling check_violations function")
    result = check_violations(event, {})
    logger.debug("check_violations response status: %s", result.get("statusCode"))

    # Return the result
    return Response(
        result.get("body", "{}"),
        status=result.get("statusCode", 200),
        mimetype="application/json",
    )


@app.route("/api/optimize-prices", methods=["POST"])
@require_api_key
def api_optimize_prices():
    logger.info("Received request to /api/optimize-prices")

    # Log the request body
    try:
        body = request.get_json()
        logger.debug("Request body: %s", body)
    except Exception as e:
        logger.error("Failed to parse JSON body: %s", e)
        return jsonify({"success": False, "error": "Invalid JSON body"}), 400

    # Create mock event object
    event = {"body": json.dumps(body)}

    # Call the endpoint function
    logger.debug("Calling optimize_prices function")
    result = optimize_prices(event, {})
    logger.debug("optimize_prices response status: %s", result.get("statusCode"))

    # Return the result
    return Response(
        result.get("body", "{}"),
        status=result.get("statusCode", 200),
        mimetype="application/json",
    )


# Add a test route to verify server is running
@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"success": True, "message": "Server is running"})


# Add catch-all route for debugging
@app.route(
    "/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)
@app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
def catch_all(path):
    logger.warning("Unhandled route accessed: %s %s", request.method, request.path)
    logger.debug("Headers: %s", dict(request.headers))

    try:
        body = request.get_json(silent=True)
        if body:
            logger.debug("Body: %s", body)
    except:
        pass

    return (
        jsonify(
            {
                "success": False,
                "error": f"Route not found: {request.method} {request.path}",
                "available_routes": [
                    "GET /ping",
                    "POST /api/check-violations",
                    "POST /api/optimize-prices",
                ],
            }
        ),
        404,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"

    logger.info(f"Starting server on port {port}, debug mode: {debug}")
    logger.info(f"API key configured: {API_KEY[:3]}...")

    app.run(debug=debug, host="0.0.0.0", port=port)
