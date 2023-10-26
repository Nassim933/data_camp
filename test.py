import requests
from bs4 import BeautifulSoup
import csv
import pickle
import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import pandas as pd
import numpy as np

# Variables globales pour Genius API
base_url = 'http://api.genius.com'
headers = {'Authorization': 'Bearer WiTs2yqMoTLZvThLCzBLov2jIuxjxjHC1h7dY31Cw1hTGgwVIm04CG38VBJGEgv0'}

# Variables globales pour Spotify API
CLIENT_ID = "9120adce768e4a4399b7730b043f9834"
CLIENT_SECRET = "4127b24fc5b3444ba4d04c64df84f3f2"

def lyrics_from_song_api_path(song_api_path):
    song_url = base_url + song_api_path
    response = requests.get(song_url, headers=headers)
    json = response.json()
    path = json['response']['song']['path']
    page_url = 'http://genius.com' + path
    page = requests.get(page_url)
    html = BeautifulSoup(page.text, 'html.parser')
    lyrics = ''
    lyrics_divs = html.find_all('div', class_='Lyrics__Container-sc-1ynbvzw-1 kUgSbL')
    for div in lyrics_divs:
        lyrics += div.get_text()
    return lyrics

def get_lyrics_for_songs(songs, output_file):
    with open(output_file, "w", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["artist", "song", "text"])
        for song in songs:
            artist_name, song_title = song.split('-')
            artist_name = artist_name.strip()
            song_title = song_title.strip()
            search_url = base_url + '/search'
            data = {'q': song_title}
            response = requests.get(search_url, params=data, headers=headers)
            json = response.json()
            song_info = None
            for hit in json['response']['hits']:
                if hit['result']['primary_artist']['name'] == artist_name:
                    song_info = hit
                    break
            if song_info:
                song_api_path = song_info['result']['api_path']
                lyrics = lyrics_from_song_api_path(song_api_path)
                if lyrics:
                    writer.writerow([artist_name, song_title, lyrics])

# Initialisation du client Spotify
client_credentials_manager = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

def get_song_album_cover_url(song_song, artist_song):
    search_query = f"track:{song_song} artist:{artist_song}"
    results = sp.search(q=search_query, type="track")
    if results and results["tracks"]["items"]:
        track = results["tracks"]["items"][0]
        album_cover_url = track["album"]["images"][0]["url"]
        return album_cover_url
    else:
        return "https://i.postimg.cc/0QNxYz4V/social.png"


def recommend(playlist, limit=50):
    recommended_music_songs = []
    recommended_music_posters = []

    for song in playlist:
        song_song, artist_song = song.split(" - ")
        index = music[(music['song'] == song_song) & (music['artist'] == artist_song)].index[0]
        distances = sorted(list(enumerate(similarity[index])), reverse=True, key=lambda x: x[1])

        for i in distances[1:6]:
            if len(recommended_music_songs) < limit:
                artist = music.iloc[i[0]].artist
                recommended_music_posters.append(get_song_album_cover_url(music.iloc[i[0]].song, artist))
                recommended_music_songs.append(music.iloc[i[0]].song)
            else:
                break

    return recommended_music_songs, recommended_music_posters



st.header('Music Recommender System')

music = pickle.load(open('df.pkl', 'rb'))
similarity = pickle.load(open('similarity.pkl', 'rb'))


# Option pour créer une playlist ou importer depuis un CSV
playlist_option = st.radio("Choose a playlist option", ("Create a Playlist", "Import from TXT"))

if playlist_option == "Create a Playlist":
    music = pickle.load(open('df.pkl','rb'))
    similarity = pickle.load(open('similarity.pkl','rb'))

    music_list = [f"{music['song'].iloc[i]} - {music['artist'].iloc[i]}" for i in range(len(music))]
    selected_playlist = st.multiselect(
        "Type or select songs to create a playlist",
        music_list
    )

    if st.button('Show Recommendation'):
        if len(selected_playlist) > 0:
            recommended_music_songs, recommended_music_posters = recommend(selected_playlist, limit=50)
            num_recommendations = len(recommended_music_songs)

            num_cols = 5
            num_rows = num_recommendations // num_cols
            if num_recommendations % num_cols != 0:
                num_rows += 1

            for row in range(num_rows):
                cols = st.columns(num_cols)
                for col in cols:
                    if recommended_music_songs:
                        col.text(recommended_music_songs.pop(0))
                        col.image(recommended_music_posters.pop(0))
        else:
            st.warning("Please select songs to create a playlist.")
else:
    uploaded_file = st.file_uploader("Upload a TXT file with your playlist", type=["txt"])
    if uploaded_file is not None:
        songs = uploaded_file.read().decode("utf-8").splitlines()
        get_lyrics_for_songs(songs, 'playlist.csv')
        df = pd.read_csv('playlist.csv')
        if 'song' in df and 'artist' in df:
            imported_playlist = [f"{row['song']} - {row['artist']}" for _, row in df.iterrows()]
            st.write("Imported Playlist:")

            # Define a simplified music DataFrame from the imported playlist
            music = df[['song', 'artist']]  # You can add more columns as needed

            # Define similarity for the imported data
            # You can calculate or load similarity as per your data
            # Here, we initialize it as a random placeholder
            num_songs = len(music)
            similarity = np.random.rand(num_songs, num_songs)  # Replace with actual similarity calculation

            if st.button('Show Recommendation'):
                recommended_music_songs, recommended_music_posters = recommend(imported_playlist)
                num_recommendations = len(recommended_music_songs)

                num_cols = 5
                num_rows = num_recommendations // num_cols
                if num_recommendations % num_cols != 0:
                    num_rows += 1

                for row in range(num_rows):
                    cols = st.columns(num_cols)
                    for col in cols:
                        if recommended_music_songs:
                            col.text(recommended_music_songs.pop(0))
                            col.image(recommended_music_posters.pop(0))
        else:
            st.warning("The CSV file should have 'song' and 'artist' columns.")
