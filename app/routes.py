# app/routes.py
from flask import (render_template, url_for, flash, redirect, Blueprint, 
                   request, Response, stream_with_context)
from app import db, bcrypt
from app.models import User, Analysis
from flask_login import login_user, current_user, logout_user, login_required
from datetime import date
import json

# --- ALTERAÇÃO IMPORTANTE AQUI ---
# Importamos a função diretamente do seu novo local na pasta 'services'
from app.services.analysis_logic import gerar_analises

# --- ROTAS PRINCIPAIS E DE AUTENTICAÇÃO ---

main = Blueprint('main', __name__)

@main.route("/")
@main.route("/home")
def index():
    return render_template('index.html')

@main.route('/api/analise/public')
def api_analise_public():
    data_selecionada = request.args.get('date', default=str(date.today()), type=str)
    # A chamada à função agora é direta, sem o prefixo 'analysis_logic'
    return Response(stream_with_context(gerar_analises(data_selecionada, 'free')), mimetype='text/event-stream')

# ... (O resto das suas rotas de autenticação (register, login, logout) continuam iguais) ...
@main.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, email=email, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Sua conta foi criada! Você já pode fazer login.', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html', title='Registrar')

@main.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user, remember=True)
            return redirect(url_for('main.dashboard'))
        else:
            flash('Login sem sucesso. Por favor, verifique o e-mail e a senha.', 'danger')
    return render_template('login.html', title='Login')

@main.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('main.index'))


# --- ROTAS PROTEGIDAS PARA MEMBROS ---

@main.route("/dashboard")
@login_required
def dashboard():
    return render_template('dashboard.html', title='Dashboard')

@main.route("/analysis/<int:analysis_id>")
def analysis_detail(analysis_id):
    analysis = Analysis.query.get_or_404(analysis_id)
    content = json.loads(analysis.content)
    return render_template('analysis_detail.html', title='Análise Detalhada', analysis_content=content)

@main.route('/api/analise/private')
@login_required
def api_analise_private():
    data_selecionada = request.args.get('date', default=str(date.today()), type=str)
    user_tier_do_utilizador = current_user.subscription_tier
    # A chamada à função agora é direta, sem o prefixo 'analysis_logic'
    return Response(stream_with_context(gerar_analises(data_selecionada, user_tier_do_utilizador)), mimetype='text/event-stream')