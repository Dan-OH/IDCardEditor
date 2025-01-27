from flask import Flask
from flask_assets import Environment, Bundle
from webassets.cache import MemoryCache

app = Flask(__name__)
#app.config['MAX_CONTENT_LENGTH'] = 10000

app.config['ASSETS_CACHE'] = MemoryCache(capacity=1000)

assets = Environment(app)
# create bundle for Flask-Assets to compile and prefix scss to css
css = Bundle('src/scss/styles.scss',
             filters=['libsass'],
             output='dist/css/styles.css',
             depends='src/scss/*.scss')

assets.register("asset_css", css)
css.build()

from app import routes
