import configparser
import requests
import json
import datetime as dt
import time
import os
import re

script_dir = os.path.dirname(os.path.abspath(__file__)) # Get the path to the directory containing this script
config_path = os.path.join(script_dir, 'config.txt') # Construct the path to the configuration file

# Load the configuration file
config = configparser.ConfigParser()
config.read(config_path)

# Initialize global variables from config.txt
CLIENT_ID = config.get('strava', 'client_id')
CLIENT_SECRET = config.get('strava', 'client_secret')
REFRESH_TOKEN = config.get('strava', 'refresh_token')
ACCESS_TOKEN = config.get('strava', 'access_token')
expires_at = int(config.get('strava', 'expires_at'))
API_KEY = config.get('open_weather', 'api_key')

# Writes json input to 'sample.json' for testing
def write_json(data):
    with open("sample.json", "w") as f:
        f.write(json.dumps(data, indent=4))
    f.close()

def can_apply_weather(activity):
    start_minutes_seconds = re.search(r':(\d{2}):(\d{2})Z', activity['start_date']).groups()
    start_minutes = int(start_minutes_seconds[0]) + int(start_minutes_seconds[1]) / 60
    elapsed_minutes = activity['elapsed_time'] / 60
    if (start_minutes + elapsed_minutes >= 60 and activity['type'] != 'VirtualRide' and not activity['trainer'] and not activity['manual']):
        return True
    return False

while (True):
    # Check if access token is expired and get a new one using the refresh token
    if (expires_at < dt.datetime.now().timestamp()):
        # Get a new refresh token
        refresh_obj = requests.post(f'https://www.strava.com/api/v3/oauth/token?client_id={CLIENT_ID}&client_secret={CLIENT_SECRET}&grant_type=refresh_token&refresh_token={REFRESH_TOKEN}',
            headers={
                "Content-Type": "application/json"
            }
        ).json()
        
        # Set the program variables
        ACCESS_TOKEN = refresh_obj['access_token']
        REFRESH_TOKEN = refresh_obj['refresh_token']
        expires_at = refresh_obj['expires_at']

        # Update the config varialbes
        config.set('strava', 'access_token', refresh_obj['access_token'])
        config.set('strava', 'refresh_token', refresh_obj['refresh_token'])
        config.set('strava', 'expires_at', str(refresh_obj['expires_at']))

        # Write new variables to config.txt
        with open('config.txt', 'w') as configfile:
            config.write(configfile)
    
    # Get the authenticated athlete's 30 most recent activities
    activities = requests.get('https://www.strava.com/api/v3/athlete/activities',
        headers={
            'Authorization': 'Bearer ' + ACCESS_TOKEN
        }
    ).json()

    # Get the index of the most recent activity that is not virtual or manual or 
    idx = 0
    while (can_apply_weather(activities[idx])):
        idx += 1
    idx -= 1

    # Get the detailed data of the activity
    recent_activity = requests.get('https://www.strava.com/api/v3/activities/' + str(activities[idx]['id']),
        headers={
            'Authorization': 'Bearer ' + ACCESS_TOKEN
        }
    ).json()
    
    # Check if the description already includes the weather data
    if (not re.search(r'\d+.F \| \d+\.\d mph', recent_activity['description'])):
        start_date = int(dt.datetime.strptime(recent_activity['start_date'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc).timestamp())
        end_date = start_date + recent_activity['elapsed_time']
        start_lat, start_lon = recent_activity['start_latlng']

        # Get the weather data at the start point for the duration of the activity
        weather = requests.get(f'https://history.openweathermap.org/data/2.5/history/city?lat={start_lat}&lon={start_lon}&start={start_date}&end={end_date}&units=imperial&appid={API_KEY}').json()

        # Extract the important weather data from weather and average it over the duration of the activity
        avg_temp = sum(list(map(lambda elem: elem['main']['temp'], weather['list']))) / len(weather['list'])
        avg_wind_speed = sum(list(map(lambda elem: elem['wind']['speed'], weather['list']))) / len(weather['list'])
        avg_wind_dir = sum(list(map(lambda elem: elem['wind']['deg'], weather['list']))) / len(weather['list'])
        
        # Convert the wind direction in deg to the corresponding arrow character
        if (-22.5 <= avg_wind_dir and avg_wind_dir < 22.5): # N
            wind_arrow = chr(8595)
        elif (22.5 <= avg_wind_dir and avg_wind_dir < 22.5 * 3): # NE
            wind_arrow = chr(8601)
        elif (22.5 * 3 <= avg_wind_dir and avg_wind_dir < 22.5 * 5): # E
            wind_arrow = chr(8592)
        elif (22.5 * 5 <= avg_wind_dir and avg_wind_dir < 22.5 * 7): # SE
            wind_arrow = chr(8598)
        elif (22.5 * 7 <= avg_wind_dir and avg_wind_dir < 22.5 * 9): # S
            wind_arrow = chr(8593)
        elif (22.5 * 9 <= avg_wind_dir and avg_wind_dir < 22.5 * 11): # SW
            wind_arrow = chr(8599)
        elif (22.5 * 11 <= avg_wind_dir and avg_wind_dir < 22.5 * 13): # W
            wind_arrow = chr(8594)
        else: # NW
            wind_arrow = chr(8600)

        # Format weather description
        description = f'{round(avg_temp)}{chr(176)}F | {round(avg_wind_speed * 10) / 10} mph {wind_arrow}'
        if (not recent_activity['description']):
            description = recent_activity['description'] + '\n' + description
        
        # Add the description to the activity
        activity_id = recent_activity['id']
        requests.put(f'https://www.strava.com/api/v3/activities/{activity_id}',
            headers={
                'Authorization': 'Bearer ' + ACCESS_TOKEN,
                'Content_Type': 'application/json'
            },
            data={
                'description': description
            }
        )
    
    # Print the description of the activity with the date
    activity_YMD = re.match(r'^(\d{4})-(\d{2})-(\d{2})', recent_activity['start_date_local']).group()
    print('Description of activity on ' + activity_YMD + ':\n' + recent_activity['description'] + '\n')
    time.sleep(180)