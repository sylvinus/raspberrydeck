# import time
# import urllib.request
# import re
# import json
# import hashlib
import logging

import threading

from . import frontend, library, deck, playback

logging.basicConfig(level="DEBUG", format='%(asctime)s  %(name)10s  %(levelname)s: %(message)s')

if __name__ == "__main__":

    library.init_folders()
    library.read_medialist()

    deck_thread = threading.Thread(target=deck.device_search)
    deck_thread.start()

    playback_thread = threading.Thread(target=playback.play_forever)
    playback_thread.start()

    download_thread = threading.Thread(target=library.download_and_cache_all)
    download_thread.start()

    frontend_thread = threading.Thread(target=frontend.serve_forever)
    frontend_thread.start()

    # Wait until all application threads have terminated (for this example,
    # this is when all deck handles are closed).
    for t in threading.enumerate():
        if t is threading.currentThread():
            continue

        if t.is_alive():
            t.join()