import logging
import time
from queue import Queue
import os
import math
from functools import lru_cache

try:
    from PIL import Image, ImageDraw, ImageFont
    from StreamDeck.DeviceManager import DeviceManager
    from StreamDeck.ImageHelpers import PILHelper
except:
    print("\n\n/!\\ You are missing one of the dependencies of Raspberry Deck! Please run:\npip install -r requirements.txt\n\n")
    import sys
    sys.exit(1)

logging.getLogger("PIL.Image").setLevel(logging.INFO)

logger = logging.getLogger("deck")

REFRESH_QUEUE = Queue()

PAGE = 1

LAST_KEYDOWN = None

fonts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts/")


from . import config, library, playback

def key_change_callback(deck, key, state):
    global LAST_KEYDOWN, PAGE

    keypress_duration = 0

    if state:
        LAST_KEYDOWN = time.time()
    else:
        if LAST_KEYDOWN is not None:
            keypress_duration = time.time() - LAST_KEYDOWN

    logger.debug("Key state %s = %s (%0.3fs)", key, state, keypress_duration)

    # Last key
    if key == deck.key_count() - 1 and state == False:

        if keypress_duration > 2:
            playback.stop()
        else:
            # next page
            old_page = PAGE
            total_pages = math.ceil(len(library.MEDIALIST) / (deck.key_count() - 1))
            if total_pages > 1:
                PAGE = (PAGE % total_pages) + 1
                update_deck_images(deck)

    # We trigger play on key up
    elif state == False:
        media = library.get_key_media(key + (deck.key_count() - 1) * (PAGE - 1))
        playback.play(media)

# Generates a custom tile with run-time generated text and custom image via the
# PIL module.
@lru_cache(maxsize=1024)
def render_thumb(deck, icon=None, text=None, text_size=14):
    # Create new key image of the correct dimensions, black background.
    image = PILHelper.create_image(deck)

    if icon:
        img = Image.open(icon).convert("RGBA")
        img.thumbnail((image.width, image.height), Image.LANCZOS)
        img_pos = ((image.width - img.width) // 2, (image.height - img.height) // 2)
        image.paste(img, img_pos, img)

    if text:
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(os.path.join(fonts_dir, config.FONT), text_size)
        label_w, label_h = draw.textsize(text, font=font)
        label_pos = ((image.width - label_w) // 2, (image.height - label_h) // 2)
        draw.text(label_pos, text=text, font=font, fill="white")

    return PILHelper.to_native_format(deck, image)

def update_key_image(deck, key, text=None, text_size=None):

    if text is not None:
        thumb = render_thumb(deck, text=text, text_size=text_size)
    else:
        image = library.get_key_image(key + (deck.key_count() - 1) * (PAGE - 1))
        if image:
            thumb = render_thumb(deck, icon=image)
        else:
            thumb = render_thumb(deck)

    deck.set_key_image(key, thumb)

def update_deck_images(deck):

    update_key_image(deck, deck.key_count() - 1, str(PAGE), text_size=50)

    # Set initial key images.
    # Last one is blank (stop button)
    for key in range(deck.key_count() - 1):
        update_key_image(deck, key)



def device_setup(deck):

    logger.info("Using deck '%s'", deck.deck_type())

    logger.info("Deck ID: %s", deck.id())

    deck.open()

    logger.info("Deck SN: %s", deck.get_serial_number().strip())

    deck.reset()

    deck.set_brightness(config.STREAMDECK_BRIGHTNESS)

    update_deck_images(deck)

    # Register callback function for when a key state changes.
    deck.set_key_callback(key_change_callback)

def device_id(deck):
    return deck.id()

def device_search():

    deck = None

    while True:
        streamdecks = DeviceManager().enumerate()
        ids = {device_id(d) for d in streamdecks}

        if deck and device_id(deck) not in ids:
            # Deck was just disconnected
            logger.debug("Deck %s disconnected.", device_id(deck))
            try:
                deck.close()
            except Exception as e:
                logger.error("While closing deck: %s", e)
            deck = None

        if not deck and len(streamdecks) > 0:
            logger.debug("Found %s streamdecks", len(streamdecks))
            deck = streamdecks[0]
            device_setup(deck)

        try:
            if deck and REFRESH_QUEUE.get(block=False):
                update_deck_images(deck)
        except Exception:
            pass

        time.sleep(1)