import logging
import time
from threading import Lock

import vlc

from . import library

STATE = "idle"
STATE_LOCK = Lock()
MEDIA = None
PLAYER = None

logger = logging.getLogger("playback")


def set_state(state):
    global STATE
    if state == STATE:
        return
    logger.debug("State changed: %s -> %s", STATE, state)
    STATE = state

def play_forever():
    global PLAYER
    # Playback thread

    while True:
        time.sleep(0.1)

        if STATE in "idle":
            continue

        with STATE_LOCK:
            if STATE == "playing":
                good_states = ["State.Playing", "State.NothingSpecial", "State.Opening"]
                player_state = str(PLAYER.get_state())
                if player_state in good_states:
                    continue
                logger.debug("New player internal state: %s" % player_state)
                set_state("stopping")

            if STATE == "stopping":
                if PLAYER:
                    PLAYER.stop()
                    PLAYER = None
                set_state("idle")

            if STATE == "loading":

                if PLAYER:
                    PLAYER.stop()

                # TODO: fetch in a thread to keep being reponsive while fetching?
                audio = library.fetch_audio(MEDIA["url"])

                PLAYER = vlc.MediaPlayer(audio["filename"])
                PLAYER.play()

                set_state("playing")

def stop():
    with STATE_LOCK:
        set_state("stopping")

def play(media):
    global MEDIA

    if not media:
        return

    with STATE_LOCK:

        # Can only play after properly stopping
        if STATE != "idle":
            return

        MEDIA = media
        set_state("loading")
