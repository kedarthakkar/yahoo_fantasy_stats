from flask import Flask, render_template, jsonify, redirect, request, session
from yahoo_oauth import OAuth2
import yahoo_fantasy_api as yfa
import statistics
from datetime import datetime
import os
import json 
import logging 
import sys

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev')  # Add a secret key for sessions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))

# OAuth configuration
YAHOO_AUTH_URL = "https://api.login.yahoo.com/oauth2/request_auth"
YAHOO_TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
REDIRECT_URI = "https://fantasy-wrapped-e5f08855da35.herokuapp.com/callback"
CLIENT_ID = os.getenv('CONSUMER_KEY')
CLIENT_SECRET = os.getenv('CONSUMER_SECRET')

@app.route('/auth')
def handle_oauth():
    """Initialize and handle OAuth2 authentication with Yahoo"""
    auth_params = {
        'client_id': CLIENT_ID,
        'redirect_uri': 'oob',
        'response_type': 'code',
        # 'scope': 'fspt-w'
    }
    
    auth_url = f"{YAHOO_AUTH_URL}?" + "&".join(f"{k}={v}" for k, v in auth_params.items())
    return redirect(auth_url)


# def get_oauth_session():
#     """Get or create OAuth session"""
#     if 'oauth_token' not in session:
#         return None
    
#     try:
#         sc = OAuth2(os.getenv('CONSUMER_KEY'), 
#                    os.getenv('CONSUMER_SECRET'),
#                    token_dict=session['oauth_token'])
#         return sc
#     except Exception as e:
#         logger.error(f"Error creating OAuth session: {e}")
#         return None

@app.route('/callback')
def callback():
    """Handle OAuth callback"""
    try:
        code = request.args.get('code')
        if not code:
            return "No code provided", 400

        sc = OAuth2(os.getenv('CONSUMER_KEY'), 
                   os.getenv('CONSUMER_SECRET'),
                   browser_callback=True)
        
        # Get token using the authorization code
        token = sc.get_token(code)
        session['oauth_token'] = token
        
        return redirect('/')
    except Exception as e:
        logger.error(f"Callback error: {e}")
        return str(e), 500

def get_fantasy_stats():
    try:
        # Get OAuth session
        sc = get_oauth_session()
        if not sc:
            return {"success": False, "error": "Not authenticated", "needs_auth": True}

        # Rest of your existing get_fantasy_stats code...
        # Create a Game object for NFL
        game = yfa.Game(sc, "nfl")

        logger.info("MADE IT HERE")
        
        # Get the league ID for the current season
        current_year = datetime.now().year
        league_id = game.league_ids(year=current_year)[0]
        
        # Create a League object
        league = game.to_league(league_id)
        
        # Get all teams in the league
        teams = league.teams()
        
        # Dictionary to store team scores
        team_scores = {team["name"]: [] for team in teams.values()}
        
        # Get the current week
        current_week = league.current_week()
        
        # Collect scores for each week
        for week in range(1, current_week):
            scores = league.matchups(week=week)["fantasy_content"]["league"][1]["scoreboard"]["0"]["matchups"]
            # Iterate over each matchup
            for i in range(scores["count"]):
                team_1_name = scores[str(i)]["matchup"]["0"]["teams"]["0"]["team"][0][2]["name"]
                team_2_name = scores[str(i)]["matchup"]["0"]["teams"]["1"]["team"][0][2]["name"]
                team_1_score = float(scores[str(i)]["matchup"]["0"]["teams"]["0"]["team"][1]["team_points"]["total"])
                team_2_score = float(scores[str(i)]["matchup"]["0"]["teams"]["1"]["team"][1]["team_points"]["total"])
                team_scores[team_1_name].append(team_1_score)
                team_scores[team_2_name].append(team_2_score)
        
        # Calculate statistics for each team
        results = {}
        for team_name, scores in team_scores.items():
            results[team_name] = {
                "mean": statistics.mean(scores),
                "median": statistics.median(scores),
                "stdev": statistics.stdev(scores),
                "scores": scores,  # Include individual scores for visualization
                "max": max(scores),
                "min": min(scores)
            }
        
        return {"success": True, "data": results}
    except Exception as e:
        logger.error(f"Error in get_fantasy_stats: {e}")
        return {"success": False, "error": str(e)}

@app.route('/')
def home():
    if 'oauth_token' not in session:
        return render_template('index.html', needs_auth=True)
    return render_template('index.html')

@app.route('/api/stats')
def get_stats():
    stats = get_fantasy_stats()
    return jsonify(stats)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
