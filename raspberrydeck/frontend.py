import logging
import sys
import os

from flask import Flask, request, send_from_directory

from . import config, library, deck


static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend/")

app = Flask("frontend", static_url_path="", static_folder=static_dir, template_folder=static_dir)
app.use_reloader = False
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['TEMPLATES_AUTO_RELOAD'] = True


logger = logging.getLogger("frontend")


@app.route('/')
def index():
    return send_from_directory(static_dir, "index.html")

@app.route('/api/state')
def get_state():
    return {
        "medialist": library.MEDIALIST,
        # "state": MEDIA_STATE
    }

@app.route('/api/medialist', methods=["POST"])
def post_medialist():
    post = request.get_json()
    if type(post) != list:
        raise Exception("Unexpected POST")
    library.set_medialist(post)
    deck.REFRESH_QUEUE.put(True, block=False)
    library.download_and_cache_all()
    return {
        "result": "ok"
    }

@app.route('/api/image')
def get_image():
    url = request.args.get("url")
    meta = library.fetch_metadata(url)
    filename = os.path.join(os.getcwd(), library.get_file(meta["thumb"]))
    return send_from_directory(os.path.dirname(filename), os.path.basename(filename))


def serve_forever():
    
    # Turn off some Flask output
    sys.modules['flask.cli'].show_server_banner = lambda *x: None
    logging.getLogger('werkzeug').setLevel(logging.ERROR)

    logger.info("Starting frontend at port %s", config.FRONTEND_PORT)
    app.run(port=int(config.FRONTEND_PORT), host="0.0.0.0")
