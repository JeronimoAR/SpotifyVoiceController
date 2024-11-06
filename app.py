from flask import Flask, redirect, request, session, url_for, render_template
from dotenv import load_dotenv
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError

load_dotenv()
app = Flask(__name__)
app.secret_key = '19331212'
app.config['SESSION_COOKIE_NAME'] = 'Spotify Auth Session'

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.getenv("REDIRECT_URI")

scope = 'user-read-private user-read-email user-library-read user-library-modify' \
        ' user-read-playback-state user-modify-playback-state user-read-currently-playing playlist-read-private ' \
        'playlist-read-collaborative playlist-modify-private playlist-modify-public user-follow-read ' \
        'user-follow-modify user-top-read user-read-recently-played app-remote-control streaming'


@app.route('/', methods=['GET', 'POST'])
def index():
    if 'token_info' not in session:
        return redirect(url_for('login'))

    token_info = session.get('token_info', None)
    track_info = None
    message = None

    try:
        sp = spotipy.Spotify(auth=token_info['access_token'])

        user = sp.current_user()
        print(user)
        if user['product'] != 'premium':
            message = "This feature is only available for Spotify Premium users. " \
                      "Please upgrade to use this functionality."
        elif(user['product'] == 'premium'):
            message = "Enjoy the use of this app"
            # Get the list of available devices
            devices = sp.devices()
            active_device_id = None

            # Find the active device
            for device in devices['devices']:
                if device['is_active']:
                    active_device_id = device['id']
                    break

            if not active_device_id:
                message = "No active device found. Please start playback on one of your devices first."
            else:
                if request.method == 'POST':
                    validatePlayback(sp.current_playback(), active_device_id, sp)
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
    except SpotifyOauthError as eAuth:
        print(eAuth)
        return redirect(url_for('login'))

    return render_template('index.html', track_info=track_info, message=message)


@app.route('/callback')
def callback():
    sp_oauth = SpotifyOAuth(client_id=client_id,
                            client_secret=client_secret,
                            redirect_uri=SPOTIPY_REDIRECT_URI,
                            scope=scope)
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session['token_info'] = token_info

    return redirect(url_for('index'))


@app.route('/login')
def login():
    sp_oauth = SpotifyOAuth(client_id=client_id,
                            client_secret=client_secret,
                            redirect_uri=SPOTIPY_REDIRECT_URI,
                            scope=scope)
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

def validatePlayback(playback, active_device_id, sp):
    if playback and not playback['is_playing']:
        sp.start_playback(device_id=active_device_id)

if __name__ == '__main__':
    app.run(host='192.168.5.106', port=5000, debug=True)

