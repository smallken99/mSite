import os
import time
from flask import Flask, url_for as flask_url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from mSite.config import Config


db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'users.login'
login_manager.login_message_category = 'info'
mail = Mail()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    # 自動快取破壞 (Cache Busting)：為所有靜態資源自動追加修改時間戳記 ?v=<mtime>
    @app.context_processor
    def override_url_for():
        return dict(url_for=dated_url_for)

    def dated_url_for(endpoint, **values):
        if endpoint == 'static':
            filename = values.get('filename', None)
            if filename:
                file_path = os.path.join(app.root_path, endpoint, filename)
                try:
                    values['v'] = int(os.stat(file_path).st_mtime)
                except OSError:
                    values['v'] = int(time.time())
        return flask_url_for(endpoint, **values)

    from mSite.main.routes import main
    from mSite.users.routes import users
    from mSite.posts.routes import posts
    from mSite.transferFile.routes import trans
    from mSite.inventory.routes import inventory
    from mSite.cost.routes import cost
    from mSite.shop.routes import shop
    app.register_blueprint(main)
    app.register_blueprint(users)
    app.register_blueprint(posts)
    app.register_blueprint(trans)
    app.register_blueprint(inventory)
    app.register_blueprint(cost)
    app.register_blueprint(shop)



    return app
