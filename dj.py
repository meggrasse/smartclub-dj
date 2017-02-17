import time
import requests
import json
import pickle
import random
import urllib
import vlc
import sys
from pydub import AudioSegment
import librosa
from dtw import dtw
from numpy.linalg import norm
import numpy as np

instance = vlc.Instance()
player = instance.media_player_new()

def updatetrackdata():
	chart_data = json.loads(urllib.urlopen('https://itunes.apple.com/us/rss/topsongs/limit=50/json').read())
	audio_info_dict = {}
	data_dict = {'track_data' : {}, 'cluster_data' : {'bass' : [], 'treble' : []}, 'genre_data' : {}}
	track_id_list = []
	for ii in range(50):
		track_id = chart_data['feed']['entry'][ii]['id']['attributes']['im:id']
		track_id_list.append(track_id)
		preview_url = chart_data['feed']['entry'][ii]['link'][1]['attributes']['href']
		genre = chart_data['feed']['entry'][ii]['category']['attributes']['im:id']
		label = chart_data['feed']['entry'][ii]['title']['label']
		data_dict['track_data'][track_id] = {'preview_url' : preview_url, 'genre' : genre, 'label' : label, 'bass_cluster' : -1, 'treble_cluster' : -1}
		if genre in data_dict['genre_data']:
			data_dict['genre_data'][genre].append(track_id)
		else:
			data_dict['genre_data'][genre] = [track_id]
		# urllib.urlretrieve(preview_url, 'tracks/original/' + str(track_id) + '.m4a')
		# song = AudioSegment.from_file('tracks/original/' + str(track_id) + '.m4a')
		# #get mfcc of bass and treble
		# song.low_pass_filter(250).export('tracks/low-pass/' + str(track_id) + '.m4a')
		# song.high_pass_filter(6000).export('tracks/high-pass/' + str(track_id) + '.m4a')
		# y_low_pass, sr_low_pass = librosa.load('tracks/low-pass/' + str(track_id) + '.m4a') 
		# y_high_pass, sr_high_pass = librosa.load('tracks/high-pass/' + str(track_id) + '.m4a')
		# #store mfcc for comparison
		# audio_info_dict[str(track_id) + '_low_pass'] = librosa.feature.mfcc(y_low_pass, sr_low_pass).T
		# audio_info_dict[str(track_id) + '_high_pass'] = librosa.feature.mfcc(y_high_pass, sr_high_pass).T
	#populate returned chart data array by comparing songs
	# for jj in range(50):
	# 	for kk in range(50):
	# 		if jj > kk:
	# 			x = audio_info_dict[str(track_id_list[jj]) + '_low_pass'].reshape(-1, 1)
	# 			y = audio_info_dict[str(track_id_list[kk]) + '_low_pass'].reshape(-1, 1)
	# 			#calculate normalized distance between the mfccs for the tracks according to filter, and add to dictionary if small
	# 			dist_lp, _, _, _ = dtw(x, y, dist=lambda x, y: norm(x - y, ord=1))
	# 			if dist_lp < 0.025:
	# 				#if there is no cluster yet, make one
	# 				if data_dict['track_data'][track_id_list[kk]]['bass_cluster'] == -1:
	# 					data_dict['track_data'][track_id_list[jj]]['bass_cluster'] = len(data_dict['cluster_data']['bass'])
	# 					data_dict['track_data'][track_id_list[kk]]['bass_cluster'] = len(data_dict['cluster_data']['bass'])
	# 					data_dict['cluster_data']['bass'].append([track_id_list[jj], track_id_list[kk]])
	# 				#otherwise add it to cluster
	# 				elif data_dict['track_data'][track_id_list[jj]]['bass_cluster'] == -1:
	# 					data_dict['track_data'][track_id_list[jj]]['bass_cluster'] = data_dict['track_data'][track_id_list[kk]]['bass_cluster']
	# 					data_dict['cluster_data']['bass'][data_dict['track_data'][track_id_list[kk]]['bass_cluster']].append(track_id_list[jj])
	# 			x = audio_info_dict[str(track_id_list[jj]) + '_high_pass'].reshape(-1, 1)
	# 			y = audio_info_dict[str(track_id_list[kk]) + '_high_pass'].reshape(-1, 1)
	# 			#calculate normalized distance for highpass, and add to dictionary if small
	# 			dist_hp, _, _, _ = dtw(x, y, dist=lambda x, y: norm(x - y, ord=1))
	# 			if dist_hp < 0.00025:
	# 				#if there is no cluster yet, make one
	# 				if data_dict['track_data'][track_id_list[kk]]['treble_cluster'] == -1:
	# 					data_dict['track_data'][track_id_list[jj]]['treble_cluster'] = len(data_dict['cluster_data']['treble'])
	# 					data_dict['track_data'][track_id_list[kk]]['treble_cluster'] = len(data_dict['cluster_data']['treble'])
	# 					data_dict['cluster_data']['treble'].append([track_id_list[jj], track_id_list[kk]])
	# 				#otherwise add it to cluster
	# 				elif data_dict['track_data'][track_id_list[jj]]['treble_cluster'] == -1:
	# 					data_dict['track_data'][track_id_list[jj]]['treble_cluster'] = data_dict['track_data'][track_id_list[kk]]['treble_cluster']
	# 					data_dict['cluster_data']['treble'][data_dict['track_data'][track_id_list[kk]]['treble_cluster']].append(track_id_list[jj])
	pickle.dump(data_dict, open('track_data.p', 'wb'))
	return data_dict

def get_data_dict():
	data_dict = pickle.load(open('track_data.p', 'rb' ))
	return data_dict

# clear votes
def clear_vote_count():
	vote_res = requests.get('http://smartclub.herokuapp.com/clearvotes')
	scream_res = requests.get('http://smartclub.herokuapp.com/resetscreamtracker')

# select a new track
def select_next_track(curr_track_id, liked):
	global not_played
	# just looking at genre
	curr_track_genre = data_dict['track_data'][curr_track_id]['genre']
	if (liked == 1):
		track_ids = data_dict['genre_data'][curr_track_genre]
	else:
		genre_list = data_dict['genre_data'].keys()
		genre_list.remove(curr_track_genre)
		random_genre_index = random.randint(0, len(genre_list) - 1)
		random_genre = genre_list[random_genre_index]
		track_ids = data_dict['genre_data'][random_genre]
	track_ids = list(set(track_ids) & set(not_played.keys()))
	# no similar/different tracks that haven't been played
	if (len(track_ids) == 0):
		print "No similar/different tracks to make a smart choice. Playing random track."
		track_ids = not_played.keys()
	# we've played every track!
	if  (len(not_played.keys()) == 0):
		print "We've actually played every track!"
		for id in data_dict['track_data'].keys():
			not_played[id] = [data_dict['track_data'][id]['genre'], data_dict['track_data'][id]['bass_cluster'], data_dict['track_data'][id]['treble_cluster']]
		track_ids = not_played.keys()
	random_index = random.randint(0, len(track_ids) - 1)
	track_id = track_ids[random_index]
	play(track_id)

def update_crowd_feedback():
	vote_res = requests.get('http://smartclub.herokuapp.com/getvotecount')
	scream_res = requests.get('http://smartclub.herokuapp.com/wasthereascream')
	return (json.loads(vote_res.text), scream_res)

def play(track_id):
	global not_played
	clear_vote_count()
	not_played.pop(track_id, None)
	song_url = data_dict['track_data'][track_id]['preview_url']
	media = instance.media_new(song_url)
	player.set_media(media)
	player.play()
	print "Now playing: " + data_dict['track_data'][track_id]['label']
	print "Current genre: " + data_dict['track_data'][track_id]['genre']
	while 1:
		time.sleep(10)
		# after 10 seconds, get request to check upvotes/downvotes and possible noise reaction
		votes, scream_res = update_crowd_feedback()
		if ((votes['upvotes'] > votes['downvotes']) or (scream_res.text == "Yes")):
			print "We like it!"
			time.sleep(20)
			print "Let's hear a similar track!"
			select_next_track(track_id, 1)
		else:
			print "Not so good. Let's try a different one..."
			select_next_track(track_id, 0)
		return select_next_track()

# let's get started
if len(sys.argv) > 1 and sys.argv[1] == 'update':
	data_dict = updatetrackdata()
else:
	data_dict = get_data_dict()
not_played = {}
for id in data_dict['track_data'].keys():
	not_played[id] = [data_dict['track_data'][id]['genre'], data_dict['track_data'][id]['bass_cluster'], data_dict['track_data'][id]['treble_cluster']]
# start with a random track
random_index = random.randint(0, len(not_played.keys()) - 1)
play(not_played.keys()[random_index])


