# matsilvaj/matscore_ai/MatScore_AI-8c62a1bbb800a601129fe855777ce01336db29d0/app/__init__.py
# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_caching import Cache
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate # <-- 1. IMPORTAR MIGRATE
from dotenv import load_dotenv
import os
import logging
from logging.handlers import RotatingFileHandler
import stripe

load_dotenv()

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'main.login'
cache = Cache(config={
    'CACHE_TYPE': 'RedisCache',
    'CACHE_REDIS_URL': os.getenv('CACHE_REDIS_URL', 'redis://localhost:6379/0')
})
mail = Mail()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=os.getenv('CACHE_REDIS_URL', 'redis://localhost:6379/0')
)
migrate = Migrate() # <-- 2. INICIALIZAR MIGRATE

@login_manager.user_loader
def load_user(user_id):
    from .models import User
    return User.query.get(int(user_id))

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    db_user = os.getenv('DB_USER')
    db_pass = os.getenv('DB_PASS')
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT')
    db_name = os.getenv('DB_NAME')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}'

    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS').lower() in ['true', 'on', '1']
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    
    app.config['STRIPE_PUBLIC_KEY'] = os.getenv('STRIPE_PUBLIC_KEY')
    stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    cache.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db) # <-- 3. CONECTAR MIGRATE COM O APP E O DB
    if not app.debug:
        limiter.init_app(app)

    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # REMOVA OU COMENTE ESTA PARTE PARA QUE O MIGRATE CONTROLE A CRIAÇÃO DE TABELAS
    # with app.app_context():
    #     db.create_all()

    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler('logs/matscore.log', maxBytes=1024000, backupCount=10)
        
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('MatScore AI')

    return app