# matsilvaj/matscore_ai/MatScore_AI-8c62a1bbb800a601129fe855777ce01336db29d0/app/routes.py
# app/routes.py
from flask import (render_template, url_for, flash, redirect, Blueprint, 
                   request, Response, stream_with_context, jsonify) # <-- Adicionar jsonify
from . import db, bcrypt, mail, limiter 
from app.models import User, Analysis, DailyUserView, ContactMessage
import os
from flask_mail import Message
from flask_login import login_user, current_user, logout_user, login_required
from datetime import date
import json
from functools import wraps
import stripe # <-- Adicionar import

from app.services.analysis_logic import gerar_analises

main = Blueprint('main', __name__)

# ... (suas funções de envio de email e decoradores) ...
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


# --- ROTAS DE PAGAMENTO STRIPE ---

@main.route("/create-checkout-session", methods=["POST"])
@login_required
def create_checkout_session():
    price_id = request.form.get('price_id')
    
    # Cria um cliente na Stripe se o usuário ainda não tiver um
    if not current_user.stripe_customer_id:
        customer = stripe.Customer.create(
            email=current_user.email,
            name=current_user.username
        )
        current_user.stripe_customer_id = customer.id
        db.session.commit()

    try:
        checkout_session = stripe.checkout.Session.create(
            customer=current_user.stripe_customer_id,
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                },
            ],
            mode="subscription", # MODO DE ASSINATURA
            success_url=url_for('main.payment_success', _external=True),
            cancel_url=url_for('main.payment_cancel', _external=True),
            allow_promotion_codes=True, # Permite cupons de desconto
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        flash(f'Erro ao iniciar o pagamento: {e}', 'danger')
        return redirect(url_for('main.plans'))

@main.route("/payment-success")
def payment_success():
    flash('Pagamento bem-sucedido! Sua assinatura está ativa.', 'success')
    return redirect(url_for('main.futebol'))

@main.route("/payment-cancel")
def payment_cancel():
    flash('O pagamento foi cancelado.', 'info')
    return redirect(url_for('main.plans'))

@main.route("/stripe-webhook", methods=["POST"])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
    
    # Se o webhook_secret não estiver configurado, não continue.
    if not webhook_secret:
        return "Webhook secret não configurado.", 500
        
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        # Payload inválido
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        # Assinatura inválida
        return 'Invalid signature', 400

    # Lida com o evento de checkout bem-sucedido
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # --- CORREÇÃO APLICADA AQUI ---
        # Em vez de usar session['customer'] diretamente,
        # vamos buscar a sessão completa na API da Stripe.
        try:
            full_session = stripe.checkout.Session.retrieve(session.id)
            customer_id = full_session.customer
        except stripe.error.StripeError as e:
            print(f"Erro ao buscar a sessão da Stripe: {e}")
            return "Erro interno", 500
        # -----------------------------

        if customer_id:
            # Encontra o usuário no seu banco de dados
            user = User.query.filter_by(stripe_customer_id=customer_id).first()
            if user:
                user.subscription_tier = 'member' # Atualiza o plano do usuário
                db.session.commit()
                print(f"Assinatura ativada para o usuário: {user.email}")

    # Lida com o evento de renovação de assinatura bem-sucedida
    if event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        customer_id = invoice.get('customer')
        if customer_id:
            user = User.query.filter_by(stripe_customer_id=customer_id).first()
            if user:
                user.subscription_tier = 'member' # Garante que a assinatura continue ativa
                db.session.commit()
                print(f"Assinatura renovada para o usuário: {user.email}")


    # Lida com o evento de falha ou cancelamento da assinatura
    if event['type'] == 'customer.subscription.deleted' or (event['type'] == 'customer.subscription.updated' and event['data']['object'].get('cancel_at_period_end')):
        subscription = event['data']['object']
        customer_id = subscription.get('customer')
        if customer_id:
            user = User.query.filter_by(stripe_customer_id=customer_id).first()
            if user:
                user.subscription_tier = 'free' # Volta para o plano gratuito
                db.session.commit()
                print(f"Assinatura cancelada para o usuário: {user.email}")


    return 'OK', 200


# --- ROTAS PRINCIPAIS --- (sem alterações, apenas para contexto)
@main.route("/")
@main.route("/home")
def index():
    today_str = date.today().strftime('%Y-%m-%d')
    todays_analyses_db = Analysis.query.filter_by(analysis_date=today_str).all()
    analyses_list = []
    for analysis_obj in todays_analyses_db:
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
    # Passa a chave publicável para o template
    stripe_public_key = os.getenv('STRIPE_PUBLIC_KEY')
    return render_template('plans.html', title='Nossos Planos', stripe_public_key=stripe_public_key)

# ... (resto do seu arquivo de rotas) ...
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
    
    # Cria o título dinâmico para a aba do navegador
    page_title = f"{analysis_data.get('mandante_nome', 'Análise')} vs {analysis_data.get('visitante_nome', 'Detalhada')}"
    
    return render_template('analysis_detail.html', title=page_title, analysis=analysis_data, limit_reached=limit_reached)

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