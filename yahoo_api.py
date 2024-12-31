from flask import Flask, render_template, jsonify, redirect, request, session
import yahoo_fantasy_api as yfa
import statistics
from datetime import datetime
import os
import json 
import logging 
import sys
import requests

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))

class YahooAPI:
    def __init__(self, token):
        self.token = token
        self.base_url = "https://fantasysports.yahooapis.com/fantasy/v2"
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json'
        }
    
    def get_league_data(self):
        # Get all leagues for current year
        current_year = datetime.now().year
        url = f"{self.base_url}/users;use_login=1/games;game_keys=nfl/leagues?format=json"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        leagues_data = response.json()
        
        # Get the first league ID (you might want to modify this to handle multiple leagues)
        league_key = leagues_data['fantasy_content']['users']['0']['user'][1]['games']['0']['game'][1]['leagues']['0']['league'][0]['league_key']
        
        return self.get_league_stats(league_key)
    
    def get_league_stats(self, league_key):
        # Get teams in league
        teams_url = f"{self.base_url}/league/{league_key}/teams?format=json"
        teams_response = requests.get(teams_url, headers=self.headers)
        teams_response.raise_for_status()
        teams_data = teams_response.json()

        # Get current week
        standings_url = f"{self.base_url}/league/{league_key}/standings?format=json"
        standings_response = requests.get(standings_url, headers=self.headers)
        standings_response.raise_for_status()
        standings_data = standings_response.json()
        current_week = standings_data['fantasy_content']['league'][0]['current_week']

        # Initialize team scores
        teams = {}
        for team in teams_data['fantasy_content']['league'][1]['teams'].values():
            if isinstance(team, dict):
                team_name = team['team'][0][2]['name']
                teams[team_name] = []
        
        # Get scores for each week
        for week in range(1, int(current_week)):
            scoreboard_url = f"{self.base_url}/league/{league_key}/scoreboard;week={week}?format=json"
            scores_response = requests.get(scoreboard_url, headers=self.headers)
            scores_response.raise_for_status()
            scores_data = scores_response.json()
            matchups = scores_data['fantasy_content']['league'][1]['scoreboard']['0']['matchups'] 
            for i in range(int(matchups['count'])):
                matchup = matchups[str(i)]['matchup']
                logger.info(matchup['0']['teams'])
                for team in matchup['0']['teams'].values():
                    # logger.info('team: ' + str(team))
                    # logger.info('team type: ' + str(type(team)))
                    team_name = team['team'][0][2]['name']
                    team_score = float(team['team'][1]['team_points']['total'])
                    teams[team_name].append(team_score)

        logger.info('teams 2: ' + str(teams))
        
        # Calculate statistics
        results = {}
        for team_name, scores in teams.items():
            if len(scores) >= 2:  # Need at least 2 scores for standard deviation
                results[team_name] = {
                    "mean": statistics.mean(scores),
                    "median": statistics.median(scores),
                    "stdev": statistics.stdev(scores),
                    "scores": scores,
                    "max": max(scores),
                    "min": min(scores)
                }

        logger.info('results: ' + str(results))
        
        return results
