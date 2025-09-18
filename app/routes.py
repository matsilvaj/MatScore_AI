# app/routes.py
from flask import (render_template, url_for, flash, redirect, Blueprint, 
                   request, Response, stream_with_context)
from app import db, bcrypt
from app.models import User, Analysis
from flask_login import login_user, current_user, logout_user, login_required
from datetime import date
import json

# Importamos a função diretamente do seu novo local na pasta 'services'
from app.services.analysis_logic import gerar_analises

main = Blueprint('main', __name__)

# --- ROTAS PRINCIPAIS ---

@main.route("/")
@main.route("/home")
def index():
    # A página inicial agora redireciona para a de futebol
    return redirect(url_for('main.futebol'))

@main.route("/futebol")
def futebol():
    return render_template('futebol.html', title='Análises de Futebol')

@main.route("/basquete")
def basquete():
    return render_template('basquete.html', title='Análises de Basquete')

@main.route("/plans")
def plans():
    return render_template('plans.html', title='Nossos Planos')

# --- API UNIFICADA ---

@main.route('/api/analise')
def api_analise():
    user_tier = 'free'
    if current_user.is_authenticated:
        user_tier = current_user.subscription_tier
    data_selecionada = request.args.get('date', default=str(date.today()), type=str)
    return Response(stream_with_context(gerar_analises(data_selecionada, user_tier)), mimetype='text/event-stream')

# --- ROTAS DE AUTENTICAÇÃO ---

@main.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.futebol'))
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
        return redirect(url_for('main.futebol'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user, remember=True)
            return redirect(url_for('main.futebol'))
        else:
            flash('Login sem sucesso. Por favor, verifique o e-mail e a senha.', 'danger')
    return render_template('login.html', title='Login')

@main.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('main.index'))

# --- ROTAS DE CONTEÚDO E CONTA ---

@main.route("/analysis/<int:analysis_id>")
def analysis_detail(analysis_id):
    analysis = Analysis.query.get_or_404(analysis_id)
    content = json.loads(analysis.content)
    return render_template('analysis_detail.html', title='Análise Detalhada', analysis_content=content)

@main.route("/account")
@login_required
def account():
    return render_template('account.html', title='Minha Conta')

@main.route("/account/change_password", methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    if not bcrypt.check_password_hash(current_user.password, current_password):
        flash('A sua senha atual está incorreta. Por favor, tente novamente.', 'danger')
        return redirect(url_for('main.account'))
    hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
    current_user.password = hashed_password
    db.session.commit()
    flash('A sua senha foi alterada com sucesso!', 'success')
    return redirect(url_for('main.account'))

@main.route("/account/delete", methods=['POST'])
@login_required
def delete_account():
    db.session.delete(current_user)
    db.session.commit()
    logout_user()
    flash('A sua conta foi excluída com sucesso.', 'info')
    return redirect(url_for('main.index'))