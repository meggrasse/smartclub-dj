import time
import requests
import json
import pickle
import random
import math
import urllib
import vlc
import copy
import sys
from pydub import AudioSegment
import librosa
from dtw import dtw
from numpy.linalg import norm
from sklearn.naive_bayes import GaussianNB
import numpy as np

track_data = {}
cluster_data = {'bass': [], 'treble':[]}

instance = vlc.Instance()
player = instance.media_player_new()

# arrays for classification
X = [[]]
y = []

def updatetrackdata():
	chart_data = json.loads(urllib.urlopen('https://itunes.apple.com/us/rss/topsongs/limit=50/json').read())
	returned_chart_data = {}
	audio_info_dict = {}
	genre_data = {}
	track_id_list = []
	for ii in range(50):
		track_id = chart_data['feed']['entry'][ii]['id']['attributes']['im:id']
		track_id_list.append(track_id)
		preview_url = chart_data['feed']['entry'][ii]['link'][1]['attributes']['href']
		genre = chart_data['feed']['entry'][ii]['category']['attributes']['im:id']
		returned_chart_data[track_id] = {'preview_url' : preview_url, 'genre' : genre, 'bass_cluster' : -1, 'treble_cluster' : -1}
		if genre in genre_data:
			genre_data[genre].append(track_id)
		else:
			genre_data[genre] = [track_id]
		urllib.urlretrieve(preview_url, 'tracks/original/' + str(track_id) + '.m4a')
		song = AudioSegment.from_file('tracks/original/' + str(track_id) + '.m4a')
		#get mfcc of bass and treble
		song.low_pass_filter(250).export('tracks/low-pass/' + str(track_id) + '.m4a')
		song.high_pass_filter(6000).export('tracks/high-pass/' + str(track_id) + '.m4a')
		y_low_pass, sr_low_pass = librosa.load('tracks/low-pass/' + str(track_id) + '.m4a') 
		y_high_pass, sr_high_pass = librosa.load('tracks/high-pass/' + str(track_id) + '.m4a')
		#store mfcc for comparison
		audio_info_dict[str(track_id) + '_low_pass'] = librosa.feature.mfcc(y_low_pass, sr_low_pass).T
		audio_info_dict[str(track_id) + '_high_pass'] = librosa.feature.mfcc(y_high_pass, sr_high_pass).T
		#to track what value distance should be
		dist_lp_list = []
		dist_hp_list = []
	#populate returned chart data array by comparing songs
	for jj in range(50):
		for kk in range(50):
			if jj > kk:
				x = audio_info_dict[str(track_id_list[jj]) + '_low_pass'].reshape(-1, 1)
				y = audio_info_dict[str(track_id_list[kk]) + '_low_pass'].reshape(-1, 1)
				#calculate normalized distance between the mfccs for the tracks according to filter, and add to dictionary if small
				dist_lp, _, _, _ = dtw(x, y, dist=lambda x, y: norm(x - y, ord=1))
				if dist_lp < 0.025:
					#if there is no cluster yet, make one
					if returned_chart_data[track_id_list[kk]]['bass_cluster'] == -1:
						returned_chart_data[track_id_list[jj]]['bass_cluster'] = len(cluster_data['bass'])
						returned_chart_data[track_id_list[kk]]['bass_cluster'] = len(cluster_data['bass'])
						cluster_data['bass'].append([track_id_list[jj], track_id_list[kk]])
					#otherwise add it to cluster
					elif returned_chart_data[track_id_list[jj]]['bass_cluster'] == -1:
						returned_chart_data[track_id_list[jj]]['bass_cluster'] = returned_chart_data[track_id_list[kk]]['bass_cluster']
						cluster_data['bass'][returned_chart_data[track_id_list[kk]]['bass_cluster']].append(track_id_list[jj])
				x = audio_info_dict[str(track_id_list[jj]) + '_high_pass'].reshape(-1, 1)
				y = audio_info_dict[str(track_id_list[kk]) + '_high_pass'].reshape(-1, 1)
				#calculate normalized distance for highpass, and add to dictionary if small
				dist_hp, _, _, _ = dtw(x, y, dist=lambda x, y: norm(x - y, ord=1))
				if dist_hp < 0.00025:
					#if there is no cluster yet, make one
					if returned_chart_data[track_id_list[kk]]['treble_cluster'] == -1:
						returned_chart_data[track_id_list[jj]]['treble_cluster'] = len(cluster_data['treble'])
						returned_chart_data[track_id_list[kk]]['treble_cluster'] = len(cluster_data['treble'])
						cluster_data['treble'].append([track_id_list[jj], track_id_list[kk]])
					#otherwise add it to cluster
					elif returned_chart_data[track_id_list[jj]]['treble_cluster'] == -1:
						returned_chart_data[track_id_list[jj]]['treble_cluster'] = returned_chart_data[track_id_list[kk]]['treble_cluster']
						cluster_data['treble'][returned_chart_data[track_id_list[kk]]['treble_cluster']].append(track_id_list[jj])
				dist_lp_list.append(dist_lp)
				dist_hp_list.append(dist_hp)
	track_data['returned_chart_data'] = returned_chart_data
	track_data['cluster_data'] = cluster_data
	track_data['genre_data'] = genre_data
	pickle.dump(track_data, open( 'track_data.p', 'wb' ))
	return track_data

def gettrackdata():
	track_data = pickle.load(open('track_data.p', 'rb' ))
	return track_data

# clear votes
def clear_vote_count():
	vote_res = requests.get('http://smartclub.herokuapp.com/clearvotes')
	scream_res = requests.get('http://smartclub.herokuapp.com/resetscreamtracker')

# select a new track
def switch_genre(track_id):
	genre = track_data['returned_chart_data'][track_id]['genre']
	temp_genre_data = copy.deepcopy(track_data['genre_data'])
	temp_genre_data.pop(genre)
	random_genre_index = int(math.floor(random.random() * len(temp_genre_data.keys())))
	random_genre = temp_genre_data.keys()[random_genre_index]
	random_track_index = int(math.floor(random.random() * len(temp_genre_data[random_genre])))
	return play(temp_genre_data[random_genre][random_track_index])

def update_crowd_feedback():
	vote_res = requests.get('http://smartclub.herokuapp.com/getvotecount')
	scream_res = requests.get('http://smartclub.herokuapp.com/wasthereascream')
	return (json.loads(vote_res.text), scream_res)

def play(track_id):
	clear_vote_count()
	song_url = track_data['returned_chart_data'][track_id]['preview_url']
	media = instance.media_new(song_url)
	player.set_media(media)
	player.play()
	while 1:
		time.sleep(10)
		# after 10 seconds, get request to check upvotes/downvotes and possible noise reaction
		votes, scream_res = update_crowd_feedback()
		if ((votes['upvotes'] > votes['downvotes']) or (scream_res.text == "Yes")):
			# log that they like it & play the rest of the song (20 seconds since its a preview url)
			time.sleep(20)
			votes, scream_res = update_crowd_feedback()
			# if they still like the song play a similar one
			if ((votes['upvotes'] > votes['downvotes']) or (scream_res.text == "Yes")):
				genre = track_data['returned_chart_data'][track_id]['genre']
				random_index = int(math.floor(random.random() * len(track_data['genre_data'][genre])))
				return play(track_data['genre_data'][genre][random_index])
			else:
				switch_genre(track_id)
		else:
			# if they don't like it, switch to a different song
		   return switch_genre(track_id)

# let's get started
if len(sys.argv) > 1 and sys.argv[1] == 'update':
	track_data = updatetrackdata()
else:
	track_data = gettrackdata()
# start with a random track
random_index = int(math.floor(random.random() * len(track_data['returned_chart_data'].keys())))
play(track_data['returned_chart_data'].keys()[random_index])


