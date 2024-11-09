from flask import Flask, redirect, request, session, url_for, render_template
from dotenv import load_dotenv
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError
from spotipy import SpotifyException
import logging
import time

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", 'supersecretkey')  # Store your secret key securely
app.config['SESSION_COOKIE_NAME'] = 'Spotify Auth Session'

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.getenv("REDIRECT_URI")

scope = 'user-read-private user-read-email user-library-read user-library-modify user-read-playback-state ' \
        'user-modify-playback-state user-read-currently-playing playlist-read-private playlist-read-collaborative ' \
        'playlist-modify-private playlist-modify-public user-follow-read user-follow-modify user-top-read ' \
        'user-read-recently-played app-remote-control streaming'

# Create a single SpotifyOAuth instance
sp_oauth = SpotifyOAuth(client_id=client_id,
                        client_secret=client_secret,
                        redirect_uri=SPOTIPY_REDIRECT_URI,
                        scope=scope,
                        show_dialog=True)

def is_token_expired(token_info):
    now = int(time.time())
    return token_info['expires_at'] - now < 60

def get_token():
    token_info = session.get('token_info', None)
    if not token_info:
        return None

    if is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        session['token_info'] = token_info
    return token_info

@app.route('/', methods=['GET', 'POST'])
def index():
    message = None
    logged_in = False
    track_info = None

    token_info = get_token()

    if token_info:
        logged_in = True

        try:
            sp = spotipy.Spotify(auth=token_info['access_token'])

            if request.method == 'POST':
                song_name = request.form['song_name']
                results = sp.search(q=song_name, limit=1)
                if results['tracks']['items']:
                    track = results['tracks']['items'][0]
                    track_info = {
                        'name': track['name'],
                        'artist': track['artists'][0]['name'],
                        'album': track['album']['name'],
                    }
                    sp.add_to_queue(track['id'])
                    sp.next_track()
                else:
                    track_info = {'error': 'Song not found'}

        except SpotifyOauthError as eAuth:
            logger.error(f"Spotify OAuth error: {eAuth}")
            return redirect(url_for('login'))
        except SpotifyException as SpException:
            logger.error(f"Spotify API error: {SpException}")
            message = "There was a problem with the Spotify API. Please try again later."
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            message = "An unexpected error occurred. Please try again later."
    else:
        return redirect(url_for('login'))

    return render_template('index.html', track_info=track_info, message=message, logged_in=logged_in)

@app.route('/callback')
def callback():

    # Exchange the authorization code for an access token and refresh token
    token_info = sp_oauth.get_cached_token()
    session['token_info'] = token_info

    # Create a Spotify client with the access token
    sp = spotipy.Spotify(auth=token_info['access_token'])

    # Fetch and print the current user's details for verification
    user = sp.current_user()
    print(f"Logged in as: {user['display_name']} ({user['id']})")

    return redirect(url_for('index'))

@app.route('/login')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/logout')
def logout():
    # Clear the token from the session
    session.pop('token_info', None)
    # Clear the entire session
    session.clear()
    return redirect("/")

if __name__ == '__main__':
    app.run(host='192.168.5.106', port=5000, debug=True)
