"""
Local development server for the pricing engine API.
"""

import os
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from functools import wraps

# Load environment variables
load_dotenv()

# Import API endpoints
from api.endpoints import check_violations, optimize_prices

app = Flask(__name__)

# Simple API key authentication
API_KEY = os.environ.get("API_KEY", "dev_api_key_123")


def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get API key from header
        api_key = request.headers.get("X-API-Key")

        # Check if API key is valid
        if api_key != API_KEY:
            return jsonify({"success": False, "error": "Invalid API key"}), 401

        return f(*args, **kwargs)

    return decorated_function


@app.route("/api/check-violations", methods=["POST"])
@require_api_key
def api_check_violations():
    # Create mock event object
    event = {"body": json.dumps(request.json)}

    # Call the endpoint function
    result = check_violations(event, {})

    # Return the result
    return jsonify(json.loads(result.get("body", "{}")))


@app.route("/api/optimize-prices", methods=["POST"])
@require_api_key
def api_optimize_prices():
    # Create mock event object
    event = {"body": json.dumps(request.json)}

    # Call the endpoint function
    result = optimize_prices(event, {})

    # Return the result
    return jsonify(json.loads(result.get("body", "{}")))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
    print(f"Server running on port {port}")
