from yahoo_oauth import OAuth2
import yahoo_fantasy_api as yfa
import statistics

# Authenticate with Yahoo
sc = OAuth2(None, None, from_file="oauth2.json")

# Create a Game object for NFL
game = yfa.Game(sc, "nfl")

# Get the league ID for the current season
league_id = game.league_ids(year=2024)[0]

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
    scores = league.matchups(week=week)["fantasy_content"]["league"][1]["scoreboard"][
        "0"
    ]["matchups"]
    # Iterate over each matchup
    for i in range(scores["count"]):
        team_1_name = scores[str(i)]["matchup"]["0"]["teams"]["0"]["team"][0][2]["name"]
        team_2_name = scores[str(i)]["matchup"]["0"]["teams"]["1"]["team"][0][2]["name"]
        team_1_score = float(
            scores[str(i)]["matchup"]["0"]["teams"]["0"]["team"][1]["team_points"][
                "total"
            ]
        )
        team_2_score = float(
            scores[str(i)]["matchup"]["0"]["teams"]["1"]["team"][1]["team_points"][
                "total"
            ]
        )
        team_scores[team_1_name].append(team_1_score)
        team_scores[team_2_name].append(team_2_score)

# Calculate mean and median for each team
results = {}
for team_name, scores in team_scores.items():
    mean = statistics.mean(scores)
    median = statistics.median(scores)
    stdev = statistics.stdev(scores)
    results[team_name] = {"mean": mean, "median": median, "stdev": stdev}

# Print results
print("Team Score Statistics:")
print("=====================")
for team_name, stats in results.items():
    print(f"{team_name}:")
    print(f"  Mean: {stats['mean']:.2f}")
    print(f"  Median: {stats['median']:.2f}")
    print(f"  Standard Deviation: {stats['stdev']:.2f}")
    print()
