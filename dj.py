import time
import requests
import json
import random
import math
import urllib
import vlc
import copy

chart_data_dict = {}
genre_dict = {'country' : 6, 'electronic' : 7, 'pop' : 8, 'dance' : 17, 'rap' : 18, 'rock' : 21}

instance = vlc.Instance()
player = instance.media_player_new()

# updates the track data stored in the dict
for key, val in genre_dict.iteritems():
    chart_data_dict[key] = json.loads(urllib.urlopen('https://itunes.apple.com/us/rss/topsongs/limit=10/genre=' + str(val) + '/json').read())

# clear votes
def clear_vote_count():
    vote_res = requests.get('http://smartclub.herokuapp.com/clearvotes')
    scream_res = requests.get('http://smartclub.herokuapp.com/resetscreamtracker')

# randomly select a new genre
def switch_genre(genre):
    temp_genre_dict = copy.deepcopy(genre_dict)
    temp_genre_dict.pop(genre)
    random_index = int(math.floor(random.random() * len(temp_genre_dict)))
    return play(temp_genre_dict.keys()[random_index])

def update_crowd_feedback():
    vote_res = requests.get('http://smartclub.herokuapp.com/getvotecount')
    scream_res = requests.get('http://smartclub.herokuapp.com/wasthereascream')
    return (json.loads(vote_res.text), scream_res)

def play(genre):
    clear_vote_count()
    top_track_list = chart_data_dict[genre]['feed']['entry']
    random_index = int(math.floor(random.random() * len(top_track_list)))
    song_url = top_track_list[random_index]['link'][1]['attributes']['href']
    media = instance.media_new(song_url)
    player.set_media(media)
    player.play()
    while 1:
        time.sleep(10)
        # after 10 seconds, get request to check upvotes/downvotes and possible noise reaction
        votes, scream_res = update_crowd_feedback()
        if ((votes['upvotes'] > votes['downvotes']) or (scream_res.text == "Yes")):
            # play the rest of the song (20 seconds since its a preview url)
            time.sleep(20)
            votes, scream_res = update_crowd_feedback()
            # if they still like the song play a similar one
            if ((votes['upvotes'] > votes['downvotes']) or (scream_res.text == "Yes")):
                return play(genre)
            else:
                return switch_genre(genre)
        else:
            # if they don't like it, switch to a different song
           return switch_genre(genre)

