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
REDIRECT_URI = os.getenv("REDIRECT_URI")
CLIENT_ID = os.getenv("CONSUMER_KEY")
CLIENT_SECRET = os.getenv("CONSUMER_SECRET")


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


def refresh_access_token():
    """
    Exchange the refresh token for a new access token.
    """
    try:
        token_data = {
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "refresh_token": session["refresh_token"],
        }

        response = requests.post(YAHOO_TOKEN_URL, data=token_data)
        if response.status_code != 200:
            logger.error(f"Token exchange failed: {response.text}")
            return "Authentication failed", 500

        token_info = response.json()
        session["access_token"] = token_info["access_token"]
        return redirect(url_for("home"))
    except Exception as e:
        logger.error(f"Error in refresh_token: {e}")
        return "Refresh token exchange failed", 500


def get_fantasy_team_list(league_key):
    """
    Call YahooAPI class to get team list.
    """
    try:
        if "access_token" not in session:
            return {"success": False, "error": "Not authenticated", "needs_auth": True}

        yahoo = YahooAPI(session["access_token"])
        team_names, team_logos = yahoo.get_team_list(league_key)
        return {
            "success": True,
            "data": {"team_names": team_names, "team_logos": team_logos},
        }
    except Exception as e:
        logger.error(f"Error in get_team_list: {e}")
        return {"success": False, "error": str(e)}


def get_fantasy_team_wrapped(team_name, league_key):
    """
    Call YahooAPI class to get the necessary information for the wrapped summary.
    """
    try:
        if "access_token" not in session:
            return {"success": False, "error": "Not authenticated", "needs_auth": True}

        yahoo = YahooAPI(session["access_token"])
        team_info = yahoo.get_team_wrapped(team_name, league_key)
        return {
            "success": True,
            "data": {
                "team_logo": team_info["logo_url"],
                "team_rank": team_info["rank"],
                "team_record": team_info["record"],
                "team_avg_points": team_info["avg_points"],
                "bbq_chicken": team_info["bbq_chicken"],
                "bbq_chicken_avg_points": team_info["bbq_chicken_avg_points"],
                "nemesis": team_info["nemesis"],
                "nemesis_avg_points": team_info["nemesis_avg_points"],
                "percentage_improvement": team_info["percentage_improvement"],
                "over_under_performer": team_info["over_under_performer"],
            },
        }
    except Exception as e:
        logger.error(f"Error in get_team_wrapped: {e}")
        return {"success": False, "error": str(e)}


@app.route("/")
def home():
    if "access_token" not in session:
        return render_template("league_list.html", needs_auth=True)

    try:
        yahoo_api = YahooAPI(session["access_token"])
    except Exception as e:
        refresh_access_token()

    league_names, league_keys = yahoo_api.get_league_list()
    return render_template(
        "league_list.html",
        league_info=zip(league_names, league_keys),
        needs_auth=False,
    )


@app.route("/team_list/<league_key>")
def team_list(league_key):
    if "access_token" not in session:
        return render_template("team_list.html", needs_auth=True)

    try:
        yahoo_api = YahooAPI(session["access_token"])
    except Exception as e:
        refresh_access_token()

    team_list = get_fantasy_team_list(league_key)
    session["team_name_mapping"] = {
        team_name.replace(" ", "-"): team_name for team_name in team_list["data"]["team_names"]
    }
    session["league_key"] = league_key
    return render_template(
        "team_list.html",
        team_info=zip(team_list["data"]["team_names"], team_list["data"]["team_logos"]),
        needs_auth=False,
    )


@app.route("/team_wrapped/<team_name>")
def get_team_wrapped(team_name):
    if "team_name_mapping" not in session:
        team_name = team_name.replace("-", " ")
    team_name = session["team_name_mapping"][team_name]
    wrapped = get_fantasy_team_wrapped(team_name, session["league_key"])
    if wrapped["data"]["over_under_performer"] == "Over":
        badge_image = "images/overperformer.webp"
    else:
        badge_image = "images/underperformer.webp"

    return render_template(
        "wrapped.html",
        team_name=team_name,
        team_logo=wrapped["data"]["team_logo"],
        team_rank=wrapped["data"]["team_rank"],
        team_record=wrapped["data"]["team_record"],
        team_avg_points=wrapped["data"]["team_avg_points"],
        bbq_chicken=wrapped["data"]["bbq_chicken"],
        bbq_chicken_avg_points=wrapped["data"]["bbq_chicken_avg_points"],
        nemesis=wrapped["data"]["nemesis"],
        nemesis_avg_points=wrapped["data"]["nemesis_avg_points"],
        percentage_improvement=wrapped["data"]["percentage_improvement"],
        over_under_performer=wrapped["data"]["over_under_performer"],
        badge_image=badge_image,
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
