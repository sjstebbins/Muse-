from flask import Flask, request, redirect, g, render_template, jsonify
import json
import requests
import random
import base64
import urllib
import os
import pprint
from itertools import *
from sklearn.neighbors import DistanceMetric
#Itunes
from pyItunes import *
#Youtube
from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.tools import argparser
# firebase
import pyrebase

GLOBAL = {
    'authorization_header': None,
    'avatar': None,
    'spotify_playlists_ids': [],
    'spotify_playlists_names': [],
    'iTunes_library': None,
    'iTunes_playlists': []
}

config = {
    'apiKey': "AIzaSyC0snFo1RTSYg_OEaJ-373bOdQoDQSv3pg",
    'authDomain': "muse-d2516.firebaseapp.com",
    'databaseURL': "https://muse-d2516.firebaseio.com",
    'storageBucket': "muse-d2516.appspot.com"
}
firebase = pyrebase.initialize_app(config)
db = firebase.database()

# Set home directory based on logged in user
homedir = os.environ['HOME']
local_username = homedir.rsplit('/', 1)[-1]

# Authentication Steps, paramaters, and responses are defined at https://developer.spotify.com/web-api/authorization-guide/
# Visit this url to see all the steps, parameters, and expected response.

app = Flask(__name__)

#  Client Keys
CLIENT_ID = "efe1eb24d4144c85820e486aac3dfe6d"
CLIENT_SECRET = "fc0d5b90374e49a4bb9de5f9a6e3abdc"

# Spotify URLS
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com"
API_VERSION = "v1"
SPOTIFY_API_URL = "{}/{}".format(SPOTIFY_API_BASE_URL, API_VERSION)


# Server-side Parameters
CLIENT_SIDE_URL = "http://127.0.0.1"
PORT = 8080
REDIRECT_URI = "{}:{}/callback/q".format(CLIENT_SIDE_URL, PORT)
SCOPE = "playlist-modify-public playlist-modify-private playlist-read-private"
STATE = ""
SHOW_DIALOG_bool = True
SHOW_DIALOG_str = str(SHOW_DIALOG_bool).lower()


auth_query_parameters = {
    "response_type": "code",
    "redirect_uri": REDIRECT_URI,
    "scope": SCOPE,
    "client_id": CLIENT_ID
}

@app.route("/")
def index():
    return render_template("landing.html")

# @app.route('/foo', methods=['GET', 'POST])
# def foo():
#     return 'HELLO'
@app.route("/authorize", methods=['GET', 'POST'])
def authorize():
    url_args = "&".join(["{}={}".format(key,urllib.quote(val)) for key,val in auth_query_parameters.iteritems()])
    auth_url = "{}/?{}".format(SPOTIFY_AUTH_URL, url_args)
    # add itunes playlists
    if os.path.exists("/Users/" + local_username + "/Music/iTunes/iTunes Music Library.xml"):
        GLOBAL['iTunes_library'] = Library("/Users/" + local_username + "/Music/iTunes/iTunes Music Library.xml")
        GLOBAL['iTunes_playlists'] = GLOBAL['iTunes_library'].getPlaylistNames()[2:len(GLOBAL['iTunes_library'].getPlaylistNames())]

    # Get a reference to the auth service
    # email = request.args.get('email', 0, type=str)
    # password = request.args.get('password', 0, type=str)
    # print email, password
    auth = firebase.auth()

    # auth.create_user_with_email_and_password('sjfstebbins@gmail.com', 'testing')
    GLOBAL['user'] = auth.sign_in_with_email_and_password('sjfstebbins@gmail.com', 'testing')

    # firebaseUser = auth.sign_in_with_email_and_password('sjfstebbins@gmail.com', 'test')
    #
    # # Get a reference to the database service
    # db = firebase.database()
    # data = {
    #     "name": "Mortimer 'Morty' Smith"
    # }
    # results = db.child("users").child("Morty").update(data, firebaseUser['idToken'])
    return redirect(auth_url)

@app.route("/itunes")
def add_library():
    return

@app.route("/callback/q")
def callback():
    # Auth Step 4: Requests refresh and access tokens
    auth_token = request.args['code']
    code_payload = {
        "grant_type": "authorization_code",
        "code": str(auth_token),
        "redirect_uri": REDIRECT_URI
    }
    base64encoded = base64.b64encode("{}:{}".format(CLIENT_ID, CLIENT_SECRET))
    headers = {"Authorization": "Basic {}".format(base64encoded)}
    post_request = requests.post(SPOTIFY_TOKEN_URL, data=code_payload, headers=headers)

    # Auth Step 5: Tokens are Returned to Application
    response_data = json.loads(post_request.text)
    access_token = response_data["access_token"]
    refresh_token = response_data["refresh_token"]
    token_type = response_data["token_type"]
    expires_in = response_data["expires_in"]

    # Auth Step 6: Use the access token to access Spotify API
    GLOBAL['authorization_header'] = {"Authorization":"Bearer {}".format(access_token)}

    # Get profile data
    user_profile_api_endpoint = "{}/me".format(SPOTIFY_API_URL)
    profile_response = requests.get(user_profile_api_endpoint, headers=GLOBAL['authorization_header'])
    profile_data = json.loads(profile_response.text)
    GLOBAL['avatar'] = profile_data['images'][0]['url']

    # Get a reference to the database service
    data = {
        "name": profile_data['display_name']
    }
    db.child("users").child(profile_data['display_name']).update(data, GLOBAL['user']['idToken'])

    # Get spotify playlists
    playlist_api_endpoint = "{}/playlists".format(profile_data["href"])
    playlists_response = requests.get(playlist_api_endpoint, headers=GLOBAL['authorization_header'])
    playlists_data = json.loads(playlists_response.text)

    for playlist in playlists_data['items']:
        GLOBAL['spotify_playlists_names'].append(playlist['name'])
        GLOBAL['spotify_playlists_ids'].append(playlist['id'])

    return redirect("/home")

@app.route("/home")
def home():
    return render_template("index.html",
                            avatar=GLOBAL['avatar'],
                            itunes_playlists=enumerate(GLOBAL['iTunes_playlists']),
                            spotify_playlists=enumerate(GLOBAL['spotify_playlists_names']))
@app.route("/get_playlist")
def get_playlist():

    # MUSE Algo
    seed_data = {
        'titles': [],
        'artists': [],
        'artist_ids': [],
        'play_counts':[],
        'song_ids': [],
        'track_genres': [],
        'attributes': [],
        'images': [],
        'distances': []
    }

    def getSong (track, new):
        if track != 0:
            if new:
                artist = "%20artist:" + urllib.quote(track['artist'] or '').encode()
                song = urllib.quote(track['name'] or '').encode()
                plays = 1
            else:
                artist = "%20artist:" + urllib.quote(track.artist or '').encode()
                song = urllib.quote(track.name  or '').encode()
                plays = track.play_count
            # spotifySearch(song,artist,track.play_count)
            track_api_endpoint = SPOTIFY_API_URL  + "/search?q=" + song + artist + "&type=track&limit=1"
            track_response = requests.get(track_api_endpoint, headers=GLOBAL['authorization_header'])
            tracks_data = json.loads(track_response.text)
            # add track data if search for track yielded results
            if len(tracks_data['tracks']['items']) > 0:
                # append to song_ids
                track_id = tracks_data['tracks']['items'][0]['id']
                seed_data['song_ids'].append(track_id)
                # append to titles
                track_title = tracks_data['tracks']['items'][0]['name']
                seed_data['titles'].append(track_title)
                # append to artist_ids
                track_artist = tracks_data['tracks']['items'][0]['artists'][0]['id']
                seed_data['artist_ids'].append(track_artist)
                # append to artist_ids
                track_artist = tracks_data['tracks']['items'][0]['artists'][0]['name']
                seed_data['artists'].append(track_artist)
                # append to play_counts
                if plays:
                    seed_data['play_counts'].append(plays)
                else:
                    seed_data['play_counts'].append(1)
                # append images
                seed_data['images'].append(tracks_data['tracks']['items'][0]['album']['images'][0]['url'])

    # if making request for billboard playlist
    if request.args.get('day', None, type=str) != None:
        from selenium import webdriver
        from selenium.webdriver.common.keys import Keys
        driver = webdriver.Chrome(executable_path="./chromedriver")
        driver.get("http://www.umdmusic.com/default.asp?Chart=D")
        #click earnings calendar button
        elem = driver.find_element_by_name('ChDay')
        elem.clear()
        elem.send_keys(request.args.get('day', 0, type=str))
        elem = driver.find_element_by_name('ChMonth')
        elem.clear()
        elem.send_keys(request.args.get('month', 0, type=str))
        elem = driver.find_element_by_name('ChYear')
        elem.clear()
        elem.send_keys(request.args.get('year', 0, type=str))
        driver.find_element_by_name('charts').submit()
        # driver.find_element_by_css_selector('archive-search__input').click()
        rows = driver.find_elements_by_tag_name('tr');
        rows_data = []
        for row in rows[15:40]:
            cells = row.find_elements_by_tag_name('td')
            artist = cells[4].get_attribute("innerHTML").split("</b>")[0].split('<b>')[1].rstrip()
            title =  cells[4].get_attribute("innerHTML").split("<br>")[1].rstrip()
            plays = int(cells[3].get_attribute("innerHTML").strip())
            rows_data.append([artist,title,plays])
        playlist = rows_data

        # extract playlist track data
        for track in playlist:
            getSong(track, False)


        # close browser
        driver.quit()

    # if making request for itunes playlist
    else:
        playlist = request.args.get('playlist', 0, type=int)

         # extract playlist track data
        for track in GLOBAL['iTunes_library'].getPlaylist(GLOBAL['iTunes_playlists'][playlist]).tracks:
            getSong(track, False)

    # if adding a new song to the playlist
    track = {}
    if request.args.get('title', 0, type=str) != 'None':
        track['name'] = request.args.get('title', 0, type=str)
        track['artist'] = request.args.get('artist', 0, type=str)
    print track
    if track['name']:
        getSong(track, True)


    # API: get collected song attributes
    attributes_api_endpoint = SPOTIFY_API_URL  + "/audio-features?ids=" + ",".join(seed_data['song_ids'])
    attributes_response = requests.get(attributes_api_endpoint, headers=GLOBAL['authorization_header'])
    seed_data['attributes'] = json.loads(attributes_response.text)['audio_features']

    # multiply songs node based on play_counts to weight songs played more
    library_tracks = []
    for i,attributes in enumerate(seed_data['attributes']):
        library_tracks.extend(repeat(attributes, seed_data['play_counts'][i]))

    # create phantom_average_track
    phantom_average_track = {}
    target_attributes = ['energy','liveness','tempo','speechiness','acousticness','instrumentalness','danceability','loudness']
    for attribute in target_attributes:
        phantom_average_track[attribute] = sum(track[attribute] for track in library_tracks) / len(library_tracks)

    # create tracks with just the float variables
    playlist_tracks_attributes = []
    for track in seed_data['attributes']:
        track_float_values = {}
        for attribute in target_attributes:
            track_float_values[attribute] = track[attribute]
        playlist_tracks_attributes.append(track_float_values.values())

    # get seed_distances from phantom_average_track
    seed_distances = [phantom_average_track.values()] + playlist_tracks_attributes
    dist = DistanceMetric.get_metric('euclidean')
    distances = dist.pairwise(seed_distances)[0]
    seed_data['distances'] = distances[1:len(distances)]

    # get attributes of the 5 closest tracks to the phantom_average_track
    seed_indexes = seed_data['distances'].argsort()[:5]
    seed_songs = [seed_data['song_ids'][i] for i in seed_indexes]
    seed_artists = [seed_data['artist_ids'][i] for i in seed_indexes]

    # get target attributes from phantom_average_track (roudn to two decimals)
    target_energy = str(round(phantom_average_track['energy'],2))
    target_liveness = str(round(phantom_average_track['liveness'],2))
    target_tempo = str(round(phantom_average_track['tempo'],2))
    target_speechiness = str(round(phantom_average_track['speechiness'],2))
    target_acousticness = str(round(phantom_average_track['acousticness'],2))
    target_instrumentalness = str(round(phantom_average_track['instrumentalness'],2))
    target_danceability = str(round(phantom_average_track['danceability'],2))
    target_loudness = str(round(phantom_average_track['loudness'],2))

    # sort recommendation_data object based on recommendation_data distances
    sorted_seed_indexes = seed_data['distances'].argsort()[:len(seed_data['distances'])]
    for key in seed_data.keys():
        if seed_data[key] != []:
            seed_data[key] = [seed_data[key][i] for i in sorted_seed_indexes]

    tracks = []
    for i, title in enumerate(seed_data['titles']):
        tracks.append([
            seed_data['artists'][i],
            title,
            str(round((100 -  seed_data['distances'][i]), 2)) + '%',
            seed_data['images'][i]
        ])
    #-----------------------------------------------------------
    # Pick best recommended song
    #------------------------------------------------------------

    recommendation_data = {
        'data': [],
        'titles': [],
        'artists': [],
        'images': [],
        'ids': [],
        'attributes': [],
        'distances': []
    }

    # API: get recommended tracks data based on seed and target values
    recommendations_api_endpoint = SPOTIFY_API_URL  + "/recommendations?seed_artists=" + ",".join(seed_artists) + "&target_energy=" + target_energy + "&target_liveness=" + target_liveness + "&target_tempo=" + target_tempo + "&target_speechiness=" + target_speechiness + "&target_acousticness=" + target_acousticness + "&target_instrumentalness=" + target_instrumentalness + "&target_danceability=" + target_danceability + "&target_loudness=" + target_loudness + "&limit=20"
    recommendations_response = requests.get(recommendations_api_endpoint, headers=GLOBAL['authorization_header'])
    recommendation_data['data'] = json.loads(recommendations_response.text)['tracks']

    # set recommended track title and ids
    for track in recommendation_data['data']:
        # Dont add duplicate recommendations or songs already in your playlist
        if track['id'] not in recommendation_data['ids'] and track['id'] not in seed_data['song_ids']:
            recommendation_data['titles'].append(track['name'])
            recommendation_data['artists'].append(track['artists'][0]['name'])
            recommendation_data['ids'].append(track['id'])
            recommendation_data['images'].append(track['album']['images'][0]['url'])

    # API: get collected tracks attributes
    attributes_api_endpoint = SPOTIFY_API_URL  + "/audio-features?ids=" + ",".join(recommendation_data['ids'])
    attributes_response = requests.get(attributes_api_endpoint, headers=GLOBAL['authorization_header'])
    recommendation_data['attributes'] = json.loads(attributes_response.text)['audio_features']

    # create tracks with just the float variables
    recommendation_track_attributes = []
    for track in recommendation_data['attributes']:
        track_float_values = {}
        for attribute in target_attributes:
            track_float_values[attribute] = track[attribute]
        recommendation_track_attributes.append(track_float_values.values())

    # get recommendation_distances from phantom_average_track
    recommendation_distances = [phantom_average_track.values()] + recommendation_track_attributes
    dist = DistanceMetric.get_metric('euclidean')
    distances = dist.pairwise(recommendation_distances)[0]
    recommendation_data['distances'] = distances[1:len(distances)]

    # sort recommendation_data object based on recommendation_data distances
    sorted_recommendation_indexes = recommendation_data['distances'].argsort()[:len(recommendation_data['distances'])]
    for key in recommendation_data.keys():
        if recommendation_data[key] != []:
            recommendation_data[key] = [recommendation_data[key][i] for i in sorted_recommendation_indexes]

    # combine reommendation data into list
    recommendations = []
    # totalDistance = sum(recommendation_data['distances'])
    for i, title in enumerate(recommendation_data['titles']):
        recommendations.append([
            recommendation_data['artists'][i],
            title,
            str(round((100 -  recommendation_data['distances'][i]), 2)) + '%',
            recommendation_data['images'][i]
        ])

    return jsonify(tracks=tracks,recommendations=recommendations)

@app.route("/auto_generate")
def auto_generate():
    seed_data = {
        'titles': [],
        'artists': [],
        'artist_ids': [],
        'play_counts':[],
        'song_ids': [],
        'track_genres': [],
        'attributes': [],
        'images': [],
        'distances': []
    }
    playlist = request.args.get('playlist', 0, type=int)

    # extract playlist track data
    for track in GLOBAL['iTunes_library'].getPlaylist(GLOBAL['iTunes_playlists'][playlist]).tracks:
        artist = "%20artist:" + urllib.quote(track.artist).encode() if track.artist else ''
        song = urllib.quote(track.name).encode() or ''
        plays = track.play_count
        # spotifySearch(song,artist,track.play_count)
        track_api_endpoint = SPOTIFY_API_URL  + "/search?q=" + song + artist + "&type=track&limit=1"
        track_response = requests.get(track_api_endpoint, headers=GLOBAL['authorization_header'])
        tracks_data = json.loads(track_response.text)
        # add track data if search for track yielded results
        if len(tracks_data['tracks']['items']) > 0:
            # append to song_ids
            track_id = tracks_data['tracks']['items'][0]['id']
            seed_data['song_ids'].append(track_id)
            # append to titles
            track_title = tracks_data['tracks']['items'][0]['name']
            seed_data['titles'].append(track_title)
            # append to artist_ids
            track_artist = tracks_data['tracks']['items'][0]['artists'][0]['id']
            seed_data['artist_ids'].append(track_artist)
            # append to artist_ids
            track_artist = tracks_data['tracks']['items'][0]['artists'][0]['name']
            seed_data['artists'].append(track_artist)
            # append to play_counts
            if plays:
                seed_data['play_counts'].append(plays)
            else:
                seed_data['play_counts'].append(1)
            # append images
            seed_data['images'].append(tracks_data['tracks']['items'][0]['album']['images'][0]['url'])
    # API: get collected tracks attributes
    attributes_api_endpoint = SPOTIFY_API_URL  + "/audio-features?ids=" + ",".join(seed_data['song_ids'])
    attributes_response = requests.get(attributes_api_endpoint, headers=GLOBAL['authorization_header'])
    seed_data['attributes'] = json.loads(attributes_response.text)['audio_features']


    # SPOTIFY PLAYLISTS
    # # Get user playlist data
    # playlist_api_endpoint = "{}/playlists".format(profile_data["href"]) + '/08hZj3VHb1C0uJE1gcZ4Cg'
    # playlists_response = requests.get(playlist_api_endpoint, headers=GLOBAL['authorization_header'])
    # playlist_data = json.loads(playlists_response.text)
    #
    # # Get song attributes of all songs in a user's playlist
    # ## work on getting better results sent back
    # playlist_tracks = playlist_data["tracks"]["items"]
    # song_ids = []
    # track_names = []
    # for track in playlist_tracks:
    #     artist = track['track']['artists'][0]['name'].lower() or ''
    #     song = track['track']['name'].lower() or ''


    def recurs(seed_data,i,max):
        # API: get collected tracks attributes
        attributes_api_endpoint = SPOTIFY_API_URL  + "/audio-features?ids=" + ",".join(seed_data['song_ids'])
        attributes_response = requests.get(attributes_api_endpoint, headers=GLOBAL['authorization_header'])
        seed_data['attributes'] = json.loads(attributes_response.text)['audio_features']
        # multiply songs node based on play_counts to weight songs played more
        library_tracks = []
        for i,attributes in enumerate(seed_data['attributes']):
            library_tracks.extend(repeat(attributes, seed_data['play_counts'][i]))

        ##PERFORM PCA TO REDUCE DIMENSIONALITY?

        # create phantom_average_track
        phantom_average_track = {}
        target_attributes = ['energy','liveness','tempo','speechiness','acousticness','instrumentalness','danceability','loudness']
        for attribute in target_attributes:
            phantom_average_track[attribute] = sum(track[attribute] for track in library_tracks) / len(library_tracks)

        # create tracks with just the float variables
        playlist_tracks_attributes = []
        for track in seed_data['attributes']:
            track_float_values = {}
            for attribute in target_attributes:
                track_float_values[attribute] = track[attribute]
            playlist_tracks_attributes.append(track_float_values.values())

        # get seed_distances from phantom_average_track
        seed_distances = [phantom_average_track.values()] + playlist_tracks_attributes
        dist = DistanceMetric.get_metric('euclidean')
        distances = dist.pairwise(seed_distances)[0]
        seed_data['distances'] = distances[1:len(distances)]

        # get attributes of the 5 closest tracks to the phantom_average_track
        seed_indexes = seed_data['distances'].argsort()[:5]
        seed_songs = [seed_data['song_ids'][i] for i in seed_indexes]
        seed_artists = [seed_data['artist_ids'][i] for i in seed_indexes]

        # get target attributes from phantom_average_track (roudn to two decimals)
        target_energy = str(round(phantom_average_track['energy'],2))
        target_liveness = str(round(phantom_average_track['liveness'],2))
        target_tempo = str(round(phantom_average_track['tempo'],2))
        target_speechiness = str(round(phantom_average_track['speechiness'],2))
        target_acousticness = str(round(phantom_average_track['acousticness'],2))
        target_instrumentalness = str(round(phantom_average_track['instrumentalness'],2))
        target_danceability = str(round(phantom_average_track['danceability'],2))
        target_loudness = str(round(phantom_average_track['loudness'],2))

        # sort recommendation_data object based on recommendation_data distances
        sorted_seed_indexes = seed_data['distances'].argsort()[:len(seed_data['distances'])]
        for key in seed_data.keys():
            if seed_data[key] != []:
                seed_data[key] = [seed_data[key][i] for i in sorted_seed_indexes]

        tracks = []
        for i, title in enumerate(seed_data['titles']):
            tracks.append([
                seed_data['artists'][i],
                title,
                str(round((100 -  seed_data['distances'][i]), 2)) + '%',
                seed_data['images'][i]
            ])
        #-----------------------------------------------------------
        # Pick best recommended song
        #------------------------------------------------------------

        recommendation_data = {
            'data': [],
            'titles': [],
            'artists': [],
            'artist_ids': [],
            'images': [],
            'ids': [],
            'attributes': [],
            'distances': []
        }
        # API: get recommended tracks data based on seed and target values
        recommendations_api_endpoint = SPOTIFY_API_URL  + "/recommendations?seed_artists=" + ",".join(seed_artists) + "&target_energy=" + target_energy + "&target_liveness=" + target_liveness + "&target_tempo=" + target_tempo + "&target_speechiness=" + target_speechiness + "&target_acousticness=" + target_acousticness + "&target_instrumentalness=" + target_instrumentalness + "&target_danceability=" + target_danceability + "&target_loudness=" + target_loudness + "&limit=1"
        recommendations_response = requests.get(recommendations_api_endpoint, headers=GLOBAL['authorization_header'])
        recommendation_data['data'] = json.loads(recommendations_response.text)['tracks']

        # set recommended track title and ids
        for track in recommendation_data['data']:
            # Dont add duplicate recommendations or songs already in your playlist
            if track['id'] not in recommendation_data['ids'] and track['id'] not in seed_data['song_ids']:
                recommendation_data['titles'].append(track['name'])
                recommendation_data['artists'].append(track['artists'][0]['name'])
                recommendation_data['artist_ids'].append(track['artists'][0]['id'])
                recommendation_data['ids'].append(track['id'])
                recommendation_data['images'].append(track['album']['images'][0]['url'])

        # API: get collected tracks attributes
        attributes_api_endpoint = SPOTIFY_API_URL  + "/audio-features?ids=" + ",".join(recommendation_data['ids'])
        attributes_response = requests.get(attributes_api_endpoint, headers=GLOBAL['authorization_header'])
        recommendation_data['attributes'] = json.loads(attributes_response.text)['audio_features']

        # create tracks with just the float variables
        recommendation_track_attributes = []
        for track in recommendation_data['attributes']:
            track_float_values = {}
            for attribute in target_attributes:
                track_float_values[attribute] = track[attribute]
            recommendation_track_attributes.append(track_float_values.values())

        # get recommendation_distances from phantom_average_track
        recommendation_distances = [phantom_average_track.values()] + recommendation_track_attributes
        dist = DistanceMetric.get_metric('euclidean')
        distances = dist.pairwise(recommendation_distances)[0]
        recommendation_data['distances'] = distances[1:len(distances)]

        # sort recommendation_data object based on recommendation_data distances
        sorted_recommendation_indexes = recommendation_data['distances'].argsort()[:len(recommendation_data['distances'])]
        for key in recommendation_data.keys():
            if recommendation_data[key] != []:
                recommendation_data[key] = [recommendation_data[key][i] for i in sorted_recommendation_indexes]

        # combine reommendation data into list
        recommendations = []
        # totalDistance = sum(recommendation_data['distances'])
        for i, title in enumerate(recommendation_data['titles']):
            recommendations.append([
                recommendation_data['artists'][i],
                title,
                str(round((100 -  recommendation_data['distances'][i]), 2)) + '%',
                recommendation_data['images'][i],
                recommendation_data['ids'][i]
            ])

        # totalDistance = sum(recommendation_data['distances'])
        if i <= max:
            seed_data['titles'].append(recommendation_data['titles'][0])
            seed_data['artists'].append(recommendation_data['artists'][0])
            seed_data['play_counts'].append(1)
            seed_data['attributes'].append(recommendation_data['attributes'][0])
            seed_data['song_ids'].append(recommendation_data['ids'][0])
            seed_data['images'].append(recommendation_data['images'][0])
            seed_data['distances'].append(recommendation_data['distances'][0])
            seed_data['artist_ids'].append(recommendation_data['artist_ids'][0])
            return recurs(seed_data, i+1, max)
        else:
            return jsonify(tracks=tracks,recommendations=recommendations)

    recurs(seed_data,1,request.args.get('max', 0, type=int))

        # #---------------------------------------------------------------
        # # Stats for my playist being better
        # #---------------------------------------------------------------
        # from scipy import stats
        # # perform a two sample ttest of my library track distances from average and my recommend track distances
        # seed_recommend_ttest = stats.ttest_ind(seed_data['distances'],recommendation_data['distances'][0:len(seed_data['distances'])])


@app.route("/get_video")
def get_video():
    #---------------------------------------------------------------
    # API: Youtube API
    #---------------------------------------------------------------
    artist = request.args.get('artist', 0, type=str)
    song = request.args.get('title', 0, type=str)

    # set DEVELOPER_KEY to the API key value from the APIs & auth > Registered apps
    # tab of
    #   https://cloud.google.com/console
    # Please ensure that you have enabled the YouTube Data API for your project.
    YOUTUBE_API_SERVICE_NAME = "youtube"
    YOUTUBE_API_VERSION = "v3"

    def youtube_search(options):
        youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
        developerKey='AIzaSyDZiOlhTzNkk1PyxtUygYfz8BRGrRPSrq4')

        # call the search.list method to retrieve results matching the specified
        # query term.
        search_response = youtube.search().list(
            q=options['q'],
            type="video",
            part="id,snippet",
            maxResults=10
        ).execute()

        search_videos = []

        # merge video ids
        for search_result in search_response.get("items", []):
            search_videos.append(search_result["id"]["videoId"])

        video_ids = search_videos

          # call the videos.list method to retrieve location details for each video.
        video_response = youtube.videos().list(
            id=video_ids,
            part='snippet, recordingDetails'
        ).execute()

        videos = []

        # add each result to the list, and then display the list of matching videos.
        for video_result in video_response.get("items", []):
            videos.append(video_result["snippet"]["title"])
            break;

        return video_ids[0]

    # return the id of the video
    return jsonify(video=str(youtube_search({'q': artist + "," + song})))

if __name__ == "__main__":
    app.run(debug=True,port=PORT)
