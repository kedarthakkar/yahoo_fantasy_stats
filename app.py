from flask import Flask, render_template, jsonify
from yahoo_oauth import OAuth2
import yahoo_fantasy_api as yfa
import statistics
from datetime import datetime
import os
import json 
import logging 
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))

app = Flask(__name__)

def get_fantasy_stats():
    try:
        # Authenticate with Yahoo
        oauth_creds = {
            'consumer_key': os.getenv('CONSUMER_KEY'),
            'consumer_secret': os.getenv('CONSUMER_SECRET'),
        }

        with open('oauth.json', 'w') as f:
            json.dump(oauth_creds, f)
            
        sc = OAuth2(None, None, from_file='oauth.json')
        
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
        return {"success": False, "error": str(e)}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/stats')
def get_stats():
    stats = get_fantasy_stats()
    return jsonify(stats)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
