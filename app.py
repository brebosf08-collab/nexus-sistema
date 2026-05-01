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
    criar_pedido, obter_pedidos, obter_pedido_detalhado, atualizar_status_pedido,
    obter_historico,
    criar_reuniao, obter_reunioes, atualizar_status_reuniao, deletar_reuniao,
    criar_contato, obter_contatos, deletar_contato,
    obter_dashboard,
    criar_aviso, obter_avisos, contar_avisos_nao_lidos, marcar_aviso_lido, deletar_aviso,
    salvar_perfil_loja, obter_perfil_loja, listar_fornecedores, listar_clientes,
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


@app.route('/loja/<int:forn_id>')
def vitrine_fornecedor(forn_id):
    """Página pública da loja/vitrine do fornecedor"""
    fornecedor = obter_empresa(forn_id)
    if not fornecedor or fornecedor.get('tipo') != 'fornecedor':
        abort(404)
    produtos = obter_produtos(forn_id)
    return render_template('vitrine.html', fornecedor=fornecedor, produtos=produtos)


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
        # Busca o usuário e a empresa vinculada no banco
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
    
    print(f">>> Tentando criar categoria: '{nome}' para empresa: {empresa_id}")
    
    if not nome:
        return jsonify({'sucesso': False, 'mensagem': 'Nome da categoria é obrigatório'}), 400
    if not empresa_id:
        return jsonify({'sucesso': False, 'mensagem': 'Sessão inválida. Faça login novamente.'}), 401
        
    r = criar_categoria(empresa_id, nome)
    if not r.get('sucesso'):
        print(f"!!! Erro no banco ao criar categoria: {r.get('mensagem')}")
        return jsonify(r), 400
        
    print(f"✅ Categoria criada com sucesso: ID {r.get('id')}")
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
    data = request.form if request.form else request.get_json(force=True, silent=True) or {}
    empresa_id = get_empresa_id()
    
    nome = (data.get('nome') or '').strip()
    print(f">>> Tentando criar produto: '{nome}' para empresa: {empresa_id}")

    if not nome:
        return jsonify({'sucesso': False, 'mensagem': 'Nome do produto é obrigatório'}), 400
    if not empresa_id:
        return jsonify({'sucesso': False, 'mensagem': 'Sessão inválida. Faça login novamente.'}), 401

    # Imagem upload
    imagem_filename = None
    if 'imagem' in request.files:
        img_file = request.files['imagem']
        if img_file and img_file.filename != '':
            ext = img_file.filename.rsplit('.', 1)[-1].lower()
            filename = secure_filename(f"{uuid.uuid4().hex}.{ext}")
            img_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            imagem_filename = filename

    # Tratamento de valores numéricos
    def to_float(val):
        try: return float(str(val).replace(',', '.'))
        except: return 0.0
    def to_int(val):
        try: return int(val)
        except: return 0

    categoria_nome = (data.get('categoria_nome') or '').strip()
    cat_id = data.get('categoria_id')
    if cat_id:
        try:
            cat_id = int(cat_id)
        except:
            cat_id = None

    if not cat_id and categoria_nome:
        cat_res = criar_categoria(empresa_id, categoria_nome)
        if not cat_res.get('sucesso'):
            return jsonify(cat_res), 400
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
        print(f"!!! Erro no banco ao criar produto: {r.get('mensagem')}")
        return jsonify(r), 400
        
    print(f"✅ Produto criado com sucesso: ID {r.get('id')}")
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

    if not cliente:
        return jsonify({'sucesso': False, 'mensagem': 'Nome do cliente é obrigatório'}), 400
    if not data_pedido:
        return jsonify({'sucesso': False, 'mensagem': 'Data é obrigatória'}), 400
    if not itens:
        return jsonify({'sucesso': False, 'mensagem': 'Adicione ao menos um item ao pedido'}), 400

    r = criar_pedido(get_empresa_id(), cliente, data_pedido, itens, vendedor_id, obs)
    if not r.get('sucesso'):
        return jsonify(r), 400
    return jsonify(r), 201


@app.route('/api/pedidos/<int:pid>', methods=['GET'])
@login_required
def api_pedido_detalhe(pid):
    d = obter_pedido_detalhado(get_empresa_id(), pid)
    if not d:
        abort(404)
    return jsonify(d)


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
    # Retorna lista de empresas do tipo fornecedor
    try:
        res = supabase.table('empresas').select('id, nome, email, telefone, endereco').eq('tipo', 'fornecedor').execute()
        return jsonify(res.data)
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500

@app.route('/api/catalogo/fornecedores/<int:forn_id>/produtos', methods=['GET'])
@login_required
def api_catalogo_produtos(forn_id):
    # Retorna lista de produtos de um fornecedor específico
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

    if qtd <= 0:
        return jsonify({'sucesso': False, 'mensagem': 'Quantidade deve ser maior que zero'}), 400
    
    # Buscar produto para validar estoque e preço
    try:
        r_prod = supabase.table('produtos').select('nome, preco, quantidade').eq('id', prod_id).eq('empresa_id', forn_id).execute()
        if not r_prod.data:
            return jsonify({'sucesso': False, 'mensagem': 'Produto não encontrado no fornecedor'}), 404
            
        prod = r_prod.data[0]
        if prod['quantidade'] < qtd:
            return jsonify({'sucesso': False, 'mensagem': 'Estoque insuficiente no fornecedor'}), 400

        # Obter nome do cliente da sessão ou banco
        cliente_empresa = session.get('empresa_nome', 'Cliente')
            
        # Preparar itens para o criar_pedido
        total = float(prod['preco']) * qtd
        itens = [{
            'produto_id': prod_id,
            'quantidade': qtd,
            'preco': float(prod['preco']),
            'subtotal': total
        }]
        
        data_hoje = datetime.date.today().strftime('%Y-%m-%d')
        cliente_nome_str = f"{cliente_empresa} ({session.get('user_nome', 'User')})"
        
        # Cria o pedido (o criar_pedido já desconta estoque e gera histórico)
        r = criar_pedido(forn_id, cliente_nome_str, data_hoje, itens, cliente_id=get_empresa_id())
        
        if r.get('sucesso'):
            return jsonify({'sucesso': True, 'mensagem': 'Pedido realizado com sucesso!'})
        else:
            return jsonify(r), 400
            
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': f"Erro interno: {str(e)}"}), 500


# ═══════════════════════════════════════════
# START
# ═══════════════════════════════════════════

init_db()

if __name__ == '__main__':
    # Em produção, use um servidor como Gunicorn
    app.run(debug=True, port=8080)
