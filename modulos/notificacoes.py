"""
Módulo de Notificações
Suporta Email, SMS e Notificações In-App
"""

from datetime import datetime, timedelta
from supabase_db import supabase
import os
import requests

# Configurações (podem vir de .env)
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASS = os.environ.get('SMTP_PASS', '')

SMS_API_KEY = os.environ.get('SMS_API_KEY', '')
SMS_API_URL = os.environ.get('SMS_API_URL', 'https://api.sms.com')

# ═══════════════════════════════════════════
# NOTIFICAÇÕES IN-APP
# ═══════════════════════════════════════════

def criar_notificacao(empresa_id, titulo, mensagem, tipo='info', link=None, dados_extras=None):
    """
    Cria uma notificação in-app
    
    Args:
        tipo: 'info', 'sucesso', 'aviso', 'erro', 'urgente'
        link: URL para onde ir ao clicar na notificação
        dados_extras: dict com dados adicionais
    """
    try:
        notif = {
            'empresa_id': empresa_id,
            'titulo': titulo,
            'mensagem': mensagem,
            'tipo': tipo,
            'link': link,
            'dados_extras': dados_extras or {},
            'lida': False,
            'data_criacao': datetime.now().isoformat()
        }
        
        res = supabase.table('notificacoes').insert(notif).execute()
        
        if res.data:
            return {'sucesso': True, 'id': res.data[0]['id']}
        return {'sucesso': False, 'erro': 'Erro ao criar notificação'}
    
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


def obter_notificacoes(empresa_id, nao_lidas=False, limite=50):
    """Retorna notificações da empresa"""
    try:
        query = supabase.table('notificacoes').select('*').eq('empresa_id', empresa_id)
        
        if nao_lidas:
            query = query.eq('lida', False)
        
        res = query.order('data_criacao', desc=True).limit(limite).execute()
        
        return res.data or []
    
    except Exception as e:
        return []


def contar_notificacoes_nao_lidas(empresa_id):
    """Conta notificações não lidas"""
    try:
        res = supabase.table('notificacoes').select('id', count='exact').eq(
            'empresa_id', empresa_id
        ).eq('lida', False).execute()
        
        return len(res.data) if res.data else 0
    
    except Exception as e:
        return 0


def marcar_notificacao_lida(notificacao_id, empresa_id=None):
    """Marca notificação como lida"""
    try:
        query = supabase.table('notificacoes').update(
            {'lida': True, 'data_leitura': datetime.now().isoformat()}
        ).eq('id', notificacao_id)

        if empresa_id is not None:
            query = query.eq('empresa_id', empresa_id)

        res = query.execute()
        
        return {'sucesso': bool(res.data)}
    
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


def deletar_notificacao(notificacao_id, empresa_id=None):
    """Deleta uma notificação"""
    try:
        query = supabase.table('notificacoes').delete().eq('id', notificacao_id)

        if empresa_id is not None:
            query = query.eq('empresa_id', empresa_id)

        res = query.execute()
        return {'sucesso': True}
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


def limpar_notificacoes_antigas(empresa_id, dias_retencao=30):
    """Remove notificações lidas com mais de X dias"""
    try:
        data_limite = (datetime.now() - timedelta(days=dias_retencao)).isoformat()
        
        supabase.table('notificacoes').delete().eq(
            'empresa_id', empresa_id
        ).eq('lida', True).lt('data_criacao', data_limite).execute()
        
        return {'sucesso': True}
    
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


# ═══════════════════════════════════════════
# NOTIFICAÇÕES POR EMAIL
# ═══════════════════════════════════════════

def enviar_email_notificacao(destinatario, assunto, corpo_html, corpo_texto=None):
    """
    Envia email de notificação
    
    Args:
        destinatario: email do recipient
        assunto: assunto do email
        corpo_html: corpo em HTML
        corpo_texto: corpo em texto puro (opcional)
    """
    try:
        if not SMTP_USER or not SMTP_PASS:
            print("Aviso: SMTP não configurado, notificação por email não enviada")
            # Registrar tentativa falhada
            registrar_tentativa_notificacao(
                tipo='email',
                destinatario=destinatario,
                status='falha',
                motivo='SMTP não configurado'
            )
            return {'sucesso': False, 'erro': 'Email não configurado'}
        
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Criar mensagem
        msg = MIMEMultipart('alternative')
        msg['Subject'] = assunto
        msg['From'] = SMTP_USER
        msg['To'] = destinatario
        
        # Adicionar versão em texto
        if corpo_texto:
            msg.attach(MIMEText(corpo_texto, 'plain'))
        
        # Adicionar versão em HTML
        msg.attach(MIMEText(corpo_html, 'html'))
        
        # Enviar
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as servidor:
            servidor.starttls()
            servidor.login(SMTP_USER, SMTP_PASS)
            servidor.sendmail(SMTP_USER, destinatario, msg.as_string())
        
        # Registrar sucesso
        registrar_tentativa_notificacao(
            tipo='email',
            destinatario=destinatario,
            status='enviado'
        )
        
        return {'sucesso': True, 'mensagem': 'Email enviado com sucesso'}
    
    except Exception as e:
        registrar_tentativa_notificacao(
            tipo='email',
            destinatario=destinatario,
            status='falha',
            motivo=str(e)
        )
        return {'sucesso': False, 'erro': str(e)}


def template_email_notificacao_estoque(produto_nome, estoque_atual, estoque_minimo):
    """Template de email para alerta de estoque baixo"""
    
    html = f"""
    <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 5px; }}
                .header {{ background-color: #ff6b6b; color: white; padding: 15px; text-align: center; }}
                .content {{ padding: 20px; }}
                .alert-box {{ background-color: #ffe0e0; border-left: 4px solid #ff6b6b; padding: 10px; margin: 10px 0; }}
                .footer {{ text-align: center; padding-top: 20px; color: #999; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>⚠️ Alerta de Estoque Baixo</h2>
                </div>
                <div class="content">
                    <p>Olá,</p>
                    <p>O estoque do produto <strong>{produto_nome}</strong> está abaixo do nível mínimo.</p>
                    <div class="alert-box">
                        <p><strong>Estoque Atual:</strong> {estoque_atual} unidades</p>
                        <p><strong>Estoque Mínimo:</strong> {estoque_minimo} unidades</p>
                    </div>
                    <p>Por favor, verifique o sistema e reponha o estoque se necessário.</p>
                </div>
                <div class="footer">
                    <p>Sistema de Gestão Nexus - {datetime.now().strftime('%d/%m/%Y')}</p>
                </div>
            </div>
        </body>
    </html>
    """
    
    return html


def template_email_pedido_novo(pedido_id, cliente_nome, valor_total):
    """Template de email para novo pedido"""
    
    html = f"""
    <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 5px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 15px; text-align: center; }}
                .content {{ padding: 20px; }}
                .pedido-info {{ background-color: #f0f0f0; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                .footer {{ text-align: center; padding-top: 20px; color: #999; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>✓ Novo Pedido Recebido</h2>
                </div>
                <div class="content">
                    <p>Olá,</p>
                    <p>Um novo pedido foi realizado!</p>
                    <div class="pedido-info">
                        <p><strong>ID do Pedido:</strong> #{pedido_id}</p>
                        <p><strong>Cliente:</strong> {cliente_nome}</p>
                        <p><strong>Valor Total:</strong> R$ {valor_total:.2f}</p>
                    </div>
                    <p>Acesse o sistema para mais detalhes e processar o pedido.</p>
                </div>
                <div class="footer">
                    <p>Sistema de Gestão Nexus - {datetime.now().strftime('%d/%m/%Y')}</p>
                </div>
            </div>
        </body>
    </html>
    """
    
    return html


# ═══════════════════════════════════════════
# NOTIFICAÇÕES POR SMS
# ═══════════════════════════════════════════

def enviar_sms_notificacao(numero_telefone, mensagem):
    """
    Envia notificação por SMS
    
    Requer: SMS_API_KEY e SMS_API_URL configurados
    """
    try:
        if not SMS_API_KEY:
            registrar_tentativa_notificacao(
                tipo='sms',
                destinatario=numero_telefone,
                status='falha',
                motivo='SMS API não configurado'
            )
            return {'sucesso': False, 'erro': 'SMS não configurado'}
        
        # Exemplo com Twilio-like API
        payload = {
            'to': numero_telefone,
            'message': mensagem,
            'api_key': SMS_API_KEY
        }
        
        response = requests.post(SMS_API_URL, json=payload, timeout=10)
        
        if response.status_code in [200, 201]:
            registrar_tentativa_notificacao(
                tipo='sms',
                destinatario=numero_telefone,
                status='enviado'
            )
            return {'sucesso': True, 'mensagem': 'SMS enviado com sucesso'}
        else:
            registrar_tentativa_notificacao(
                tipo='sms',
                destinatario=numero_telefone,
                status='falha',
                motivo=f"Erro {response.status_code}"
            )
            return {'sucesso': False, 'erro': f'Erro ao enviar SMS: {response.status_code}'}
    
    except Exception as e:
        registrar_tentativa_notificacao(
            tipo='sms',
            destinatario=numero_telefone,
            status='falha',
            motivo=str(e)
        )
        return {'sucesso': False, 'erro': str(e)}


# ═══════════════════════════════════════════
# HISTÓRICO DE NOTIFICAÇÕES
# ═══════════════════════════════════════════

def registrar_tentativa_notificacao(tipo, destinatario, status, motivo=None):
    """Registra todas as tentativas de envio de notificações"""
    try:
        record = {
            'tipo': tipo,
            'destinatario': destinatario,
            'status': status,
            'motivo': motivo,
            'data_hora': datetime.now().isoformat()
        }
        
        supabase.table('historico_notificacoes').insert(record).execute()
    
    except Exception as e:
        print(f"Erro ao registrar notificação: {e}")


def obter_historico_notificacoes(filtro_tipo=None, filtro_status=None, limite=100):
    """Retorna histórico de notificações enviadas"""
    try:
        query = supabase.table('historico_notificacoes').select('*')
        
        if filtro_tipo:
            query = query.eq('tipo', filtro_tipo)
        
        if filtro_status:
            query = query.eq('status', filtro_status)
        
        res = query.order('data_hora', desc=True).limit(limite).execute()
        
        return res.data or []
    
    except Exception as e:
        return []


# ═══════════════════════════════════════════
# PREFERÊNCIAS DE NOTIFICAÇÃO
# ═══════════════════════════════════════════

def salvar_preferencias_notificacao(empresa_id, preferencias):
    """
    Salva preferências de notificação
    
    Args:
        preferencias: dict com {
            'email_estoque_baixo': bool,
            'email_novo_pedido': bool,
            'sms_urgente': bool,
            'notificar_atrasados': bool,
            'horario_silencio': 'HH:MM'
        }
    """
    try:
        # Verificar se já existe
        existe = supabase.table('preferencias_notificacao').select('id').eq(
            'empresa_id', empresa_id
        ).execute()
        
        prefs = {
            'empresa_id': empresa_id,
            'email_estoque_baixo': preferencias.get('email_estoque_baixo', True),
            'email_novo_pedido': preferencias.get('email_novo_pedido', True),
            'sms_urgente': preferencias.get('sms_urgente', False),
            'notificar_atrasados': preferencias.get('notificar_atrasados', True),
            'horario_silencio': preferencias.get('horario_silencio', None),
            'data_atualizacao': datetime.now().isoformat()
        }
        
        if existe.data:
            # Atualizar
            res = supabase.table('preferencias_notificacao').update(prefs).eq(
                'empresa_id', empresa_id
            ).execute()
        else:
            # Criar
            res = supabase.table('preferencias_notificacao').insert(prefs).execute()
        
        return {'sucesso': bool(res.data)}
    
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


def obter_preferencias_notificacao(empresa_id):
    """Retorna preferências de notificação da empresa"""
    try:
        res = supabase.table('preferencias_notificacao').select('*').eq(
            'empresa_id', empresa_id
        ).execute()
        
        if res.data:
            return res.data[0]
        
        # Retornar preferências padrão
        return {
            'email_estoque_baixo': True,
            'email_novo_pedido': True,
            'sms_urgente': False,
            'notificar_atrasados': True
        }
    
    except Exception as e:
        return {}


from datetime import timedelta
