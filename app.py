from flask import Flask, redirect, request, session, url_for, render_template, jsonify
from dotenv import load_dotenv
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError
from spotipy import SpotifyException
import logging
from functools import wraps
import threading
import queue


# Load environment variables and setup logging (unchanged)
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", 'supersecretkey')
app.config['SESSION_COOKIE_NAME'] = 'Spotify Auth Session'

# Environment variables
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.getenv("REDIRECT_URI")

scope = 'user-read-private user-read-email user-library-read user-library-modify user-read-playback-state ' \
        'user-modify-playback-state user-read-currently-playing playlist-read-private playlist-read-collaborative ' \
        'playlist-modify-private playlist-modify-public user-follow-read user-follow-modify user-top-read ' \
        'user-read-recently-played app-remote-control streaming'

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

@app.route('/get-spotify-token')
@login_required
def get_spotify_token():
    token_info = get_token()
    if token_info:
        return jsonify({
            'access_token': token_info['access_token']
        })
    return jsonify({'error': 'No token available'}), 401

@app.route('/get-current-playback')
@login_required
def get_current_playback():
    try:
        token_info = get_token()
        sp = spotipy.Spotify(auth=token_info['access_token'])
        current_playback = sp.current_playback()
        return jsonify(current_playback if current_playback else {})
    except Exception as e:
        print(f"Error getting playback: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/process_voice_command', methods=['POST'])
@login_required
def process_voice_command():
    try:
        # Get the voice command from the frontend
        data = request.json
        command = data.get('command', '').lower()

        token_info = get_token()
        sp = spotipy.Spotify(auth=token_info['access_token'])

        # Get active device
        devices = sp.devices()
        active_device_id = next((device['id'] for device in devices['devices'] if device['is_active']), None)

        if not active_device_id:
            return jsonify({
                'success': False,
                'message': 'No active Spotify device found'
            }), 400

        if 'pausa' in command or 'detener' in command:
            sp.pause_playback(device_id=active_device_id)
            return jsonify({'success': True, 'action': 'Pausando...'})

        elif 'reproducir' in command or 'continuar' in command:
            sp.start_playback(device_id=active_device_id)
            return jsonify({'success': True, 'action': 'Continuando la Reproducción'})

        elif 'siguiente' in command or 'saltar' in command:
            sp.next_track(device_id=active_device_id)
            return jsonify({'success': True, 'action': 'Siguiente canción'})

        elif 'anterior' in command or 'atrás' in command:
            sp.previous_track(device_id=active_device_id)
            return jsonify({'success': True, 'action': 'Cancion anterior'})

        elif 'subir volumen' in command:
            current_playback = sp.current_playback()
            current_volume = current_playback['device']['volume_percent']
            sp.volume(min(current_volume + 10, 100), device_id=active_device_id)
            return jsonify({'success': True, 'action': 'Mas Volumen'})

        elif 'bajar volumen' in command:
            current_playback = sp.current_playback()
            current_volume = current_playback['device']['volume_percent']
            sp.volume(max(current_volume - 10, 0), device_id=active_device_id)
            return jsonify({'success': True, 'action': 'Menos Volumen'})

        return jsonify({
            'success': True,
            'message': 'Comando no reconocido...'
        })

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
        else:
            if request.method == 'POST':
                # Check if it's a voice control request
                if 'start_voice_control' in request.form:
                    # Start voice control in a separate thread
                    voice_thread = threading.Thread(
                        target=process_voice_command,
                        args=(sp, active_device_id),
                        daemon=True
                    )
                    voice_thread.start()
                    voice_control_active = True
                    message = "Voice control activated. Start speaking commands!"
                else:
                    # Existing song search functionality
                    song_name = request.form['song_name']
                    results = sp.search(q=song_name, limit=1)
                    if results['tracks']['items']:
                        track = results['tracks']['items'][0]
                        track_info = {
                            'name': track['name'],
                            'artist': track['artists'][0]['name'],
                            'album': track['album']['name'],
                        }
                        sp.add_to_queue(track['id'], device_id=active_device_id)
                        sp.next_track(device_id=active_device_id)
                    else:
                        track_info = {'error': 'Song not found'}
            else:
                playback = sp.current_playback()
                if playback and not playback['is_playing']:
                    sp.start_playback(device_id=active_device_id)

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
