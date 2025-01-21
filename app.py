from flask import Flask, redirect, request, session, url_for, render_template, jsonify
from dotenv import load_dotenv
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError
from spotipy import SpotifyException
import logging
from functools import wraps
import queue
from command_processor import SpotifyCommandProcessor


# Load environment variables and setup logging (unchanged)
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", 'supersecretkey')
app.config['SESSION_COOKIE_NAME'] = 'Spotify Auth Session'

command_processor = SpotifyCommandProcessor()

# Environment variables
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.getenv("REDIRECT_URI")

scope = 'user-read-playback-state user-modify-playback-state user-read-currently-playing app-remote-control streaming'

# Voice command queue
voice_command_queue = queue.Queue()

voice_recognition_active = False
voice_recognition_thread = None


def create_spotify_oauth():
    cache_handler = spotipy.cache_handler.FlaskSessionCacheHandler(session)
    return SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope=scope,
        cache_handler=cache_handler,
        show_dialog=True
    )


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token_info = get_token()
        if not token_info:
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def get_token():
    try:
        cache_handler = spotipy.cache_handler.FlaskSessionCacheHandler(session)
        auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=SPOTIPY_REDIRECT_URI,
            scope=scope,
            cache_handler=cache_handler
        )
        if not auth_manager.validate_token(cache_handler.get_cached_token()):
            return None
        return cache_handler.get_cached_token()
    except Exception as e:
        logger.error(f"Error getting token: {e}")
        return None


@app.route('/process_voice_command', methods=['POST'])
@login_required
def process_voice_command():
    try:
        # Get the voice command from the frontend
        data = request.json
        command = data.get('command', '')

        # Process the command using our new processor
        command_result = command_processor.process_command(command)

        # Get Spotify client
        token_info = get_token()
        sp = spotipy.Spotify(auth=token_info['access_token'])

        # Get active device
        devices = sp.devices()
        active_device_id = next((device['id'] for device in devices['devices'] if device['is_active']), None)

        if not active_device_id:
            return jsonify({
                'success': False,
                'message': 'No hay dispositivo activo de Spotify'
            }), 400

        # Handle the command based on the action
        if command_result['action'] == 'play_song':
            # Try exact search first
            query = f"track:{command_result['song']} artist:{command_result['artist']}"
            results = sp.search(q=query, type='track', limit=1)

            if not results['tracks']['items']:
                # If exact search fails, try a broader search
                query = f"{command_result['song']} {command_result['artist']}"
                results = sp.search(q=query, type='track', limit=1)

            if results['tracks']['items']:
                track_uri = results['tracks']['items'][0]['uri']
                track_name = results['tracks']['items'][0]['name']
                artist_name = results['tracks']['items'][0]['artists'][0]['name']

                # Queue and play the track
                sp.add_to_queue(device_id=active_device_id, uri=track_uri)
                sp.next_track(device_id=active_device_id)

                return jsonify({
                    'success': True,
                    'message': f"Reproduciendo {track_name} de {artist_name}"
                })

        # Handle basic commands
        elif command_result['action'] == 'pause':
            sp.pause_playback(device_id=active_device_id)
        elif command_result['action'] == 'resume':
            sp.start_playback(device_id=active_device_id)
        elif command_result['action'] == 'next':
            sp.next_track(device_id=active_device_id)
        elif command_result['action'] == 'previous':
            sp.previous_track(device_id=active_device_id)
        elif command_result['action'] == 'volume_up':
            current_playback = sp.current_playback()
            current_volume = current_playback['device']['volume_percent']
            sp.volume(min(current_volume + 10, 100), device_id=active_device_id)
        elif command_result['action'] == 'volume_down':
            current_playback = sp.current_playback()
            current_volume = current_playback['device']['volume_percent']
            sp.volume(max(current_volume - 10, 0), device_id=active_device_id)

        return jsonify({
            'success': True,
            'message': command_result['message']
        })

    except SpotifyException as e:
        logger.error(f"Spotify API error: {e}")
        return jsonify({
            'success': False,
            'message': 'Error al comunicarse con Spotify'
        }), 500
    except Exception as e:
        logger.error(f"Voice command processing error: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    message = None
    track_info = None
    voice_control_active = False

    try:
        token_info = get_token()
        sp = spotipy.Spotify(auth=token_info['access_token'])

        # Get current user info for verification
        current_user = sp.current_user()
        logger.info(f"Current user: {current_user['id']}")

        # Get the list of available devices
        devices = sp.devices()
        active_device_id = next((device['id'] for device in devices['devices'] if device['is_active']), None)

        if not active_device_id:
            message = "No active device found. Please activate a device on your Spotify account and try again."

    except SpotifyOauthError as eAuth:
        logger.error(f"Spotify OAuth error: {eAuth}")
        return redirect(url_for('login'))
    except SpotifyException as SpException:
        logger.error(f"Spotify API error: {SpException}")
        message = "There was a problem with the Spotify API. Please try again later."
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        message = "An unexpected error occurred. Please try again later."

    return render_template('index.html',
                           track_info=track_info,
                           message=message,
                           logged_in=True,
                           voice_control_active=voice_control_active)


@app.route('/callback')
def callback():
    try:
        cache_handler = spotipy.cache_handler.FlaskSessionCacheHandler(session)
        auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=SPOTIPY_REDIRECT_URI,
            scope=scope,
            cache_handler=cache_handler
        )

        code = request.args.get('code')
        token_info = auth_manager.get_access_token(code)

        # Create a Spotify client and get user info
        sp = spotipy.Spotify(auth=token_info['access_token'])
        user = sp.current_user()
        logger.info(f"Logged in as: {user['display_name']} ({user['id']})")

        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error in callback: {e}")
        return redirect(url_for('login'))


@app.route('/login')
def login():
    auth_manager = create_spotify_oauth()
    auth_url = auth_manager.get_authorize_url()
    return redirect(auth_url)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
