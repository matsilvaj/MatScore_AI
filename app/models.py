from . import db
from flask_login import UserMixin
from datetime import datetime, date

class User(db.Model, UserMixin):
    # ... (o seu modelo User continua igual) ...
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    subscription_tier = db.Column(db.String(20), nullable=False, default='free')

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.subscription_tier}')"

class Analysis(db.Model):
    # ... (o seu modelo Analysis continua igual) ...
    id = db.Column(db.Integer, primary_key=True)
    match_api_id = db.Column(db.Integer, nullable=False)
    analysis_date = db.Column(db.String(10), nullable=False) # Formato 'YYYY-MM-DD'
    content = db.Column(db.Text, nullable=False) # Guarda o JSON completo da análise
    generated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (db.Index('idx_match_date', "match_api_id", "analysis_date"), )

    def __repr__(self):
        return f"Analysis for match {self.match_api_id} on {self.analysis_date}"


# --- NOVO MODELO PARA RASTREAR VISUALIZAÇÕES DIÁRIAS ---
class DailyUserView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    analysis_id = db.Column(db.Integer, nullable=False)
    view_date = db.Column(db.Date, nullable=False, default=date.today)

    # Garante que um utilizador só pode ter uma entrada por análise por dia
    __table_args__ = (db.UniqueConstraint('user_id', 'analysis_id', 'view_date', name='_user_analysis_date_uc'),)

    def __repr__(self):
        return f"<DailyUserView user {self.user_id}, analysis {self.analysis_id}, date {self.view_date}>"

# --- CORREÇÃO: A CLASSE ABAIXO FOI MOVIDA PARA FORA DA 'DailyUserView' ---
class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    submitted_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<ContactMessage {self.id} from {self.email}>"