import pafy
import vlc
import time

import urllib.request
import re
import json
import hashlib

import os
import threading
from PIL import Image, ImageDraw, ImageFont
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers import PILHelper

CACHE_DIR = "cache/"

MEDIA_STATE = "idle"

if not os.path.isdir(CACHE_DIR):
    os.makedirs(CACHE_DIR)

MEDIA = [
    {
        "youtube": "https://www.youtube.com/watch?v=tw8hZhzkohw"
    },
    {
        "youtube": "https://www.youtube.com/watch?v=jTccQpTXmbg"
    },
    {
        "youtube": "https://www.youtube.com/watch?v=N5jDlspik18"
    },
    {
        "youtube": "https://www.youtube.com/watch?v=QAoR_BgtHTY"
    },
    {
        "youtube": "https://www.youtube.com/watch?v=LQYZ1taDp9w"
    },
    {
        "youtube": "https://www.youtube.com/watch?v=tVJUWVHp0VM"
    },
    {
        "youtube": "https://www.youtube.com/watch?v=JZ4kQ8KKH2E"
    },
    {
        "youtube": "https://www.youtube.com/watch?v=_pDGkeeWMCg"
    },
    {
        "youtube": "https://www.youtube.com/watch?v=2yF4TLuHwvc"
    },
    {
        "youtube": "https://www.youtube.com/watch?v=zP6PKtT1TMA",
    },
    {
        "youtube": "https://www.youtube.com/watch?v=HaqqNk68ZWk"
    },
    {
        "youtube": "https://www.youtube.com/watch?v=Ns92r5TQH3k",
    },
    {
        "youtube": "https://www.youtube.com/watch?v=J4gslL_Evs0"
    },
    {
        "youtube": "https://www.youtube.com/watch?v=Ug6dmqneAvw",
        "image": "https://contesethistoire.files.wordpress.com/2011/10/pierre-et-le-loup.jpg"
    }
]

def set_state(state):
    global MEDIA_STATE
    if state == MEDIA_STATE:
        return
    print("State %s -> %s" % (MEDIA_STATE, state))
    MEDIA_STATE = state


def play(num):
    global MEDIA_STATE

    media = MEDIA[num]

    meta = youtube_metadata(media["youtube"])
    
    if os.path.isfile(meta["cache_file"]) and meta["from_cache"]:
        url = meta["cache_file"]
    else:
        meta = youtube_metadata(media["youtube"])
        url = meta["bestaudio"]

    print("Now playing %s" % url)
    player = vlc.MediaPlayer(url)
    player.play()

    good_states = ["State.Playing", "State.NothingSpecial", "State.Opening"]
    while str(player.get_state()) in good_states and MEDIA_STATE != "stopping":
        # print('Stream is working. Current state = {}'.format(player.get_state()))
        time.sleep(0.1)

    print('Stream is not working. Current state = {}'.format(player.get_state()))
    player.stop()
    set_state("idle")

def download_and_cache_all():
    print('Starting download cache of all media...')
    for media in MEDIA:
        meta = youtube_metadata(media["youtube"], read_cache=False)
        get_file(meta["bestaudio"], filename=meta["cache_file"])
    print('... all media downloaded')

def key_change_callback(deck, key, state):

    # Last key = STOP
    if key == deck.key_count() - 1 and state:
        set_state("stopping")
        return

    if key >= len(MEDIA):
        return

    if MEDIA_STATE == "playing":
        return

    set_state("playing")

    # Print new key state
    print("Deck {} Key {} = {}".format(deck.id(), key, state), flush=True)
    thread_play = threading.Thread(target=play, args=(key,))
    thread_play.start()

# Generates a custom tile with run-time generated text and custom image via the
# PIL module.
def render_key_image(deck, icon_filename, font_filename=None, label_text=None):
    # Create new key image of the correct dimensions, black background.
    image = PILHelper.create_image(deck)

    margin = 20 if label_text else 0

    # Resize the source image asset to best-fit the dimensions of a single key,
    # and paste it onto our blank frame centered as closely as possible.
    icon = Image.open(icon_filename).convert("RGBA")
    icon.thumbnail((image.width, image.height - margin), Image.LANCZOS)
    icon_pos = ((image.width - icon.width) // 2, 0)
    image.paste(icon, icon_pos, icon)

    # Load a custom TrueType font and use it to overlay the key index, draw key
    # label onto the image.
    draw = ImageDraw.Draw(image)
    if label_text:
        font = ImageFont.truetype(font_filename, 14)
        label_w, label_h = draw.textsize(label_text, font=font)
        label_pos = ((image.width - label_w) // 2, image.height - 20)
        draw.text(label_pos, text=label_text, font=font, fill="white")

    return PILHelper.to_native_format(deck, image)

def get_cache_filename(url):
    return os.path.join(CACHE_DIR, re.sub(r'[^\w_.)( -]', '_', url))

def get_file(url, filename=None):
    filename = filename or get_cache_filename(url)
    if not os.path.isfile(filename):
        print("Downloading %s" % url)
        urllib.request.urlretrieve(url, filename + ".tmp")
        os.rename(filename + ".tmp", filename)
    return filename

def youtube_metadata(url, read_cache=True):
    filename = get_cache_filename("json_%s" % url)

    if os.path.isfile(filename) and read_cache:
        with open(filename, "r") as f:
            try:
                obj = json.load(f)
                obj["from_cache"] = True
                return obj
            except Exception as e:
                print("Failed reading cache file %s : %s" % (filename, e))

    with open(filename, "w") as f:
        video = pafy.new(url)
        obj = {
            "thumb": video.thumb,
            "bestaudio": video.getbestaudio().url,
            "cache_file": os.path.join(CACHE_DIR, hashlib.sha1(url.encode()).hexdigest())
        }
        json.dump(obj, f)
        obj["from_cache"] = False
        return obj


def update_key_image(deck, key, state):
    if key >= len(MEDIA):
        return

    if MEDIA[key].get("image"):
        filename = get_file(MEDIA[key]["image"])
    else:
        meta = youtube_metadata(MEDIA[key]["youtube"])
        filename = get_file(meta["thumb"])

    image = render_key_image(deck, filename)
    
    deck.set_key_image(key, image)

streamdecks = []
while True:
    streamdecks = DeviceManager().enumerate()
    print("Found {} Stream Deck(s).\n".format(len(streamdecks)))
    if len(streamdecks) > 0:
        break
    time.sleep(1)

deck = streamdecks[0]

deck.open()
deck.reset()
print("Opened '{}' device (serial number: '{}')".format(deck.deck_type(), deck.get_serial_number()))

deck.set_brightness(30)

# Set initial key images.
for key in range(deck.key_count()):
    update_key_image(deck, key, False)

# Register callback function for when a key state changes.
deck.set_key_callback(key_change_callback)

download_thread = threading.Thread(target=download_and_cache_all)
download_thread.start()

# Wait until all application threads have terminated (for this example,
# this is when all deck handles are closed).
for t in threading.enumerate():
    if t is threading.currentThread():
        continue

    if t.is_alive():
        t.join()
