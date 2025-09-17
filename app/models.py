# app/models.py

from . import db
from flask_login import UserMixin
from datetime import datetime

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    subscription_tier = db.Column(db.String(20), nullable=False, default='free')

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.subscription_tier}')"

# --- NOVO MODELO PARA GUARDAR ANÁLISES ---
class Analysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    match_api_id = db.Column(db.Integer, nullable=False)
    analysis_date = db.Column(db.String(10), nullable=False) # Formato 'YYYY-MM-DD'
    content = db.Column(db.Text, nullable=False) # Guarda o JSON completo da análise
    generated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Cria um índice para pesquisas rápidas
    __table_args__ = (db.Index('idx_match_date', "match_api_id", "analysis_date"), )

    def __repr__(self):
        return f"Analysis for match {self.match_api_id} on {self.analysis_date}"