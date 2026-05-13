import os
import uuid
import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, abort
from flask_cors import CORS
from werkzeug.utils import secure_filename
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Aviso: Módulo 'python-dotenv' não encontrado. Usando variáveis de ambiente do sistema.")

# Importação centralizada do banco
from supabase_db import (
    supabase, init_db,
    registrar_empresa, autenticar_usuario, obter_empresa,
    criar_categoria, obter_categorias, deletar_categoria,
    criar_produto, obter_produtos, obter_produto, atualizar_produto, deletar_produto,
    adicionar_estoque, retirar_estoque,
    criar_vendedor, obter_vendedores, deletar_vendedor,
    criar_pedido, obter_pedidos, obter_pedido_detalhado, atualizar_status_pedido, atualizar_pedido,
    obter_historico,
    criar_reuniao, obter_reunioes, atualizar_status_reuniao, deletar_reuniao,
    criar_contato, obter_contatos, deletar_contato,
    obter_dashboard,
    criar_aviso, obter_avisos, contar_avisos_nao_lidos, marcar_aviso_lido, deletar_aviso,
    salvar_perfil_loja, obter_perfil_loja, listar_fornecedores, listar_clientes,
    criar_notificacao, obter_notificacoes, marcar_notificacao_lida, deletar_notificacao, contar_notificacoes_nao_lidas,
    compartilhar_vitrine, aceitar_compartilhamento, obter_fornecedores_compartilhados, registrar_visita_vitrine, obter_visitantes_vitrine,
    obter_relatorio_fornecedor, obter_relatorio_cliente,
)

# Configuração de caminhos absoluta
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, 
            template_folder=TEMPLATE_DIR, 
            static_folder=STATIC_DIR)

CORS(app) 

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'nexus-ultra-secure-key-2026')
app.config['UPLOAD_FOLDER'] = os.path.join(STATIC_DIR, 'uploads')
app.config['SUPABASE_URL'] = os.environ.get('SUPABASE_URL', 'https://gtctfqphvsczeenpysco.supabase.co')
app.config['SUPABASE_KEY'] = os.environ.get('NEXT_PUBLIC_SUPABASE_ANON_KEY', '')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ═══════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            if request.path.startswith('/api/'):
                return jsonify({'sucesso': False, 'mensagem': 'Sessão expirada ou não autenticada'}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated


def get_empresa_id():
    return session.get('empresa_id')


# ═══════════════════════════════════════════
# PÁGINAS
# ═══════════════════════════════════════════

@app.route('/')
def home():
    if session.get('user_id'):
        tipo = session.get('empresa_tipo')
        if not tipo:
            session.clear()
            return render_template('escolha.html')
        if tipo == 'fornecedor':
            return redirect(url_for('painel_fornecedor'))
        return redirect(url_for('painel_cliente'))
    return render_template('escolha.html')


@app.route('/cadastro/<tipo>')
def cadastro_page(tipo):
    if tipo not in ('fornecedor', 'cliente'):
        return redirect(url_for('home'))
    return render_template('cadastro.html', tipo=tipo)


@app.route('/login')
@app.route('/login/<tipo>')
def login_page(tipo=None):
    if tipo and tipo not in ('fornecedor', 'cliente'):
        return redirect(url_for('login_page'))
        
    if session.get('user_id'):
        u_tipo = session.get('empresa_tipo')
        if u_tipo == 'fornecedor':
            return redirect(url_for('painel_fornecedor'))
        if u_tipo == 'cliente':
            return redirect(url_for('painel_cliente'))
        session.clear()
    return render_template('login.html', tipo=tipo)


@app.route('/fornecedor')
@login_required
def painel_fornecedor():
    tipo = session.get('empresa_tipo')
    if tipo != 'fornecedor':
        return redirect(url_for('painel_cliente'))
    
    empresa = obter_empresa(get_empresa_id())
    if not empresa:
        session.clear()
        return redirect(url_for('login_page'))
    return render_template('fornecedor.html', empresa=empresa, usuario=session.get('user_nome'))


@app.route('/cliente')
@login_required
def painel_cliente():
    tipo = session.get('empresa_tipo')
    if tipo != 'cliente':
        return redirect(url_for('painel_fornecedor'))
    
    empresa = obter_empresa(get_empresa_id())
    if not empresa:
        session.clear()
        return redirect(url_for('login_page'))
    return render_template('cliente.html', empresa=empresa, usuario=session.get('user_nome'))


@app.route('/relatorios')
@login_required
def relatorios():
    tipo = session.get('empresa_tipo')
    empresa = obter_empresa(get_empresa_id())
    if not empresa:
        session.clear()
        return redirect(url_for('login_page'))
    # Redireciona para o painel certo
    if tipo == 'fornecedor':
        return redirect(url_for('relatorios_fornecedor'))
    return redirect(url_for('relatorios_cliente'))


@app.route('/relatorios/fornecedor')
@login_required
def relatorios_fornecedor():
    if session.get('empresa_tipo') != 'fornecedor':
        return redirect(url_for('painel_cliente'))
    empresa = obter_empresa(get_empresa_id())
    if not empresa:
        session.clear()
        return redirect(url_for('login_page'))
    return render_template('relatorio_fornecedor.html',
        empresa=empresa,
        empresa_id=get_empresa_id(),
        empresa_nome=session.get('empresa_nome'),
        usuario=session.get('user_nome')
    )


@app.route('/relatorios/cliente')
@login_required
def relatorios_cliente():
    if session.get('empresa_tipo') != 'cliente':
        return redirect(url_for('painel_fornecedor'))
    empresa = obter_empresa(get_empresa_id())
    if not empresa:
        session.clear()
        return redirect(url_for('login_page'))
    return render_template('relatorio_cliente.html',
        empresa=empresa,
        empresa_id=get_empresa_id(),
        empresa_nome=session.get('empresa_nome'),
        usuario=session.get('user_nome')
    )


@app.route('/loja/<int:forn_id>')
def vitrine_fornecedor(forn_id):
    """Página pública da loja/vitrine do fornecedor"""
    fornecedor = obter_empresa(forn_id)
    if not fornecedor or fornecedor.get('tipo') != 'fornecedor':
        abort(404)
    produtos = obter_produtos(forn_id)

    # Registra visita se cliente está logado
    if session.get('user_id') and session.get('empresa_tipo') == 'cliente':
        registrar_visita_vitrine(forn_id, get_empresa_id())

    return render_template(
        'vitrine.html', fornecedor=fornecedor, produtos=produtos,
        user_type=session.get('empresa_tipo'), user_nome=session.get('user_nome'),
        user_empresa=session.get('empresa_nome')
    )


# ═══════════════════════════════════════════
# AUTH API
# ═══════════════════════════════════════════

@app.route('/api/registrar', methods=['POST'])
def api_registrar():
    data = request.get_json(force=True, silent=True) or {}
    nome_empresa = (data.get('nome_empresa') or '').strip()
    documento = (data.get('documento') or '').strip()
    tipo_documento = (data.get('tipo_documento') or 'cnpj').strip()
    tipo = (data.get('tipo') or '').strip()
    email = (data.get('email') or '').strip()
    senha = data.get('senha') or ''
    endereco = (data.get('endereco') or '').strip()
    telefone = (data.get('telefone') or '').strip()

    if not nome_empresa:
        return jsonify({'sucesso': False, 'mensagem': 'Nome da empresa é obrigatório'}), 400
    if tipo not in ('fornecedor', 'cliente'):
        return jsonify({'sucesso': False, 'mensagem': 'Tipo de conta inválido'}), 400
    if not email or not senha:
        return jsonify({'sucesso': False, 'mensagem': 'E-mail e Senha são obrigatórios'}), 400
    if len(senha) < 6:
        return jsonify({'sucesso': False, 'mensagem': 'A senha deve ter pelo menos 6 caracteres'}), 400

    r = registrar_empresa(nome_empresa, documento, tipo_documento, tipo, endereco, telefone, email, senha)
    if not r.get('sucesso'):
        return jsonify(r), 400

    empresa_id = r['id']
    user_id = r.get('user_id')

    # Login automático após cadastro
    session['user_id'] = user_id
    session['user_nome'] = email.split('@')[0]
    session['empresa_id'] = empresa_id
    session['empresa_tipo'] = tipo
    session['empresa_nome'] = nome_empresa

    redir = '/fornecedor' if tipo == 'fornecedor' else '/cliente'
    return jsonify({
        'sucesso': True, 
        'redirect': redir,
        'user_id': user_id,
        'empresa_id': empresa_id
    }), 201


@app.route('/api/login_session', methods=['POST'])
def api_login_session():
    data = request.get_json(force=True, silent=True) or {}
    email = data.get('email')
    
    if not email:
        return jsonify({'sucesso': False, 'mensagem': 'Email não fornecido'}), 400

    try:
        res = supabase.table('usuarios').select('*, empresas(nome, tipo)').eq('login', email).execute()
        if not res.data:
            return jsonify({'sucesso': False, 'mensagem': 'Usuário não encontrado no banco'}), 404
        
        u = res.data[0]
        session['user_id'] = u['id']
        session['user_nome'] = u['nome']
        session['empresa_id'] = u['empresa_id']
        session['empresa_tipo'] = u['empresas']['tipo']
        session['empresa_nome'] = u['empresas']['nome']

        redir = '/fornecedor' if u['empresas']['tipo'] == 'fornecedor' else '/cliente'
        return jsonify({'sucesso': True, 'redirect': redir})
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json(force=True, silent=True) or {}
    login = (data.get('login') or '').strip()
    senha = data.get('senha') or ''

    if not login or not senha:
        return jsonify({'sucesso': False, 'mensagem': 'Login e senha são obrigatórios'}), 400

    user = autenticar_usuario(login, senha)
    if not user:
        return jsonify({'sucesso': False, 'mensagem': 'Credenciais incorretas ou conta inativa'}), 401

    session['user_id'] = user['id']
    session['user_nome'] = user['nome']
    session['empresa_id'] = user['empresa_id']
    session['empresa_tipo'] = user['empresa_tipo']
    session['empresa_nome'] = user['empresa_nome']

    redir = '/fornecedor' if user['empresa_tipo'] == 'fornecedor' else '/cliente'
    return jsonify({'sucesso': True, 'redirect': redir})


@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'sucesso': True})


# ═══════════════════════════════════════════
# CATEGORIAS API
# ═══════════════════════════════════════════

@app.route('/api/categorias', methods=['GET'])
@login_required
def api_categorias():
    return jsonify(obter_categorias(get_empresa_id()))


@app.route('/api/categorias', methods=['POST'])
@login_required
def api_criar_categoria():
    data = request.get_json(force=True, silent=True) or {}
    nome = (data.get('nome') or '').strip()
    empresa_id = get_empresa_id()
    if not nome:
        return jsonify({'sucesso': False, 'mensagem': 'Nome da categoria é obrigatório'}), 400
    if not empresa_id:
        return jsonify({'sucesso': False, 'mensagem': 'Sessão inválida. Faça login novamente.'}), 401
    r = criar_categoria(empresa_id, nome)
    if not r.get('sucesso'):
        return jsonify(r), 400
    return jsonify(r), 201


@app.route('/api/categorias/<int:cat_id>', methods=['DELETE'])
@login_required
def api_deletar_categoria(cat_id):
    return jsonify(deletar_categoria(get_empresa_id(), cat_id))


# ═══════════════════════════════════════════
# PRODUTOS API
# ═══════════════════════════════════════════

@app.route('/api/produtos', methods=['GET'])
@login_required
def api_produtos():
    return jsonify(obter_produtos(get_empresa_id()))


@app.route('/api/produtos', methods=['POST'])
@login_required
def api_criar_produto():
    # Aceita tanto form-data (com imagem) quanto JSON
    if request.content_type and 'multipart' in request.content_type:
        data = request.form
    else:
        data = request.get_json(force=True, silent=True) or {}

    empresa_id = get_empresa_id()
    nome = (data.get('nome') or '').strip()

    if not nome:
        return jsonify({'sucesso': False, 'mensagem': 'Nome do produto é obrigatório'}), 400
    if not empresa_id:
        return jsonify({'sucesso': False, 'mensagem': 'Sessão inválida. Faça login novamente.'}), 401

    # Upload de imagem
    imagem_filename = None
    if 'imagem' in request.files:
        img_file = request.files['imagem']
        if img_file and img_file.filename != '':
            ext = img_file.filename.rsplit('.', 1)[-1].lower()
            if ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
                filename = secure_filename(f"{uuid.uuid4().hex}.{ext}")
                img_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                imagem_filename = filename

    def to_float(val):
        try: return float(str(val or 0).replace(',', '.'))
        except: return 0.0

    def to_int(val):
        try: return int(val or 0)
        except: return 0

    # Categoria — cria se vier nome, usa id se vier id
    cat_id = data.get('categoria_id')
    if cat_id:
        try: cat_id = int(cat_id)
        except: cat_id = None

    nova_cat = (data.get('categoria_nome') or '').strip()
    if not cat_id and nova_cat:
        cat_res = criar_categoria(empresa_id, nova_cat)
        if cat_res.get('sucesso'):
            cat_id = cat_res.get('id')

    r = criar_produto(
        empresa_id,
        nome,
        data.get('sku', ''),
        cat_id,
        to_float(data.get('custo', 0)),
        to_float(data.get('preco', 0)),
        to_int(data.get('quantidade', 0)),
        to_int(data.get('minimo', 0)),
        data.get('descricao', ''),
        imagem_filename
    )

    if not r.get('sucesso'):
        return jsonify(r), 400
    return jsonify(r), 201


@app.route('/api/produtos/<int:pid>', methods=['PUT'])
@login_required
def api_atualizar_produto(pid):
    data = request.get_json(force=True, silent=True) or {}
    r = atualizar_produto(get_empresa_id(), pid, data)
    if not r.get('sucesso'):
        return jsonify(r), 400
    return jsonify(r)


@app.route('/api/produtos/<int:pid>', methods=['DELETE'])
@login_required
def api_deletar_produto(pid):
    return jsonify(deletar_produto(get_empresa_id(), pid))


@app.route('/api/produtos/<int:pid>/entrada', methods=['POST'])
@login_required
def api_entrada_estoque(pid):
    data = request.get_json(force=True, silent=True) or {}
    try:
        qtd = int(data.get('quantidade', 0))
    except:
        return jsonify({'sucesso': False, 'mensagem': 'Quantidade deve ser um número'}), 400
    obs = (data.get('observacoes') or '').strip()
    if qtd <= 0:
        return jsonify({'sucesso': False, 'mensagem': 'Quantidade deve ser positiva'}), 400
    r = adicionar_estoque(get_empresa_id(), pid, qtd, obs)
    if not r.get('sucesso'):
        return jsonify(r), 400
    return jsonify(r)


@app.route('/api/produtos/<int:pid>/saida', methods=['POST'])
@login_required
def api_saida_estoque(pid):
    data = request.get_json(force=True, silent=True) or {}
    try:
        qtd = int(data.get('quantidade', 0))
    except:
        return jsonify({'sucesso': False, 'mensagem': 'Quantidade deve ser um número'}), 400
    obs = (data.get('observacoes') or '').strip()
    if qtd <= 0:
        return jsonify({'sucesso': False, 'mensagem': 'Quantidade deve ser positiva'}), 400
    r = retirar_estoque(get_empresa_id(), pid, qtd, obs)
    if not r.get('sucesso'):
        return jsonify(r), 400
    return jsonify(r)


# ═══════════════════════════════════════════
# VENDEDORES API
# ═══════════════════════════════════════════

@app.route('/api/vendedores', methods=['GET'])
@login_required
def api_vendedores():
    return jsonify(obter_vendedores(get_empresa_id()))


@app.route('/api/vendedores', methods=['POST'])
@login_required
def api_criar_vendedor():
    data = request.get_json(force=True, silent=True) or {}
    nome = (data.get('nome') or '').strip()
    if not nome:
        return jsonify({'sucesso': False, 'mensagem': 'Nome é obrigatório'}), 400
    r = criar_vendedor(get_empresa_id(), nome, data.get('email', ''),
                       data.get('telefone', ''), data.get('comissao', 0))
    if not r.get('sucesso'):
        return jsonify(r), 400
    return jsonify(r), 201


@app.route('/api/vendedores/<int:vid>', methods=['DELETE'])
@login_required
def api_deletar_vendedor(vid):
    return jsonify(deletar_vendedor(get_empresa_id(), vid))


# ═══════════════════════════════════════════
# PEDIDOS API
# ═══════════════════════════════════════════

@app.route('/api/pedidos', methods=['GET'])
@login_required
def api_listar_pedidos():
    if session.get('empresa_tipo') == 'cliente':
        return jsonify(obter_pedidos(cliente_id=get_empresa_id()))
    return jsonify(obter_pedidos(empresa_id=get_empresa_id()))


@app.route('/api/pedidos', methods=['POST'])
@login_required
def api_criar_pedido():
    data = request.get_json(force=True, silent=True) or {}
    cliente = (data.get('cliente_nome') or '').strip()
    data_pedido = (data.get('data') or '').strip()
    itens = data.get('itens') or []
    vendedor_id = data.get('vendedor_id')
    obs = data.get('observacoes', '')
    data_entrega = (data.get('data_entrega') or '').strip() or None
    mensagem_cliente = (data.get('mensagem_cliente') or '').strip()
    forma_pagamento = (data.get('forma_pagamento') or '').strip() or None
    comissao_valor = data.get('comissao_valor', 0)

    if not cliente:
        return jsonify({'sucesso': False, 'mensagem': 'Nome do cliente é obrigatório'}), 400
    if not data_pedido:
        return jsonify({'sucesso': False, 'mensagem': 'Data é obrigatória'}), 400
    if not itens:
        return jsonify({'sucesso': False, 'mensagem': 'Adicione ao menos um item ao pedido'}), 400

    r = criar_pedido(get_empresa_id(), cliente, data_pedido, itens, vendedor_id, obs,
                    data_entrega=data_entrega, mensagem_cliente=mensagem_cliente,
                    forma_pagamento=forma_pagamento, comissao_valor=comissao_valor)
    if not r.get('sucesso'):
        return jsonify(r), 400
    return jsonify(r), 201


@app.route('/api/pedidos/<int:pid>', methods=['PUT'])
@login_required
def api_atualizar_pedido(pid):
    if session.get('empresa_tipo') != 'fornecedor':
        return jsonify({'sucesso': False, 'mensagem': 'Apenas fornecedor pode atualizar pedidos'}), 403
    data = request.get_json(force=True, silent=True) or {}
    if not data:
        return jsonify({'sucesso': False, 'mensagem': 'Nenhum dado fornecido para atualização'}), 400
    r = atualizar_pedido(get_empresa_id(), pid, data)
    if not r.get('sucesso'):
        return jsonify(r), 400
    return jsonify(r)


@app.route('/api/pedidos/<int:pid>', methods=['GET'])
@login_required
def api_pedido_detalhe(pid):
    d = obter_pedido_detalhado(get_empresa_id(), pid)
    if not d:
        abort(404)
    # Retorna o pedido diretamente (não aninhado) para compatibilidade com o frontend
    pedido = d['pedido']
    pedido['itens'] = d['itens']
    return jsonify(pedido)


@app.route('/api/pedidos/<int:pid>/status', methods=['PUT'])
@login_required
def api_status_pedido(pid):
    data = request.get_json(force=True, silent=True) or {}
    status = (data.get('status') or '').strip()
    if not status:
        return jsonify({'sucesso': False, 'mensagem': 'Status é obrigatório'}), 400
    return jsonify(atualizar_status_pedido(get_empresa_id(), pid, status))


# ═══════════════════════════════════════════
# HISTÓRICO API
# ═══════════════════════════════════════════

@app.route('/api/historico', methods=['GET'])
@login_required
def api_historico():
    tipo = request.args.get('tipo')
    di = request.args.get('data_inicio')
    df = request.args.get('data_fim')
    return jsonify(obter_historico(get_empresa_id(), filtro_tipo=tipo or None,
                                   data_inicio=di or None, data_fim=df or None))


# ═══════════════════════════════════════════
# REUNIÕES API
# ═══════════════════════════════════════════

@app.route('/api/reunioes', methods=['GET'])
@login_required
def api_reunioes():
    return jsonify(obter_reunioes(get_empresa_id()))


@app.route('/api/reunioes', methods=['POST'])
@login_required
def api_criar_reuniao():
    data = request.get_json(force=True, silent=True) or {}
    titulo = (data.get('titulo') or '').strip()
    if not titulo:
        return jsonify({'sucesso': False, 'mensagem': 'Título é obrigatório'}), 400
    r = criar_reuniao(get_empresa_id(), titulo, data.get('descricao', ''),
                      data.get('data_hora', ''), data.get('local', ''),
                      data.get('participantes', ''))
    if not r.get('sucesso'):
        return jsonify(r), 400
    return jsonify(r), 201


@app.route('/api/reunioes/<int:rid>/status', methods=['PUT'])
@login_required
def api_status_reuniao(rid):
    data = request.get_json(force=True, silent=True) or {}
    return jsonify(atualizar_status_reuniao(get_empresa_id(), rid, data.get('status', '')))


@app.route('/api/reunioes/<int:rid>', methods=['DELETE'])
@login_required
def api_deletar_reuniao(rid):
    return jsonify(deletar_reuniao(get_empresa_id(), rid))


# ═══════════════════════════════════════════
# CONTATOS API
# ═══════════════════════════════════════════

@app.route('/api/contatos', methods=['GET'])
@login_required
def api_contatos():
    return jsonify(obter_contatos(get_empresa_id()))


@app.route('/api/contatos', methods=['POST'])
@login_required
def api_criar_contato():
    data = request.get_json(force=True, silent=True) or {}
    nome = (data.get('nome') or '').strip()
    if not nome:
        return jsonify({'sucesso': False, 'mensagem': 'Nome é obrigatório'}), 400
    r = criar_contato(get_empresa_id(), nome, data.get('documento', ''),
                      data.get('email', ''), data.get('telefone', ''),
                      data.get('endereco', ''), data.get('tipo', 'cliente'))
    if not r.get('sucesso'):
        return jsonify(r), 400
    return jsonify(r), 201


@app.route('/api/contatos/<int:cid>', methods=['DELETE'])
@login_required
def api_deletar_contato(cid):
    return jsonify(deletar_contato(get_empresa_id(), cid))


# ═══════════════════════════════════════════
# DASHBOARD API
# ═══════════════════════════════════════════

@app.route('/api/dashboard', methods=['GET'])
@login_required
def api_dashboard():
    return jsonify(obter_dashboard(get_empresa_id()))


# ═══════════════════════════════════════════
# CATÁLOGO API (Para Clientes)
# ═══════════════════════════════════════════

@app.route('/api/catalogo/fornecedores', methods=['GET'])
@login_required
def api_catalogo_fornecedores():
    try:
        res = supabase.table('empresas').select('id, nome, email, telefone, endereco').eq('tipo', 'fornecedor').execute()
        return jsonify(res.data)
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@app.route('/api/catalogo/fornecedores/<int:forn_id>/produtos', methods=['GET'])
@login_required
def api_catalogo_produtos(forn_id):
    return jsonify(obter_produtos(forn_id))


@app.route('/api/cliente/comprar', methods=['POST'])
@login_required
def api_cliente_comprar():
    if session.get('empresa_tipo') != 'cliente':
        return jsonify({'sucesso': False, 'mensagem': 'Apenas clientes podem realizar compras'}), 403
    
    data = request.get_json(force=True, silent=True) or {}
    try:
        forn_id = int(data.get('fornecedor_id'))
        prod_id = int(data.get('produto_id'))
    except:
        return jsonify({'sucesso': False, 'mensagem': 'Fornecedor ou produto inválido'}), 400
    
    try:
        qtd = int(data.get('quantidade', 0))
    except:
        return jsonify({'sucesso': False, 'mensagem': 'Quantidade inválida'}), 400

    data_entrega = (data.get('data_entrega') or '').strip() or None
    mensagem_cliente = (data.get('mensagem_cliente') or '').strip()
    forma_pagamento = (data.get('forma_pagamento') or '').strip() or None

    if qtd <= 0:
        return jsonify({'sucesso': False, 'mensagem': 'Quantidade deve ser maior que zero'}), 400
    
    try:
        r_prod = supabase.table('produtos').select('nome, preco, quantidade').eq('id', prod_id).eq('empresa_id', forn_id).execute()
        if not r_prod.data:
            return jsonify({'sucesso': False, 'mensagem': 'Produto não encontrado no fornecedor'}), 404
            
        prod = r_prod.data[0]
        if prod['quantidade'] < qtd:
            return jsonify({'sucesso': False, 'mensagem': 'Estoque insuficiente no fornecedor'}), 400

        cliente_empresa = session.get('empresa_nome', 'Cliente')
        total = float(prod['preco']) * qtd
        itens = [{
            'produto_id': prod_id,
            'quantidade': qtd,
            'preco': float(prod['preco']),
            'subtotal': total
        }]
        
        data_hoje = datetime.date.today().strftime('%Y-%m-%d')
        cliente_nome_str = f"{cliente_empresa} ({session.get('user_nome', 'User')})"
        
        r = criar_pedido(
            forn_id,
            cliente_nome_str,
            data_hoje,
            itens,
            cliente_id=get_empresa_id(),
            data_entrega=data_entrega,
            mensagem_cliente=mensagem_cliente,
            forma_pagamento=forma_pagamento
        )
        
        if r.get('sucesso'):
            return jsonify({'sucesso': True, 'mensagem': 'Pedido realizado com sucesso!'})
        else:
            return jsonify(r), 400
            
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': f"Erro interno: {str(e)}"}), 500


# ═══════════════════════════════════════════
# AVISOS API
# ═══════════════════════════════════════════

@app.route('/api/avisos', methods=['GET'])
@login_required
def api_avisos():
    nao_lidos = request.args.get('nao_lidos') == '1'
    return jsonify(obter_avisos(get_empresa_id(), nao_lidos_somente=nao_lidos))


@app.route('/api/avisos', methods=['POST'])
@login_required
def api_criar_aviso():
    data = request.get_json(force=True, silent=True) or {}
    titulo = (data.get('titulo') or '').strip()
    if not titulo:
        return jsonify({'sucesso': False, 'mensagem': 'Título é obrigatório'}), 400
    r = criar_aviso(get_empresa_id(), data.get('tipo', 'info'), titulo,
                    data.get('mensagem', ''), data.get('prioridade', 'normal'),
                    data.get('data_agendada'))
    return jsonify(r), 201 if r.get('sucesso') else 400


@app.route('/api/avisos/<int:aid>/lido', methods=['PUT'])
@login_required
def api_marcar_aviso_lido(aid):
    return jsonify(marcar_aviso_lido(get_empresa_id(), aid))


@app.route('/api/avisos/<int:aid>', methods=['DELETE'])
@login_required
def api_deletar_aviso(aid):
    return jsonify(deletar_aviso(get_empresa_id(), aid))


@app.route('/api/avisos/count', methods=['GET'])
@login_required
def api_contar_avisos():
    return jsonify({'count': contar_avisos_nao_lidos(get_empresa_id())})


# ═══════════════════════════════════════════
# PERFIL DA LOJA API
# ═══════════════════════════════════════════

@app.route('/api/perfil-loja', methods=['GET'])
@login_required
def api_get_perfil_loja():
    return jsonify(obter_perfil_loja(get_empresa_id()) or {})


@app.route('/api/perfil-loja', methods=['POST', 'PUT'])
@login_required
def api_salvar_perfil_loja():
    data = request.get_json(force=True, silent=True) or {}
    r = salvar_perfil_loja(
        get_empresa_id(),
        nome_loja=data.get('nome_loja'),
        descricao=data.get('descricao'),
        cor_principal=data.get('cor_principal'),
        cor_secundaria=data.get('cor_secundaria'),
        horario_funcionamento=data.get('horario_funcionamento'),
        formas_pagamento=data.get('formas_pagamento'),
        link_whatsapp=data.get('link_whatsapp'),
        link_instagram=data.get('link_instagram'),
        link_facebook=data.get('link_facebook'),
    )
    return jsonify(r)


# ═══════════════════════════════════════════
# NOTIFICAÇÕES API
# ═══════════════════════════════════════════

@app.route('/api/notificacoes', methods=['GET'])
@login_required
def api_notificacoes():
    nao_lidas = request.args.get('nao_lidas') == '1'
    return jsonify(obter_notificacoes(get_empresa_id(), nao_lidas_somente=nao_lidas))

@app.route('/api/notificacoes', methods=['POST'])
@login_required
def api_criar_notificacao():
    data = request.get_json(force=True, silent=True) or {}
    r = criar_notificacao(
        get_empresa_id(),
        data.get('tipo', 'info'),
        data.get('titulo', ''),
        data.get('mensagem', ''),
        cliente_id=data.get('cliente_id'),
        fornecedor_id=data.get('fornecedor_id')
    )
    return jsonify(r), 201 if r.get('sucesso') else 400

@app.route('/api/notificacoes/<int:nid>/lido', methods=['PUT'])
@login_required
def api_marcar_notificacao_lida(nid):
    return jsonify(marcar_notificacao_lida(get_empresa_id(), nid))

@app.route('/api/notificacoes/<int:nid>', methods=['DELETE'])
@login_required
def api_deletar_notificacao(nid):
    return jsonify(deletar_notificacao(get_empresa_id(), nid))

@app.route('/api/notificacoes/count', methods=['GET'])
@login_required
def api_contar_notificacoes():
    return jsonify({'count': contar_notificacoes_nao_lidas(get_empresa_id())})


# ═══════════════════════════════════════════
# COMPARTILHAMENTO DE VITRINE API
# ═══════════════════════════════════════════

@app.route('/api/vitrine/compartilhar', methods=['POST'])
@login_required
def api_compartilhar_vitrine():
    if session.get('empresa_tipo') != 'fornecedor':
        return jsonify({'sucesso': False, 'mensagem': 'Apenas fornecedores podem compartilhar'}), 403

    data = request.get_json(force=True, silent=True) or {}
    try:
        cliente_id = int(data.get('cliente_id'))
        metodo = (data.get('metodo') or 'convite').strip()
    except:
        return jsonify({'sucesso': False, 'mensagem': 'Dados inválidos'}), 400

    r = compartilhar_vitrine(get_empresa_id(), cliente_id, metodo)
    if r.get('sucesso'):
        if metodo == 'convite':
            criar_notificacao(
                cliente_id,
                'convite',
                f'{session.get("empresa_nome")} compartilhou sua vitrine com você!',
                f'Acesse o catálogo de produtos de {session.get("empresa_nome")}',
                cliente_id=cliente_id,
                fornecedor_id=get_empresa_id()
            )
    return jsonify(r), 201 if r.get('sucesso') else 400

@app.route('/api/vitrine/fornecedores', methods=['GET'])
@login_required
def api_obter_fornecedores_compartilhados():
    if session.get('empresa_tipo') != 'cliente':
        return jsonify({'sucesso': False, 'mensagem': 'Apenas clientes podem acessar'}), 403

    aceitos = request.args.get('aceitos') == '1'
    return jsonify(obter_fornecedores_compartilhados(get_empresa_id(), aceitos_somente=aceitos))

@app.route('/api/vitrine/<int:comp_id>/aceitar', methods=['PUT'])
@login_required
def api_aceitar_compartilhamento(comp_id):
    if session.get('empresa_tipo') != 'cliente':
        return jsonify({'sucesso': False, 'mensagem': 'Apenas clientes'}), 403
    return jsonify(aceitar_compartilhamento(get_empresa_id(), comp_id))

@app.route('/api/vitrine/<int:forn_id>/visitantes', methods=['GET'])
@login_required
def api_obter_visitantes(forn_id):
    if session.get('empresa_tipo') != 'fornecedor' or get_empresa_id() != forn_id:
        return jsonify({'sucesso': False, 'mensagem': 'Acesso negado'}), 403
    return jsonify(obter_visitantes_vitrine(forn_id))


# ═══════════════════════════════════════════
# RELATÓRIOS API
# ═══════════════════════════════════════════

@app.route('/api/relatorio/fornecedor', methods=['GET'])
@login_required
def api_relatorio_fornecedor():
    if session.get('empresa_tipo') != 'fornecedor':
        return jsonify({'sucesso': False, 'mensagem': 'Apenas fornecedores'}), 403
    return jsonify(obter_relatorio_fornecedor(get_empresa_id()))

@app.route('/api/relatorio/cliente', methods=['GET'])
@login_required
def api_relatorio_cliente():
    if session.get('empresa_tipo') != 'cliente':
        return jsonify({'sucesso': False, 'mensagem': 'Apenas clientes'}), 403
    return jsonify(obter_relatorio_cliente(get_empresa_id()))


# ═══════════════════════════════════════════
# LISTAGENS GERAIS
# ═══════════════════════════════════════════

@app.route('/api/fornecedores', methods=['GET'])
@login_required
def api_listar_fornecedores():
    return jsonify(listar_fornecedores())


@app.route('/api/clientes', methods=['GET'])
@login_required
def api_listar_clientes():
    return jsonify(listar_clientes())


# ═══════════════════════════════════════════
# START
# ═══════════════════════════════════════════

init_db()

if __name__ == '__main__':
    app.run(debug=True, port=8080)