# app/routes.py
from flask import (render_template, url_for, flash, redirect, Blueprint, 
                   request, Response, stream_with_context)
from . import db, bcrypt, mail, limiter 
from app.models import User, Analysis, DailyUserView, ContactMessage
import os
from flask_mail import Message
from flask_login import login_user, current_user, logout_user, login_required
from datetime import date
import json
# --- NOVA IMPORTAÇÃO ---
from functools import wraps

from app.services.analysis_logic import gerar_analises

main = Blueprint('main', __name__)

# --- FUNÇÃO HELPER PARA ENVIAR EMAIL DE VERIFICAÇÃO ---
def send_verification_email(user):
    token = user.get_reset_token() # Reutilizamos o mesmo método de token
    msg = Message('Confirme o Seu Endereço de E-mail - MatScore AI',
                  sender=('MatScore AI', os.getenv('MAIL_USERNAME')),
                  recipients=[user.email])
    msg.body = f'''Bem-vindo ao MatScore AI! Por favor, clique no link abaixo para verificar o seu e-mail e ativar a sua conta:
{url_for('main.confirm_email', token=token, _external=True)}

Se você não se registou no nosso site, por favor, ignore este e-mail.
'''
    mail.send(msg)

# --- FUNÇÃO HELPER PARA ENVIAR EMAIL DE RESET ---
def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Pedido de Redefinição de Senha - MatScore AI',
                  sender=('MatScore AI', os.getenv('MAIL_USERNAME')),
                  recipients=[user.email])
    msg.body = f'''Para redefinir a sua senha, visite o seguinte link:
{url_for('main.reset_token', token=token, _external=True)}

Se você não fez este pedido, simplesmente ignore este e-mail e nenhuma alteração será feita.
'''
    mail.send(msg)

# --- DECORADOR PARA EXIGIR CONFIRMAÇÃO DE EMAIL ---
def confirmed_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.email_verified:
            return redirect(url_for('main.unconfirmed'))
        return f(*args, **kwargs)
    return decorated_function

# --- ROTAS PRINCIPAIS ---

@main.route("/")
@main.route("/home")
def index():
    # Busca as 4 análises mais recentes do banco de dados
    recent_analyses_db = Analysis.query.order_by(Analysis.generated_at.desc()).limit(4).all()
    
    # Processa as análises para passar ao template
    analyses_list = []
    for analysis_obj in recent_analyses_db:
        try:
            analysis_data = json.loads(analysis_obj.content)
            analysis_data['analysis_id'] = analysis_obj.id
            analyses_list.append(analysis_data)
        except json.JSONDecodeError:
            continue
            
    return render_template('home.html', title='Início', analyses=analyses_list)


@main.route("/futebol")
@login_required
@confirmed_required
def futebol():
    views_today_count = 0
    if current_user.is_authenticated and current_user.subscription_tier == 'free':
        today = date.today()
        views_today_count = DailyUserView.query.filter_by(user_id=current_user.id, view_date=today).count()
    
    return render_template('futebol.html', title='Análises de Futebol', views_today=views_today_count)

@main.route("/basquete")
@login_required
@confirmed_required
def basquete():
    return render_template('basquete.html', title='Análises de Basquete')

@main.route("/plans")
def plans():
    return render_template('plans.html', title='Nossos Planos')

# --- API UNIFICADA ---

@main.route('/api/analise')
@login_required
@confirmed_required
@limiter.limit("10 per minute")
def api_analise():
    user_tier = 'free'
    if current_user.is_authenticated:
        user_tier = current_user.subscription_tier
    data_selecionada = request.args.get('date', default=str(date.today()), type=str)
    return Response(stream_with_context(gerar_analises(data_selecionada, user_tier)), mimetype='text/event-stream')

# --- ROTAS DE AUTENTICAÇÃO E VERIFICAÇÃO ---

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
        
        send_verification_email(user) # Envia o e-mail de verificação
        
        flash('Sua conta foi criada! Por favor, verifique o seu e-mail para ativá-la.', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html', title='Registrar')

@main.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.email_verified:
            return redirect(url_for('main.futebol'))
        else:
            return redirect(url_for('main.unconfirmed'))
            
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user, remember=True)
            if user.email_verified:
                return redirect(url_for('main.futebol'))
            else:
                return redirect(url_for('main.unconfirmed'))
        else:
            flash('Login sem sucesso. Por favor, verifique o e-mail e a senha.', 'danger')
    return render_template('login.html', title='Login')

@main.route('/confirm/<token>')
@login_required
def confirm_email(token):
    if current_user.email_verified:
        return redirect(url_for('main.futebol'))
    
    user = User.verify_reset_token(token) # Reutilizamos o mesmo método de verificação
    if user and user.id == current_user.id:
        user.email_verified = True
        db.session.commit()
        flash('A sua conta foi verificada com sucesso!', 'success')
    else:
        flash('O link de confirmação é inválido ou expirou.', 'danger')
    return redirect(url_for('main.futebol'))

@main.route('/unconfirmed')
@login_required
def unconfirmed():
    if current_user.email_verified:
        return redirect(url_for('main.futebol'))
    return render_template('unconfirmed.html', title='Confirme a sua conta')

@main.route('/resend_confirmation', methods=['POST'])
@login_required
def resend_confirmation():
    if current_user.email_verified:
        return redirect(url_for('main.futebol'))
    send_verification_email(current_user)
    flash('Um novo e-mail de confirmação foi enviado para a sua caixa de entrada.', 'success')
    return redirect(url_for('main.unconfirmed'))


@main.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@main.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.futebol'))
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            send_reset_email(user)
        flash('Se existir uma conta com esse e-mail, um link para redefinir a senha foi enviado.', 'info')
        return redirect(url_for('main.login'))
    return render_template('reset_request.html', title='Redefinir Senha')

@main.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.futebol'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('O token é inválido ou expirou.', 'danger')
        return redirect(url_for('main.reset_request'))
    if request.method == 'POST':
        password = request.form.get('password')
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('A sua senha foi atualizada! Já pode fazer login.', 'success')
        return redirect(url_for('main.login'))
    return render_template('reset_token.html', title='Redefinir Senha')

# --- ROTAS DE CONTEÚDO E CONTA ---

@main.route("/analysis/<int:analysis_id>")
@login_required
@confirmed_required
def analysis_detail(analysis_id):
    limit_reached = False
    
    if current_user.is_authenticated and current_user.subscription_tier == 'free':
        today = date.today()
        
        views_today = DailyUserView.query.filter_by(user_id=current_user.id, view_date=today).all()
        is_already_viewed = any(view.analysis_id == analysis_id for view in views_today)
        
        if not is_already_viewed and len(views_today) >= 3:
            limit_reached = True
        
        elif not is_already_viewed:
            new_view = DailyUserView(user_id=current_user.id, analysis_id=analysis_id, view_date=today)
            db.session.add(new_view)
            db.session.commit()

    analysis_obj = Analysis.query.get_or_404(analysis_id)
    analysis_data = json.loads(analysis_obj.content)
    
    return render_template('analysis_detail.html', title='Análise Detalhada', analysis=analysis_data, limit_reached=limit_reached)

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
    user_id_deleted = current_user.id
    db.session.delete(current_user)
    db.session.commit()
    logout_user()
    flash(f'A sua conta foi excluída com sucesso.', 'info')
    return redirect(url_for('main.index'))

@main.route("/terms")
def terms():
    return render_template('terms.html', title='Termos de Serviço')

@main.route("/privacy")
def privacy():
    return render_template('privacy.html', title='Política de Privacidade')

@main.route("/contact", methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        category = request.form.get('category')
        message_body = request.form.get('message')

        new_message = ContactMessage(
            name=name,
            email=email,
            category=category,
            message=message_body
        )
        db.session.add(new_message)
        db.session.commit()

        try:
            msg = Message(
                subject=f"Nova Mensagem de Contacto: [{category}]",
                sender=('MatScore AI', os.getenv('MAIL_USERNAME')),
                recipients=[os.getenv('MAIL_USERNAME')]
            )
            msg.body = f"""
            Nova mensagem recebida através do site MatScore AI.

            De: {name} ({email})
            Categoria: {category}
            -----------------------------------------

            {message_body}
            """
            mail.send(msg)
            flash('A sua mensagem foi enviada com sucesso! Responderemos em breve.', 'success')
        except Exception as e:
            print(f"ERRO AO ENVIAR EMAIL: {e}")
            flash('A sua mensagem foi guardada, mas houve um erro ao enviar a notificação. Não se preocupe, iremos vê-la.', 'info')
        
        return redirect(url_for('main.contact'))
        
    return render_template('contact.html', title='Contacto')