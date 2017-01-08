# SmartClub - DJ

This is the DJ module of the SmartClub project. This module gets sentiment data from the server, and uses that data
to determine which track to play next, finding similar tracks though filtering out and comparing the bass lines and treble lines, and using ML to match the crowd's taste.

The master repo for this project is located at https://github.com/meggrasse/smartclub.

## Requirements

Python: written using Python 2.7.10. Should work on all versions of Python 2.7.

To install the necessary libraries for this project. Navigate to the smartclub-dj directory in your shell and run:

```bash
$ pip install -r requirements.txt
```

I believe you have to have [VLC installed](https://www.videolan.org/vlc/) to utilize the VLC library. If you are on Mac using the
standard VLC installation, set your path using:

```bash
$ export VLC_PLUGIN_PATH=/Applications/VLC.app/Contents/MacOS/plugins/
```

Otherwise, configure the path to represent your filesystem.

## Setup

Update to your server URL in *clear_vote_count()* and *update_crowd_feedback()*.

## Usage

In your shell, in the smartclub-dj directory first run:

```bash
$ python dj.py update
```

This will download the iTunes Top 50 tracks and perform the necessary computations to prepare the DJ (this'll take a while).
Good news is this data will be saved to your machine, so you will only need to run this command when you want to update to
new tracks.

Once you have run that command, to run the DJ every subsequent time, in the smartclub-dj directory run:

```bash
$ python dj.py
```

It will use the data collected using the other SmartClub modules to select the next track.
If no data is being collected, it will play random songs on iTunes Top 50.
