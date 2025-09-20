# app/models.py
from . import db
from flask_login import UserMixin
from datetime import datetime, date
# --- NOVAS IMPORTAÇÕES ---
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask import current_app
# -------------------------

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    subscription_tier = db.Column(db.String(20), nullable=False, default='free')
    # --- NOVO CAMPO ADICIONADO ---
    email_verified = db.Column(db.Boolean, nullable=False, default=False)

    def get_reset_token(self, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id})

    @staticmethod
    def verify_reset_token(token, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token, max_age=expires_sec)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.subscription_tier}')"

class Analysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    match_api_id = db.Column(db.Integer, nullable=False)
    analysis_date = db.Column(db.String(10), nullable=False) # Formato 'YYYY-MM-DD'
    content = db.Column(db.Text, nullable=False) # Guarda o JSON completo da análise
    generated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (db.Index('idx_match_date', "match_api_id", "analysis_date"), )

    def __repr__(self):
        return f"Analysis for match {self.match_api_id} on {self.analysis_date}"

class DailyUserView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    analysis_id = db.Column(db.Integer, nullable=False)
    view_date = db.Column(db.Date, nullable=False, default=date.today)

    __table_args__ = (db.UniqueConstraint('user_id', 'analysis_id', 'view_date', name='_user_analysis_date_uc'),)

    def __repr__(self):
        return f"<DailyUserView user {self.user_id}, analysis {self.analysis_id}, date {self.view_date}>"

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    submitted_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<ContactMessage {self.id} from {self.email}>"
    
class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    api_id = db.Column(db.Integer, unique=True, nullable=False)
    match_date = db.Column(db.String(10), nullable=False, index=True) # Formato 'YYYY-MM-DD'
    
    home_team_id = db.Column(db.Integer, nullable=False)
    home_team_name = db.Column(db.String(100), nullable=False)
    home_team_crest = db.Column(db.String(255))
    
    away_team_id = db.Column(db.Integer, nullable=False)
    away_team_name = db.Column(db.String(100), nullable=False)
    away_team_crest = db.Column(db.String(255))
    
    league_name = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<Match {self.api_id} on {self.match_date}: {self.home_team_name} vs {self.away_team_name}>"

    def to_dict(self):
        return {
            "id": self.api_id,
            "data": self.match_date,
            "mandante_id": self.home_team_id,
            "mandante_nome": self.home_team_name,
            "mandante_escudo": self.home_team_crest,
            "visitante_id": self.away_team_id,
            "visitante_nome": self.away_team_name,
            "visitante_escudo": self.away_team_crest,
            "liga_nome": self.league_name
        }