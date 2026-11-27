
from urllib.parse import urlencode
from markupsafe import escape
import base64
import requests
import json
import os

from flask import Flask, redirect, session, url_for
from authlib.integrations.flask_client import OAuth

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]

oauth = OAuth(app)

oauth.register(
    name="keycloak",
    client_id="northstar-employee-portal",
    client_kwargs={
        "scope": "openid profile email",
        "code_challenge_method": "S256",
    },
    server_metadata_url=(
        "http://localhost:8080/realms/northstar/"
        ".well-known/openid-configuration"
    ),
)


@app.route("/")
def home():
    if "user" not in session:
        return (
            '<h2>Northstar Employee Portal</h2>'
            '<a href="/login">Sign in with Keycloak</a>'
        )

    user = session["user"]

    return (
        f"<h2>Welcome, {escape(user.get('preferred_username', 'Employee'))}</h2>"
        '<p>Authentication successful.</p>'
        '<a href="/logout">Log out of portal</a>'
    )


@app.route("/login")
def login():
    return oauth.keycloak.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )


@app.route("/callback")
def callback():

    # Exchange authorization code for tokens
    token = oauth.keycloak.authorize_access_token()

    access_token = token["access_token"]
    id_token = token["id_token"]

    # Call the protected Financial API
    try:
        response = requests.get(
            "http://localhost:5000/api/finance",
            headers={
                "Authorization": f"Bearer {access_token}"
            },
            timeout=10
        )

        print("\nFinancial API Response:")
        print("Status Code:", response.status_code)
        print("Response:", response.text)

    except requests.exceptions.RequestException as error:
        print("\nFinancial API request failed:")
        print(error)

    # Decode the access token payload
    payload_encoded = access_token.split(".")[1]
    payload_encoded += "=" * (-len(payload_encoded) % 4)

    payload = json.loads(
        base64.urlsafe_b64decode(payload_encoded)
    )

    print("\nAccess Token Payload:")
    print(json.dumps(payload, indent=4))

    # Decode the ID token header
    header_encoded = id_token.split(".")[0]
    header_encoded += "=" * (-len(header_encoded) % 4)

    header = json.loads(
        base64.urlsafe_b64decode(header_encoded)
    )

    print("\nJWT Header:")
    print(json.dumps(header, indent=4))

    # Establish the application session
    user = dict(token["userinfo"])
    session["user"] = user

    # Display OIDC identity claims
    claims = {
        "iss": user.get("iss"),
        "sub": user.get("sub"),
        "aud": user.get("aud"),
        "exp": user.get("exp"),
        "iat": user.get("iat"),
        "preferred_username": user.get("preferred_username"),
        "email": user.get("email")
    }

    print("\nOIDC Identity Claims:")

    for key, value in claims.items():
        print(f"{key}: {value}")

    return redirect(url_for("home"))


@app.route("/logout")
def logout():

    # Clear the local application session
    session.clear()

    # Initiate Keycloak logout
    logout_url = (
        "http://localhost:8080/realms/northstar"
        "/protocol/openid-connect/logout"
    )

    params = {
        "client_id": "northstar-employee-portal",
        "post_logout_redirect_uri": "http://localhost:3000/"
    }

    return redirect(logout_url + "?" + urlencode(params))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=3000, debug=False)
