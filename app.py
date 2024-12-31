from flask import Flask, render_template, jsonify, redirect, request, session, url_for
from yahoo_oauth import OAuth2
import yahoo_fantasy_api as yfa
import statistics
from datetime import datetime
import os
import json
import logging
import requests
import sys
import time
from yahoo_api import YahooAPI

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev")  # Add a secret key for sessions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))

# OAuth configuration
YAHOO_AUTH_URL = "https://api.login.yahoo.com/oauth2/request_auth"
YAHOO_TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
REDIRECT_URI = "https://fantasy-wrapped-e5f08855da35.herokuapp.com/callback"
CLIENT_ID = os.getenv("CONSUMER_KEY")
CLIENT_SECRET = os.getenv("CONSUMER_SECRET")

# TODO: Properly handle refresh token (currently the application fails if the access token expires)


@app.route("/auth")
def handle_oauth():
    """
    Initialize and handle OAuth2 authentication with Yahoo. The client is redirected to
    the callback route after authentication with authorization code provided in the request.
    """
    auth_params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
    }

    auth_url = f"{YAHOO_AUTH_URL}?" + "&".join(
        f"{k}={v}" for k, v in auth_params.items()
    )
    return redirect(auth_url)


@app.route("/callback")
def callback():
    """
    Handle OAuth callback. The authorization code is exchanged for an access token and refresh token.
    """
    try:
        code = request.args.get("code")
        if not code:
            return "No code provided", 400

        # Exchange code for token
        token_data = {
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "code": code,
        }

        response = requests.post(YAHOO_TOKEN_URL, data=token_data)
        if response.status_code != 200:
            logger.error(f"Token exchange failed: {response.text}")
            return "Authentication failed", 500

        token_info = response.json()
        session["access_token"] = token_info["access_token"]
        session["refresh_token"] = token_info.get("refresh_token")

        return redirect(url_for("home"))

    except Exception as e:
        logger.error(f"Callback error: {e}")
        return str(e), 500


def get_fantasy_stats():
    """
    Call YahooAPI class to get fantasy season stats.
    """
    try:
        if "access_token" not in session:
            return {"success": False, "error": "Not authenticated", "needs_auth": True}

        yahoo = YahooAPI(session["access_token"])
        results = yahoo.get_league_stats()
        return {"success": True, "data": results}

    except Exception as e:
        logger.error(f"Error in get_fantasy_stats: {e}")
        return {"success": False, "error": str(e)}

def get_fantasy_team_list():
    """
    Call YahooAPI class to get team list.
    """
    try:
        if "access_token" not in session:
            return {"success": False, "error": "Not authenticated", "needs_auth": True}

        yahoo = YahooAPI(session["access_token"])
        team_names, team_logos = yahoo.get_team_list()
        return {"success": True, "data": {"team_names": team_names, "team_logos": team_logos}}
    except Exception as e:
        logger.error(f"Error in get_team_list: {e}")
        return {"success": False, "error": str(e)}


@app.route("/")
def home():
    """
    Renders the home page, with authentication flow if the user is not authenticated.
    """
    if "access_token" not in session:
        return render_template("index.html", needs_auth=True)
    return render_template("index.html")


@app.route("/api/stats")
def get_stats():
    stats = get_fantasy_stats()
    return jsonify(stats)


@app.route("/team_list")
def get_team_list():
    return render_template("team_list.html")
    # team_list = get_fantasy_team_list()
    # return jsonify(team_list)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
