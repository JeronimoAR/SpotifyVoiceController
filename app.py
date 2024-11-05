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
    global token_info
    global sp
    track_info = None

    try:
        token_info = session.get('token_info', None)
        if not token_info:
            return redirect(url_for('login'))
    except spotipy.exceptions.SpotifyException as e:
        print(f"Exception: {e}")

    try:
        if request.method == 'POST':

            song_name = request.form['song_name']
            try:
                sp = spotipy.Spotify(auth=token_info['access_token'])
                playback = sp.current_playback()
                if playback and not playback['is_playing']:
                    sp.start_playback()

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
            except spotipy.exceptions.SpotifyException as e:
                print(e)
                track_info = {'error': str(e)}
    except SpotifyOauthError as eAuth:
        print(eAuth)
        return redirect(url_for('/login'))

    return render_template('index.html', track_info=track_info)


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


if __name__ == '__main__':
    app.run(debug=True)
