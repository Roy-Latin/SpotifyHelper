from flask import Flask, redirect, request, session, url_for, render_template, jsonify
from dotenv import load_dotenv
import urllib.parse
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import time
import logging
import datetime
import requests

#loading secrets
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

#putting secrets in variables
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
redirect_uri = os.getenv("REDIRECT_URI")


AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE_URL = "https://api.spotify.com/v1/"

#first greet page to with link to login into spotify
@app.route('/')
def index():
    return render_template('Greet.html')

#login page to get the user data
@app.route('/login')
def login():
    #takes the wanted premission from the user 
    scope = "user-read-private user-read-email user-library-read playlist-read-private playlist-read-collaborative user-top-read user-read-recently-played"

    #enter the data into the params
    params = {
        'client_id': client_id,
        'response_type': 'code',
        'scope': scope,
        'redirect_uri': redirect_uri,
        'show_dialog': True
    }

    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

    return redirect(auth_url)

@app.route('/callback')
def callback():
    if 'error' in request.args:
        return jsonify({"error": request.args['error']})
    
    if 'code' in request.args:
        req_body = {
            'code': request.args['code'],
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri,
            'client_id': client_id,
            'client_secret': client_secret
        }

        response = requests.post(TOKEN_URL, data=req_body)
        token_info = response.json()

        session['access_token'] = token_info['access_token']
        session['refresh_token'] = token_info['refresh_token']
        session['expires_at'] = datetime.datetime.now().timestamp() + token_info['expires_in']

        return redirect('/home')

@app.route('/refresh-token')
def refresh_token():
    if 'refresh_token' not in session:
        return redirect('/login')

    if datetime.datetime.now().timestamp > session['expires_at']:
        req_body = {
            'grant_type': 'refresh_token',
            'refresh_token': 'refresh_token',
            'client_id': client_id,
            'client_secret': client_secret
        }

        response = request.post(TOKEN_URL, data=req_body)
        new_token_info = response.json()

        session['access_token'] = new_token_info['access_token']
        session['expires_at'] = datetime.datetime.now().timestamp() + new_token_info['expires_in']

        return redirect('/home')
    
@app.route('/home')
def home():
    if 'access_token' not in session:
        return redirect('/login')
    
    if datetime.datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh-token')
    
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }
    # Get the current user's username
    user_info = get_current_user_info(session['access_token'])
    username = user_info.get('display_name', 'Unknown User')

    # Get the current user's top artists
    top_artists = get_user_top_artists(session['access_token'])
    
    # Get the current user's top tracks
    top_tracks = get_user_top_tracks(session['access_token'])

    # Render HTML template and pass the data to it
    return render_template('home.html', username=username, top_artists=top_artists, top_tracks=top_tracks)

def get_saved_tracks(access_token, limit=10):
    response = requests.get(API_BASE_URL + 'me/tracks', headers={'Authorization': f"Bearer {access_token}"})
    tracks = response.json()['items']
    saved_tracks = [{"artist": track['track']['artists'][0]['name'], "name": track['track']['name']} for track in tracks]
    return saved_tracks

def get_user_top_artists(access_token, limit=5):
    response = requests.get(API_BASE_URL + 'me/top/artists', headers={'Authorization': f"Bearer {access_token}"}, params={'limit': limit})
    artists = response.json()['items']
    top_artists = [{
        "name": artist['name'],
        "image": artist['images'][0]['url'] if artist['images'] else None
    } for artist in artists]
    return top_artists


def get_user_top_tracks(access_token, limit=10):
    response = requests.get(API_BASE_URL + 'me/top/tracks', headers={'Authorization': f"Bearer {access_token}"}, params={'limit': limit})
    tracks = response.json()['items']
    top_tracks = [{"artist": track['artists'][0]['name'], "name": track['name']} for track in tracks]
    return top_tracks
    
def get_current_user_info(access_token):
    response = requests.get(API_BASE_URL + 'me', headers={'Authorization': f"Bearer {access_token}"})
    username = response.json()
    return username
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)