from flask import Flask, render_template, request, jsonify
import requests
from datetime import datetime
import pytz
import os

app = Flask(__name__)

def get_league_standings():
    """Fetch league standings from FPL API"""
    try:
        url = "https://fantasy.premierleague.com/api/leagues-classic/1306310/standings/"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching league data: {e}")
        return None

def get_bootstrap_data():
    """Fetch bootstrap data including events (gameweeks)"""
    try:
        url = "https://fantasy.premierleague.com/api/bootstrap-static/"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching bootstrap data: {e}")
        return None

@app.template_filter('format_datetime')
def format_datetime(utc_timestamp_str):
    utc_time = datetime.fromisoformat(utc_timestamp_str.replace('Z', '+00:00'))
    target_tz = pytz.timezone('Asia/Bangkok')
    local_time = utc_time.astimezone(target_tz)
    return local_time.strftime('%a %-d %b %H:%M')


def get_current_and_previous_event():
    """Get current and previous event based on today's date"""
    bootstrap_data = get_bootstrap_data()
    if not bootstrap_data:
        return None, None
    events = bootstrap_data.get('events', [])
    now = datetime.now(pytz.UTC)
    current_event = None
    previous_event = None
    for event in events:
        deadline = datetime.fromisoformat(event['deadline_time'].replace('Z', '+00:00'))
        if now < deadline:
            current_event = event
            break
    # Find previous event
    if current_event:
        current_id = current_event['id']
        for event in events:
            if event['id'] == current_id - 1:
                previous_event = event
                break
    return current_event, previous_event
@app.route('/')
def index():
    """Home route with league standings"""
    league_data = get_league_standings()
    bootstrap_data = get_bootstrap_data()
    current_event, previous_event = get_current_and_previous_event()

    gameweeks = []
    if bootstrap_data:
        gameweeks = bootstrap_data.get('events', [])

    link_event_id = previous_event['id'] if previous_event else 3

    if league_data:
        league_info = league_data.get('league', {})
        standings = league_data.get('standings', {}).get('results', [])
        last_updated = league_data.get('last_updated_data')

        return render_template('index.html',
                               league_name=league_info.get('name'),
                               standings=standings,
                               last_updated=last_updated,
                               gameweeks=gameweeks,
                               link_event_id=link_event_id
                               )
    else:
        return render_template('index.html',
                               league_name='TB LEAGUE 25/26',
                               standings=[],
                               gameweeks=gameweeks,
                               link_event_id=link_event_id,
                               error="Unable to load league data")


@app.route('/event/<int:event_id>')
def event_page(event_id):
    def get_event_standings(event_id):
        """Fetch event-specific standings with picks data"""
        try:
            # Get league standings
            league_url = "https://fantasy.premierleague.com/api/leagues-classic/1306310/standings/"
            league_response = requests.get(league_url)
            league_response.raise_for_status()
            league_data = league_response.json()
            league_info = league_data.get('league', {})
            standings = league_data.get('standings', {}).get('results', [])

            # Fetch picks data for each entry
            for entry in standings:
                try:
                    picks_url = f"https://fantasy.premierleague.com/api/entry/{entry['entry']}/event/{event_id}/picks/"
                    picks_response = requests.get(picks_url)
                    picks_response.raise_for_status()
                    picks_data = picks_response.json()

                    # Add event-specific data to entry
                    entry['event_total'] = picks_data.get('entry_history', {}).get('points', 0)
                    entry['event_transfers'] = picks_data.get('entry_history', {}).get('event_transfers', 0)
                    entry['event_transfers_cost'] = picks_data.get('entry_history', {}).get('event_transfers_cost', 0)
                    entry['picks'] = picks_data.get('picks', [])

                except requests.RequestException as e:
                    print(f"Error fetching picks for entry {entry['entry']}: {e}")
                    entry['event_total'] = 0
                    entry['picks'] = []

            # Sort standings by event_total in descending order
            standings.sort(key=lambda x: x.get('event_total', 0), reverse=True)

            # Update ranks based on event_total
            for i, entry in enumerate(standings, 1):
                entry['event_rank'] = i

            return league_data, standings

        except requests.RequestException as e:
            print(f"Error fetching league data: {e}")
            return None, []

    bootstrap_data = get_bootstrap_data()
    gameweeks = []
    if bootstrap_data:
        gameweeks = bootstrap_data.get('events', [])

    league_data, standings = get_event_standings(event_id)
    league_info = league_data.get('league', {})

    return render_template('event.html',
                        league_info =  league_info.get('name'),
                        event_id=event_id,
                        gameweeks=gameweeks,
                        standings=standings,
                        league_name=f"{event_id}",
                        last_updated=league_data.get('last_updated_data') if league_data else None)

@app.route('/api/data', methods=['GET', 'POST'])
def api_data():
    """API endpoint for handling data"""
    if request.method == 'POST':
        data = request.get_json()
        return jsonify({
            'message': 'Data received successfully',
            'received_data': data,
            'status': 'success'
        })
    else:
        return jsonify({
            'message': 'Welcome to the API',
            'endpoints': ['/api/data'],
            'methods': ['GET', 'POST']
        })

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return render_template('404.html'), 404

if __name__ == '__main__':
    # Enable debug mode for development
    app.run(debug=True, host='0.0.0.0', port=8090)
