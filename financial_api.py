from flask import Flask, request, jsonify
import jwt
from jwt import PyJWKClient

app = Flask(__name__)

ISSUER = "http://localhost:8080/realms/northstar"
AUDIENCE = "northstar-finance-api"

JWKS_URL = ISSUER + "/protocol/openid-connect/certs"
jwks_client = PyJWKClient(JWKS_URL)


@app.route("/api/finance", methods=["GET"])
def finance():

    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing access token"}), 401

    token = auth_header.split(" ", 1)[1]

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=AUDIENCE,
            issuer=ISSUER,
            options={"require": ["exp", "iss", "aud", "sub"]}
        )

        if claims.get("typ") != "Bearer":
            return jsonify({"error": "Invalid token type"}), 401

    except jwt.PyJWTError:
        return jsonify({"error": "Invalid access token"}), 401

    roles = claims.get("realm_access", {}).get("roles", [])

    if "finance" not in roles:
        return jsonify({"error": "Insufficient permissions"}), 403

    return jsonify({
        "message": "Access granted",
        "department": "Finance",
        "quarterly_revenue": 2500000
    }), 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)