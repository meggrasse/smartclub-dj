import time
import requests
import json
import pickle
import random
import math
import urllib
import vlc
import sys
from pydub import AudioSegment
import librosa
from dtw import dtw
from numpy.linalg import norm
from sklearn.naive_bayes import GaussianNB
from sklearn.cluster import DBSCAN
import numpy as np
import time

instance = vlc.Instance()
player = instance.media_player_new()

def updatetrackdata():
	chart_data = json.loads(urllib.urlopen('https://itunes.apple.com/us/rss/topsongs/limit=50/json').read())
	audio_info_dict = {}
	track_data = {'returned_chart_data' : {}, 'cluster_data' : {'bass' : [], 'treble' : []}, 'genre_data' : {}}
	track_id_list = []
	X_low_pass = pickle.load(open('low_pass.p', 'rb' ))
	X_high_pass = pickle.load(open('high_pass.p', 'rb' ))
	for ii in range(50):
		track_id = chart_data['feed']['entry'][ii]['id']['attributes']['im:id']
		track_id_list.append(track_id)
		preview_url = chart_data['feed']['entry'][ii]['link'][1]['attributes']['href']
		genre = chart_data['feed']['entry'][ii]['category']['attributes']['im:id']
		track_data['returned_chart_data'][track_id] = {'preview_url' : preview_url, 'genre' : genre, 'bass_cluster' : -1, 'treble_cluster' : -1}
		if genre in track_data['genre_data']:
			track_data['genre_data'][genre].append(track_id)
		else:
			track_data['genre_data'][genre] = [track_id]
		urllib.urlretrieve(preview_url, 'tracks/original/' + str(track_id) + '.m4a')
		song = AudioSegment.from_file('tracks/original/' + str(track_id) + '.m4a')
		#get mfcc of bass and treble
		song.low_pass_filter(250).export('tracks/low-pass/' + str(track_id) + '.m4a')
		song.high_pass_filter(6000).export('tracks/high-pass/' + str(track_id) + '.m4a')
		y_low_pass, sr_low_pass = librosa.load('tracks/low-pass/' + str(track_id) + '.m4a') 
		y_high_pass, sr_high_pass = librosa.load('tracks/high-pass/' + str(track_id) + '.m4a')
		#store mfcc for comparison
		X_low_pass.append(librosa.feature.mfcc(y_low_pass, sr_low_pass).T)
		X_high_pass.append(librosa.feature.mfcc(y_high_pass, sr_high_pass).T)
		#populate returned chart data array by comparing songs
	pickle.dump(X_low_pass, open('low_pass.p', 'wb'))
	pickle.dump(X_high_pass, open('high_pass.p', 'wb'))
	print "finished pickling"

	t0 = time.time()

	db_low_pass = DBSCAN().fit(X_low_pass)
	core_samples_mask = np.zeros_like(db_low_pass.labels_, dtype=bool)
	core_samples_mask[db_low_pass.core_sample_indices_] = True

	db_high_pass = DBSCAN().fit(X_high_pass)
	core_samples_mask = np.zeros_like(db_high_pass.labels_, dtype=bool)
	core_samples_mask[db_high_pass.core_sample_indices_] = True

	t1 = time.time()

	print t1 - t0

	#pickle.dump(track_data, open('track_data.p', 'wb'))
	#return track_data

def get_track_data():
	track_data = pickle.load(open('track_data.p', 'rb' ))
	return track_data

# clear votes
def clear_vote_count():
	vote_res = requests.get('http://smartclub.herokuapp.com/clearvotes')
	scream_res = requests.get('http://smartclub.herokuapp.com/resetscreamtracker')

# select a new track
def select_next_track():
	global not_played
	global y
	# buffer to ensure we have some data before we start making selections
	if sum(y) < -45:
		play_random()
	# otherwise, use the model to make a decision
	else:
		y_ = np.array(y)
		X_np_ = np.array(not_played.values()).astype(np.float)
		model = GaussianNB()
		model.fit(X, y_)
		predicted = model.predict(X_np_)
		to_play = np.where(predicted == 1)[0]
		if len(to_play) > 0:
			track_id_index = to_play[0]
			track_id = not_played.keys()[track_id_index]
			# remove track from list of unplayed tracks
			not_played.pop(track_id, None)
			play(track_id)
		else:
			play_random()

def play_random():
	global not_played
	global y
	random_index = int(math.floor(random.random() * len(not_played.keys())))
	track_id = not_played.keys()[random_index]
	# remove track from list of unplayed tracks
	not_played.pop(track_id, None)
	play(track_id)

def update_crowd_feedback():
	vote_res = requests.get('http://smartclub.herokuapp.com/getvotecount')
	scream_res = requests.get('http://smartclub.herokuapp.com/wasthereascream')
	return (json.loads(vote_res.text), scream_res)

def play(track_id):
	global not_played
	global y
	clear_vote_count()
	song_url = track_data['returned_chart_data'][track_id]['preview_url']
	media = instance.media_new(song_url)
	player.set_media(media)
	player.play()
	while 1:
		time.sleep(10)
		index = track_data['returned_chart_data'].keys().index(track_id)
		# after 10 seconds, get request to check upvotes/downvotes and possible noise reaction
		votes, scream_res = update_crowd_feedback()
		if ((votes['upvotes'] > votes['downvotes']) or (scream_res.text == "Yes")):
			# they like it at first -- play the rest of the song (20 seconds since its a preview url)
			time.sleep(20)
			votes, scream_res = update_crowd_feedback()
			# they still like the song -- log that they like it & play a similar one
			if ((votes['upvotes'] > votes['downvotes']) or (scream_res.text == "Yes")):
				y[index] = 1
			# log that they don't like it anymore
			else:
				y[index] = 0
		# log that they don't like it
		else:
			y[index] = 0
		return select_next_track()

# let's get started
if len(sys.argv) > 1 and sys.argv[1] == 'update':
	track_data = updatetrackdata()
else:
	track_data = get_track_data()
# init classification vectors
X = []
for id in track_data['returned_chart_data'].keys():
	X.append([track_data['returned_chart_data'][id]['genre'], track_data['returned_chart_data'][id]['bass_cluster'], track_data['returned_chart_data'][id]['treble_cluster']])
y = [-1] * 50
# keep track of the tracks that haven't played yet
not_played = {}
for i in range(50):
	not_played[track_data['returned_chart_data'].keys()[i]] = X[i]
X = np.array(X).astype(np.float)
# start with a random track
random_index = int(math.floor(random.random() * len(track_data['returned_chart_data'].keys())))
play(track_data['returned_chart_data'].keys()[random_index])


