from threading import Lock
import json
import os
import urllib.request
import shutil
import re
import hashlib
import logging
import tempfile

import youtube_dl

from . import config

logger = logging.getLogger("media")

ytd_logger = logging.getLogger("downloader")


MEDIALIST = []

MEDIALIST_LOCK = Lock()
DOWNLOAD_LOCK = Lock()


def init_folders():
    if not os.path.isdir(config.CACHE_DIR):
        os.makedirs(config.CACHE_DIR)

    medialist_dir = os.path.dirname(config.MEDIA_FILE)
    if not os.path.isdir(medialist_dir):
        os.makedirs(medialist_dir)


def set_medialist(lst):
    global MEDIALIST

    with MEDIALIST_LOCK:
        MEDIALIST = lst

        shutil.copy(config.MEDIA_FILE, config.MEDIA_FILE+".bak")
        with open(config.MEDIA_FILE, "w") as f:
           json.dump(lst, f, indent=4)

def read_medialist():
    global MEDIALIST

    with MEDIALIST_LOCK:
        if os.path.isfile(config.MEDIA_FILE):
            with open(config.MEDIA_FILE, "r") as f:
                MEDIALIST = json.load(f)

def download_and_cache_all():
    logger.debug('Starting download cache of all media...')
    for media in MEDIALIST:
        fetch_audio(media["url"])
    print('... all media downloaded')

def get_cache_filename(url):
    return os.path.join(config.CACHE_DIR, re.sub(r'[^\w_.)( -]', '_', url))

def get_file(url, filename=None):
    filename = filename or get_cache_filename(url)
    if not os.path.isfile(filename):
        logger.debug("Downloading %s" % url)
        urllib.request.urlretrieve(url, filename + ".tmp")
        os.rename(filename + ".tmp", filename)
    return filename


def fetch_audio(url, read_cache=True):
    filename = get_cache_filename(url)

    if os.path.isfile(filename) and read_cache:
        return {
            "filename": filename,
            "from_cache": True
        }

    with DOWNLOAD_LOCK:

        if os.path.isfile(filename) and read_cache:
            return {
                "filename": filename,
                "from_cache": True
            }

        ydl_opts = {
            "logger": ytd_logger,
            "outtmpl": filename,
            "format": "bestaudio",
            "socket_timeout": 30
            # writethumbnail
            # cachedir
            # noplaylist
        }
        
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return {
            "filename": filename,
            "from_cache": False
        }


def fetch_metadata(url, read_cache=True):
    filename = get_cache_filename("json_%s" % url)

    if os.path.isfile(filename) and read_cache:
        with open(filename, "r") as f:
            try:
                obj = json.load(f)
                obj["from_cache"] = True
                return obj
            except Exception as e:
                logger.error("Failed reading cache file %s : %s" % (filename, e))

    ydl_opts = {
        "writeinfojson": True,
        "skip_download": True,
        "logger": ytd_logger,
        "outtmpl": filename,
        "socket_timeout": 30
    }
    
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    with open(filename+".info.json", "r") as jsonf:
        metadata = json.load(jsonf)        
    os.remove(filename+".info.json")

    def sort_key(img):
        w = img.get("width", 0)
        # No need for a bigger image than this
        if w < 500:
            return w
        else:
            return -w

    images = sorted(metadata.get("thumbnails", []), key=sort_key, reverse=True)
    
    if len(images) == 0:
        return {}

    obj = {
        "thumb": images[0]["url"]
    }
    with open(filename, "w") as cachef:
        json.dump(obj, cachef)

    obj["from_cache"] = False

    return obj

def get_key_media(key):
    if key >= len(MEDIALIST):
        return

    return MEDIALIST[key]

def get_key_image(key):
    if key >= len(MEDIALIST):
        return

    if (MEDIALIST[key].get("image") or "").strip():
        return get_file(MEDIALIST[key]["image"])
    else:
        meta = fetch_metadata(MEDIALIST[key]["url"])
        return get_file(meta["thumb"])
