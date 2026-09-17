import os
import uuid
import datetime
import json
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, abort, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Aviso: Módulo 'python-dotenv' não encontrado. Usando variáveis de ambiente do sistema.")

# Importar novos módulos de funcionalidades de forma independente.
# Assim uma dependência opcional não derruba recursos que já estão disponíveis.
try:
    from modulos.produtos import (
        criar_produto_completo, atualizar_estoque, obter_movimentos_produto,
        criar_alerta_estoque_baixo, obter_alertas_estoque, obter_estatisticas_inventario
    )
    PRODUTOS_MODULO_CARREGADO = True
except ImportError as produto_err:
    print(f"Aviso: módulo de produtos indisponível: {produto_err}")
    PRODUTOS_MODULO_CARREGADO = False

try:
    from modulos.agendamento import (
        criar_agendamento, obter_agendamentos, atualizar_agendamento,
        cancelar_agendamento, concluir_agendamento, deletar_agendamento,
        obter_proximos_agendamentos, obter_agendamentos_atrasados
    )
    AGENDAMENTO_MODULO_CARREGADO = True
except ImportError as agendamento_err:
    print(f"Aviso: módulo de agendamento indisponível: {agendamento_err}")
    AGENDAMENTO_MODULO_CARREGADO = False

try:
    from modulos.notificacoes import (
        criar_notificacao as criar_notif_nova,
        obter_notificacoes as obter_notif_nova,
        contar_notificacoes_nao_lidas as contar_notif_nao_lidas,
        marcar_notificacao_lida as marcar_notif_lida,
        deletar_notificacao as deletar_notif_nova,
        enviar_email_notificacao, template_email_notificacao_estoque,
        obter_preferencias_notificacao, salvar_preferencias_notificacao
    )
    NOTIFICACOES_MODULO_CARREGADO = True
except ImportError as notificacoes_err:
    print(f"Aviso: módulo de notificações indisponível: {notificacoes_err}")
    NOTIFICACOES_MODULO_CARREGADO = False

# Exportação desativada. O fluxo de estoque agora fica todo dentro do sistema,
# sem depender de planilhas/CSV.
EXPORTACAO_MODULO_CARREGADO = False

try:
    from modulos.carrinho import (
        adicionar_ao_carrinho, obter_carrinho, remover_do_carrinho,
        atualizar_quantidade_carrinho, limpar_carrinho, converter_carrinho_em_pedido,
        obter_resumo_carrinho
    )
    CARRINHO_MODULO_CARREGADO = True
except ImportError as carrinho_err:
    print(f"Aviso: módulo de carrinho indisponível: {carrinho_err}")
    CARRINHO_MODULO_CARREGADO = False

MODULOS_CARREGADOS = all((
    PRODUTOS_MODULO_CARREGADO,
    AGENDAMENTO_MODULO_CARREGADO,
    NOTIFICACOES_MODULO_CARREGADO,
    EXPORTACAO_MODULO_CARREGADO,
    CARRINHO_MODULO_CARREGADO,
))

# Importação centralizada do banco
from supabase_db import (
    supabase, init_db,
    registrar_empresa, autenticar_usuario, obter_empresa,
    criar_categoria, obter_categorias, deletar_categoria,
    criar_produto, obter_produtos, obter_produto, atualizar_produto, deletar_produto,
    adicionar_estoque, retirar_estoque,
    criar_materia_prima, obter_materias_primas, atualizar_materia_prima, deletar_materia_prima,
    salvar_composicao_produto, calcular_materias_primas_produto,
    adicionar_estoque_materia_prima, retirar_estoque_materia_prima, registrar_ordem_producao,
    criar_vendedor, obter_vendedores, deletar_vendedor,
    criar_pedido, obter_pedidos, obter_pedido_detalhado, atualizar_status_pedido, atualizar_pedido,
    analisar_pedidos_estoque,
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

MATERIA_PRIMA_MARKER = '[DADOS_MATERIA_PRIMA] '
MATERIAS_PRODUTO_MARKER = '[MATERIAS_PRIMAS_PRODUTO] '
TIPO_ITEM_MARKER = '[TIPO_ITEM] '
MATERIA_ESTOQUE_MARKER = '[ESTOQUE_MATERIA_PRIMA] '
TEMPO_PRODUTO_MARKER = '[TEMPO_PRODUTO] '


def _to_float_safe(val):
    try:
        return float(str(val or 0).replace(',', '.'))
    except:
        return 0.0


def _to_int_safe(val):
    try:
        return int(float(str(val or 0).replace(',', '.')))
    except:
        return 0


def extrair_materia_prima(data):
    nome = (data.get('materia_prima_nome') or '').strip()
    quantidade = _to_float_safe(data.get('materia_prima_quantidade', 0))
    minimo = _to_float_safe(data.get('materia_prima_minimo', 0))
    unidade = (data.get('materia_prima_unidade') or 'kg').strip() or 'kg'

    if not nome and quantidade <= 0 and minimo <= 0:
        return None

    return {
        'nome': nome or 'Matéria-prima',
        'quantidade': quantidade,
        'unidade': unidade,
        'minimo': minimo,
    }


def anexar_materia_prima_descricao(descricao, materia_prima):
    descricao = (descricao or '').strip()
    if MATERIA_PRIMA_MARKER in descricao:
        descricao = descricao.split(MATERIA_PRIMA_MARKER, 1)[0].strip()
    if not materia_prima:
        return descricao
    payload = json.dumps(materia_prima, ensure_ascii=False, separators=(',', ':'))
    return f"{descricao}\n\n{MATERIA_PRIMA_MARKER}{payload}".strip()


def limpar_marcadores_descricao(descricao):
    linhas = []
    for linha in (descricao or '').splitlines():
        if linha.startswith((MATERIA_PRIMA_MARKER, MATERIAS_PRODUTO_MARKER, TIPO_ITEM_MARKER, MATERIA_ESTOQUE_MARKER, TEMPO_PRODUTO_MARKER)):
            continue
        linhas.append(linha)
    return '\n'.join(linhas).strip()


def extrair_materias_produto(data):
    raw = data.get('materias_primas_json') or data.get('materias_primas') or ''
    if not raw:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return []
    materias = []
    for item in raw if isinstance(raw, list) else []:
        try:
            materia_id = item.get('materia_prima_id') or item.get('id')
            quantidade = _to_float_safe(item.get('quantidade_por_produto') or item.get('quantidade') or 0)
            tipo_calculo = (item.get('tipo_calculo') or 'quantidade').strip()
            percentual = _to_float_safe(item.get('percentual') or 0)
        except AttributeError:
            continue
        valor_valido = percentual > 0 if tipo_calculo == 'percentual' else quantidade > 0
        if not materia_id or not valor_valido:
            continue
        materias.append({
            'materia_prima_id': int(materia_id),
            'nome': (item.get('nome') or '').strip(),
            'unidade': (item.get('unidade') or 'kg').strip() or 'kg',
            'tipo_calculo': tipo_calculo,
            'quantidade_por_produto': quantidade,
            'percentual': percentual if tipo_calculo == 'percentual' else 0,
        })
    return materias


def anexar_materias_produto_descricao(descricao, materias):
    descricao = limpar_marcadores_descricao(descricao)
    if not materias:
        return descricao
    payload = json.dumps(materias, ensure_ascii=False, separators=(',', ':'))
    return f"{descricao}\n\n{MATERIAS_PRODUTO_MARKER}{payload}".strip()


def extrair_tempo_produto(data):
    tempo_preparo = _to_int_safe(data.get('tempo_preparo', 0))
    unidade = (data.get('tempo_preparo_unidade') or 'minutos').strip() or 'minutos'
    if tempo_preparo <= 0:
        return None
    return {
        'tempo_preparo': tempo_preparo,
        'tempo_preparo_unidade': unidade,
    }


def anexar_tempo_produto_descricao(descricao, tempo):
    descricao = limpar_marcadores_descricao(descricao)
    if not tempo:
        return descricao
    payload = json.dumps(tempo, ensure_ascii=False, separators=(',', ':'))
    return f"{descricao}\n\n{TEMPO_PRODUTO_MARKER}{payload}".strip()


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
    if not (
        any(c.islower() for c in senha)
        and any(c.isupper() for c in senha)
        and any(c.isdigit() for c in senha)
        and any(not c.isalnum() for c in senha)
    ):
        return jsonify({
            'sucesso': False,
            'mensagem': 'A senha precisa ter letra maiúscula, letra minúscula, número e símbolo. Exemplo: Sistema@123'
        }), 400

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


@app.route('/api/estoque/produtos', methods=['GET'])
@login_required
def api_estoque_produtos():
    return jsonify(obter_produtos(get_empresa_id()))


@app.route('/api/estoque/materias-primas', methods=['GET'])
@login_required
def api_estoque_materias_primas():
    return jsonify(obter_materias_primas(get_empresa_id()))


@app.route('/api/produtos', methods=['POST'])
@login_required
def api_criar_produto():
    if session.get('empresa_tipo') != 'fornecedor':
        return jsonify({'sucesso': False, 'mensagem': 'Apenas fornecedores podem cadastrar produtos'}), 403

    # Aceita tanto form-data (com imagem) quanto JSON
    if request.content_type and 'multipart' in request.content_type:
        data = request.form.to_dict()
    else:
        data = request.get_json(force=True, silent=True) or {}

    empresa_id = get_empresa_id()
    if not empresa_id:
        return jsonify({'sucesso': False, 'mensagem': 'Sessão inválida. Faça login novamente.'}), 401

    # Upload de imagem
    imagem_url = None
    if 'imagem' in request.files:
        img_file = request.files['imagem']
        if img_file and img_file.filename != '':
            ext = img_file.filename.rsplit('.', 1)[-1].lower()
            if ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
                filename = secure_filename(f"{uuid.uuid4().hex}.{ext}")
                img_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                imagem_url = f"/static/uploads/{filename}"

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
        else:
            return jsonify(cat_res), 400

    materias_produto = extrair_materias_produto(data)
    descricao = anexar_materias_produto_descricao(data.get('descricao', ''), materias_produto)
    descricao = anexar_tempo_produto_descricao(descricao, extrair_tempo_produto(data))

    dados_produto = {
        'nome': (data.get('nome') or '').strip(),
        'sku': data.get('sku', ''),
        'categoria_id': cat_id,
        'custo': to_float(data.get('custo', 0)),
        'preco': to_float(data.get('preco', 0)),
        'quantidade': to_int(data.get('quantidade', 0)),
        'minimo': to_int(data.get('minimo', 0)),
        'descricao': descricao,
        'imagem_url': imagem_url or data.get('imagem_url', ''),
        'codigo_barras': data.get('codigo_barras', ''),
        'materias_primas': materias_produto,
    }

    if not dados_produto['nome']:
        return jsonify({'sucesso': False, 'mensagem': 'Nome do produto é obrigatório'}), 400

    resultado = criar_produto(
        empresa_id,
        dados_produto['nome'],
        dados_produto['sku'],
        dados_produto['categoria_id'],
        dados_produto['custo'],
        dados_produto['preco'],
        dados_produto['quantidade'],
        dados_produto['minimo'],
        dados_produto['descricao'],
        dados_produto['imagem_url']
    )

    if not resultado.get('sucesso'):
        resultado['mensagem'] = resultado.get('mensagem') or resultado.get('erro') or 'Erro ao cadastrar produto'
        return jsonify(resultado), 400

    produto_id = resultado.get('produto_id') or resultado.get('id')
    if produto_id and materias_produto:
        salvar_composicao_produto(empresa_id, produto_id, materias_produto)

    if resultado.get('sucesso'):
        try:
            criar_aviso(
                empresa_id,
                'produto',
                '✓ Produto Cadastrado',
                f"Novo produto '{dados_produto.get('nome')}' cadastrado com sucesso",
                'normal'
            )
        except Exception:
            pass

    return jsonify(resultado), 201


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
# MATÉRIAS-PRIMAS API
# ═══════════════════════════════════════════

@app.route('/api/materias-primas', methods=['GET'])
@login_required
def api_materias_primas():
    return jsonify(obter_materias_primas(get_empresa_id()))


@app.route('/api/materias-primas', methods=['POST'])
@login_required
def api_criar_materia_prima():
    if session.get('empresa_tipo') != 'fornecedor':
        return jsonify({'sucesso': False, 'mensagem': 'Apenas fornecedores podem cadastrar matéria-prima'}), 403
    data = request.get_json(force=True, silent=True) or {}
    r = criar_materia_prima(
        get_empresa_id(),
        data.get('nome', ''),
        unidade=data.get('unidade', 'kg'),
        quantidade=_to_float_safe(data.get('quantidade', 0)),
        minimo=_to_float_safe(data.get('minimo', 0)),
        custo_unitario=_to_float_safe(data.get('custo_unitario', 0)),
        sku=data.get('sku', ''),
        descricao=data.get('descricao', '')
    )
    if not r.get('sucesso'):
        return jsonify(r), 400
    return jsonify(r), 201


@app.route('/api/materias-primas/<int:mid>', methods=['PUT'])
@login_required
def api_atualizar_materia_prima(mid):
    data = request.get_json(force=True, silent=True) or {}
    r = atualizar_materia_prima(get_empresa_id(), mid, data)
    if not r.get('sucesso'):
        return jsonify(r), 400
    return jsonify(r)


@app.route('/api/materias-primas/<int:mid>', methods=['DELETE'])
@login_required
def api_deletar_materia_prima(mid):
    return jsonify(deletar_materia_prima(get_empresa_id(), mid))


@app.route('/api/materias-primas/<int:mid>/entrada', methods=['POST'])
@login_required
def api_entrada_materia_prima(mid):
    data = request.get_json(force=True, silent=True) or {}
    qtd = _to_float_safe(data.get('quantidade', 0))
    if qtd <= 0:
        return jsonify({'sucesso': False, 'mensagem': 'Quantidade deve ser positiva'}), 400
    r = adicionar_estoque_materia_prima(get_empresa_id(), mid, qtd, data.get('observacoes') or 'Entrada de matéria-prima')
    if not r.get('sucesso'):
        return jsonify(r), 400
    return jsonify(r)


@app.route('/api/materias-primas/<int:mid>/saida', methods=['POST'])
@login_required
def api_saida_materia_prima(mid):
    data = request.get_json(force=True, silent=True) or {}
    qtd = _to_float_safe(data.get('quantidade', 0))
    if qtd <= 0:
        return jsonify({'sucesso': False, 'mensagem': 'Quantidade deve ser positiva'}), 400
    r = retirar_estoque_materia_prima(get_empresa_id(), mid, qtd, data.get('observacoes') or 'Saída de matéria-prima')
    if not r.get('sucesso'):
        return jsonify(r), 400
    return jsonify(r)


@app.route('/api/producao/ordem', methods=['POST'])
@login_required
def api_ordem_producao():
    if session.get('empresa_tipo') != 'fornecedor':
        return jsonify({'sucesso': False, 'mensagem': 'Apenas fornecedores podem registrar produção'}), 403
    data = request.get_json(force=True, silent=True) or {}
    try:
        produto_id = int(data.get('produto_id'))
    except Exception:
        return jsonify({'sucesso': False, 'mensagem': 'Produto inválido'}), 400
    r = registrar_ordem_producao(
        get_empresa_id(),
        produto_id,
        _to_float_safe(data.get('quantidade', 0)),
        observacoes=data.get('observacoes', ''),
        data_producao=data.get('data_producao')
    )
    return jsonify(r), 200 if r.get('sucesso') else 400


@app.route('/api/ia/materias-primas/calcular', methods=['POST'])
@login_required
def api_ia_calcular_materias_primas():
    if session.get('empresa_tipo') != 'fornecedor':
        return jsonify({'sucesso': False, 'mensagem': 'Apenas fornecedores podem calcular produção'}), 403

    data = request.get_json(force=True, silent=True) or {}
    try:
        produto_id = int(data.get('produto_id'))
        quantidade = _to_float_safe(data.get('quantidade'))
    except Exception:
        return jsonify({'sucesso': False, 'mensagem': 'Produto ou quantidade inválidos'}), 400

    r = calcular_materias_primas_produto(get_empresa_id(), produto_id, quantidade)
    return jsonify(r), 200 if r.get('sucesso') else 400


# ═══════════════════════════════════════════════════════════════
# PRODUTOS V2 - COM INVENTÁRIO COMPLETO (NOVO)
# ═══════════════════════════════════════════════════════════════

@app.route('/api/v2/produtos', methods=['POST'])
@login_required
def api_criar_produto_v2():
    """Cria produto com validações e integração com inventário completa"""
    if not PRODUTOS_MODULO_CARREGADO:
        return jsonify({'sucesso': False, 'mensagem': 'Módulo de produtos não disponível'}), 503
    
    if session.get('empresa_tipo') != 'fornecedor':
        return jsonify({'sucesso': False, 'mensagem': 'Apenas fornecedores podem cadastrar produtos'}), 403
    
    # Aceita tanto form-data (com imagem) quanto JSON
    if request.content_type and 'multipart' in request.content_type:
        data = request.form.to_dict()
    else:
        data = request.get_json(force=True, silent=True) or {}
    
    empresa_id = get_empresa_id()
    
    # Upload de imagem
    imagem_url = None
    if 'imagem' in request.files:
        img_file = request.files['imagem']
        if img_file and img_file.filename != '':
            ext = img_file.filename.rsplit('.', 1)[-1].lower()
            if ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
                filename = secure_filename(f"{uuid.uuid4().hex}.{ext}")
                img_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                imagem_url = f"/static/uploads/{filename}"
    
    def to_float(val):
        try: return float(str(val or 0).replace(',', '.'))
        except: return 0.0
    
    def to_int(val):
        try: return int(val or 0)
        except: return 0
    
    # Preparar dados do produto
    materias_produto = extrair_materias_produto(data)
    descricao = anexar_materias_produto_descricao(data.get('descricao', ''), materias_produto)
    descricao = anexar_tempo_produto_descricao(descricao, extrair_tempo_produto(data))
    dados_produto = {
        'nome': data.get('nome', ''),
        'sku': data.get('sku', ''),
        'categoria_id': to_int(data.get('categoria_id')) or None,
        'custo': to_float(data.get('custo')),
        'preco': to_float(data.get('preco')),
        'quantidade': to_int(data.get('quantidade')),
        'minimo': to_int(data.get('minimo')),
        'descricao': descricao,
        'imagem_url': imagem_url or data.get('imagem_url', ''),
        'codigo_barras': data.get('codigo_barras', ''),
        'materias_primas': materias_produto,
    }
    
    resultado = criar_produto_completo(empresa_id, dados_produto)
    
    if resultado.get('sucesso'):
        try:
            criar_aviso(
                empresa_id,
                'produto',
                '✓ Produto Cadastrado',
                f"Novo produto '{dados_produto.get('nome')}' foi cadastrado com sucesso",
                'normal'
            )
        except Exception:
            pass
        
        return jsonify(resultado), 201
    
    return jsonify(resultado), 400


@app.route('/api/v2/estoque/<int:pid>', methods=['PUT'])
@login_required
def api_atualizar_estoque_v2(pid):
    """Atualiza estoque com histórico automático"""
    if not PRODUTOS_MODULO_CARREGADO:
        return jsonify({'sucesso': False, 'mensagem': 'Módulo de produtos não disponível'}), 503
    
    data = request.get_json(force=True, silent=True) or {}
    
    try:
        quantidade = int(data.get('quantidade'))
    except:
        return jsonify({'sucesso': False, 'erro': 'Quantidade inválida'}), 400
    
    motivo = data.get('motivo', 'Ajuste manual')
    resultado = atualizar_estoque(pid, quantidade, motivo)
    
    if resultado.get('sucesso'):
        try:
            criar_aviso(
                get_empresa_id(),
                'estoque',
                '📦 Estoque Atualizado',
                f"Estoque atualizado: {motivo}",
                'normal'
            )
        except Exception:
            pass
    
    return jsonify(resultado), 200 if resultado.get('sucesso') else 400


@app.route('/api/v2/movimentos/<int:pid>', methods=['GET'])
@login_required
def api_obter_movimentos_v2(pid):
    """Retorna histórico de movimentos de estoque"""
    if not PRODUTOS_MODULO_CARREGADO:
        return jsonify([]), 200
    
    limite = request.args.get('limite', 50, type=int)
    movimentos = obter_movimentos_produto(pid, limite)
    
    return jsonify(movimentos), 200


@app.route('/api/v2/inventario/estadisticas', methods=['GET'])
@login_required
def api_estadisticas_inventario_v2():
    """Retorna estatísticas de inventário da empresa"""
    if not PRODUTOS_MODULO_CARREGADO:
        return jsonify({'erro': 'Módulo de produtos não disponível'}), 503
    
    stats = obter_estatisticas_inventario(get_empresa_id())
    return jsonify(stats), 200


@app.route('/api/v2/alertas-estoque', methods=['GET'])
@login_required
def api_obter_alertas_estoque_v2():
    """Retorna alertas de estoque baixo"""
    if not PRODUTOS_MODULO_CARREGADO:
        return jsonify([]), 200
    
    filtro_status = request.args.get('status', 'aberto')
    alertas = obter_alertas_estoque(get_empresa_id(), filtro_status)
    
    return jsonify(alertas), 200


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


@app.route('/api/pedidos/analise', methods=['GET'])
@login_required
def api_analise_pedidos():
    if session.get('empresa_tipo') != 'fornecedor':
        return jsonify({'sucesso': False, 'mensagem': 'Apenas fornecedor pode analisar pedidos'}), 403
    r = analisar_pedidos_estoque(get_empresa_id())
    return jsonify(r), 200 if r.get('sucesso') else 400


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
    r = atualizar_status_pedido(get_empresa_id(), pid, status)
    return jsonify(r), 200 if r.get('sucesso') else 400


# ═══════════════════════════════════════════
# CARRINHO DE COMPRAS API
# ═══════════════════════════════════════════

@app.route('/api/carrinho', methods=['GET'])
@login_required
def api_obter_carrinho():
    """Retorna o carrinho do cliente logado"""
    if not CARRINHO_MODULO_CARREGADO:
        return jsonify({'itens': [], 'total_itens': 0, 'total_geral': 0}), 200
    
    fornecedor_id = request.args.get('fornecedor_id', type=int)
    carrinho = obter_carrinho(get_empresa_id(), fornecedor_id)
    
    return jsonify(carrinho), 200


@app.route('/api/carrinho/resumo', methods=['GET'])
@login_required
def api_resumo_carrinho():
    """Retorna resumo rápido do carrinho"""
    if not CARRINHO_MODULO_CARREGADO:
        return jsonify({'total_itens': 0, 'total_geral': 0, 'quantidade_produtos': 0}), 200
    
    resumo = obter_resumo_carrinho(get_empresa_id())
    
    return jsonify(resumo), 200


@app.route('/api/carrinho/adicionar', methods=['POST'])
@login_required
def api_adicionar_carrinho():
    """Adiciona produto ao carrinho"""
    if not CARRINHO_MODULO_CARREGADO:
        return jsonify({'sucesso': False, 'erro': 'Módulo não disponível'}), 503
    
    if session.get('empresa_tipo') != 'cliente':
        return jsonify({'sucesso': False, 'erro': 'Apenas clientes podem usar carrinho'}), 403
    
    data = request.get_json(force=True, silent=True) or {}
    
    try:
        produto_id = int(data.get('produto_id'))
        fornecedor_id = int(data.get('fornecedor_id'))
        quantidade = int(data.get('quantidade', 1))
    except:
        return jsonify({'sucesso': False, 'erro': 'Dados inválidos'}), 400
    
    resultado = adicionar_ao_carrinho(get_empresa_id(), produto_id, quantidade, fornecedor_id)
    
    status = 200 if resultado.get('sucesso') else 400
    return jsonify(resultado), status


@app.route('/api/carrinho/<int:item_id>', methods=['DELETE'])
@login_required
def api_remover_carrinho(item_id):
    """Remove item do carrinho"""
    if not CARRINHO_MODULO_CARREGADO:
        return jsonify({'sucesso': False}), 503
    
    if session.get('empresa_tipo') != 'cliente':
        return jsonify({'sucesso': False}), 403
    
    resultado = remover_do_carrinho(item_id, get_empresa_id())
    
    status = 200 if resultado.get('sucesso') else 400
    return jsonify(resultado), status


@app.route('/api/carrinho/<int:item_id>', methods=['PUT'])
@login_required
def api_atualizar_carrinho(item_id):
    """Atualiza quantidade de item no carrinho"""
    if not CARRINHO_MODULO_CARREGADO:
        return jsonify({'sucesso': False}), 503
    
    if session.get('empresa_tipo') != 'cliente':
        return jsonify({'sucesso': False}), 403
    
    data = request.get_json(force=True, silent=True) or {}
    
    try:
        nova_quantidade = int(data.get('quantidade', 0))
    except:
        return jsonify({'sucesso': False, 'erro': 'Quantidade inválida'}), 400
    
    resultado = atualizar_quantidade_carrinho(item_id, nova_quantidade, get_empresa_id())
    
    status = 200 if resultado.get('sucesso') else 400
    return jsonify(resultado), status


@app.route('/api/carrinho/limpar', methods=['DELETE'])
@login_required
def api_limpar_carrinho():
    """Remove todos os items do carrinho"""
    if not CARRINHO_MODULO_CARREGADO:
        return jsonify({'sucesso': False}), 503
    
    if session.get('empresa_tipo') != 'cliente':
        return jsonify({'sucesso': False}), 403
    
    fornecedor_id = request.args.get('fornecedor_id', type=int)
    resultado = limpar_carrinho(get_empresa_id(), fornecedor_id)
    
    return jsonify(resultado), 200 if resultado.get('sucesso') else 400


@app.route('/api/carrinho/checkout', methods=['POST'])
@login_required
def api_checkout():
    """Converte carrinho em pedido"""
    if not CARRINHO_MODULO_CARREGADO:
        return jsonify({'sucesso': False, 'erro': 'Módulo não disponível'}), 503
    
    if session.get('empresa_tipo') != 'cliente':
        return jsonify({'sucesso': False, 'erro': 'Apenas clientes'}), 403
    
    data = request.get_json(force=True, silent=True) or {}
    
    fornecedor_id = data.get('fornecedor_id')
    if not fornecedor_id:
        return jsonify({'sucesso': False, 'erro': 'Fornecedor é obrigatório'}), 400
    
    # Preparar dados do pedido
    dados_pedido = {
        'cliente_nome': session.get('empresa_nome', 'Cliente'),
        'cliente_email': data.get('email', ''),
        'telefone': data.get('telefone', ''),
        'endereco': data.get('endereco', ''),
        'forma_pagamento': data.get('forma_pagamento', 'pendente'),
        'mensagem': data.get('mensagem', ''),
        'data_entrega': data.get('data_entrega')
    }
    
    resultado = converter_carrinho_em_pedido(get_empresa_id(), fornecedor_id, dados_pedido)
    
    if resultado.get('sucesso'):
        try:
            criar_aviso(
                fornecedor_id,
                'pedido',
                '🛒 Novo Pedido Recebido',
                f"Novo pedido #{resultado.get('pedido_id')} - Total: R$ {resultado.get('total'):.2f}",
                'alta'
            )
        except Exception:
            pass
    
    status = 201 if resultado.get('sucesso') else 400
    return jsonify(resultado), status


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
    try:
        criar_aviso(
            get_empresa_id(),
            'reuniao',
            'Reunião agendada',
            f"{titulo} em {data.get('data_hora', '')}",
            'normal',
            data.get('data_hora')
        )
    except Exception:
        pass
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
            try:
                criar_aviso(
                    forn_id,
                    'pedido',
                    'Novo pedido recebido',
                    f"{cliente_empresa} comprou {qtd}x {prod['nome']} no valor de R$ {total:.2f}.",
                    'alta'
                )
            except Exception:
                pass
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
    if NOTIFICACOES_MODULO_CARREGADO:
        nao_lidas = request.args.get('nao_lidas') == '1'
        return jsonify(obter_notif_nova(get_empresa_id(), nao_lidas=nao_lidas))

    nao_lidas = request.args.get('nao_lidas') == '1'
    return jsonify(obter_notificacoes(get_empresa_id(), nao_lidas_somente=nao_lidas))

@app.route('/api/notificacoes', methods=['POST'])
@login_required
def api_criar_notificacao():
    data = request.get_json(force=True, silent=True) or {}

    if NOTIFICACOES_MODULO_CARREGADO:
        r = criar_notif_nova(
            get_empresa_id(),
            data.get('titulo', ''),
            data.get('mensagem', ''),
            tipo=data.get('tipo', 'info'),
            link=data.get('link'),
            dados_extras=data.get('dados_extras')
        )
        return jsonify(r), 201 if r.get('sucesso') else 400

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
    if NOTIFICACOES_MODULO_CARREGADO:
        return jsonify(marcar_notif_lida(nid, get_empresa_id()))

    return jsonify(marcar_notificacao_lida(get_empresa_id(), nid))

@app.route('/api/notificacoes/<int:nid>', methods=['DELETE'])
@login_required
def api_deletar_notificacao(nid):
    if NOTIFICACOES_MODULO_CARREGADO:
        return jsonify(deletar_notif_nova(nid, get_empresa_id()))

    return jsonify(deletar_notificacao(get_empresa_id(), nid))

@app.route('/api/notificacoes/count', methods=['GET'])
@login_required
def api_contar_notificacoes():
    if NOTIFICACOES_MODULO_CARREGADO:
        return jsonify({'count': contar_notif_nao_lidas(get_empresa_id())})

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





# ═══════════════════════════════════════════════════════════════
# ENDPOINTS PARA AGENDAMENTOS (NOVO)
# ═══════════════════════════════════════════════════════════════

@app.route('/api/agendamentos', methods=['POST'])
@login_required
def api_criar_agendamento():
    """Cria um novo agendamento"""
    if not AGENDAMENTO_MODULO_CARREGADO:
        return jsonify({'sucesso': False, 'mensagem': 'Módulo de agendamento não disponível'}), 503
    
    data = request.get_json(force=True, silent=True) or {}
    resultado = criar_agendamento(get_empresa_id(), data)
    
    if resultado.get('sucesso'):
        try:
            criar_aviso(
                get_empresa_id(),
                'agendamento',
                '📅 Agendamento Criado',
                f"Agendamento: {data.get('titulo')} em {data.get('data')}",
                'normal'
            )
        except Exception:
            pass
        
        return jsonify(resultado), 201
    return jsonify(resultado), 400


@app.route('/api/agendamentos', methods=['GET'])
@login_required
def api_listar_agendamentos():
    """Lista agendamentos da empresa"""
    if not AGENDAMENTO_MODULO_CARREGADO:
        return jsonify([]), 200
    
    filtro_data = request.args.get('data')  # hoje, semana, mes, atrasado
    filtro_status = request.args.get('status')
    
    agendamentos = obter_agendamentos(
        get_empresa_id(),
        filtro_data=filtro_data,
        filtro_status=filtro_status
    )
    
    return jsonify(agendamentos), 200


@app.route('/api/agendamentos/<int:agenda_id>', methods=['PUT'])
@login_required
def api_atualizar_agendamento(agenda_id):
    """Atualiza um agendamento"""
    if not AGENDAMENTO_MODULO_CARREGADO:
        return jsonify({'sucesso': False, 'mensagem': 'Módulo de agendamento não disponível'}), 503
    
    data = request.get_json(force=True, silent=True) or {}
    resultado = atualizar_agendamento(agenda_id, data)
    
    return jsonify(resultado), 200 if resultado.get('sucesso') else 400


@app.route('/api/agendamentos/<int:agenda_id>/concluir', methods=['PUT'])
@login_required
def api_concluir_agendamento(agenda_id):
    """Marca agendamento como concluído"""
    if not AGENDAMENTO_MODULO_CARREGADO:
        return jsonify({'sucesso': False, 'mensagem': 'Módulo de agendamento não disponível'}), 503
    
    data = request.get_json(force=True, silent=True) or {}
    observacoes = data.get('observacoes', '')
    
    resultado = concluir_agendamento(agenda_id, observacoes)
    
    if resultado.get('sucesso'):
        try:
            criar_aviso(
                get_empresa_id(),
                'agendamento',
                '✓ Agendamento Concluído',
                f"Agendamento #{agenda_id} foi concluído",
                'normal'
            )
        except Exception:
            pass
    
    return jsonify(resultado), 200 if resultado.get('sucesso') else 400


@app.route('/api/agendamentos/<int:agenda_id>/cancelar', methods=['PUT'])
@login_required
def api_cancelar_agendamento(agenda_id):
    """Cancela um agendamento"""
    if not AGENDAMENTO_MODULO_CARREGADO:
        return jsonify({'sucesso': False, 'mensagem': 'Módulo de agendamento não disponível'}), 503
    
    data = request.get_json(force=True, silent=True) or {}
    motivo = data.get('motivo', '')
    
    resultado = cancelar_agendamento(agenda_id, motivo)
    
    return jsonify(resultado), 200 if resultado.get('sucesso') else 400


@app.route('/api/agendamentos/<int:agenda_id>', methods=['DELETE'])
@login_required
def api_deletar_agendamento(agenda_id):
    """Deleta um agendamento"""
    if not AGENDAMENTO_MODULO_CARREGADO:
        return jsonify({'sucesso': False, 'mensagem': 'Módulo de agendamento não disponível'}), 503
    
    resultado = deletar_agendamento(agenda_id)
    
    return jsonify(resultado), 200 if resultado.get('sucesso') else 400


@app.route('/api/agendamentos/proximos', methods=['GET'])
@login_required
def api_proximos_agendamentos():
    """Retorna próximos agendamentos"""
    if not AGENDAMENTO_MODULO_CARREGADO:
        return jsonify([]), 200
    
    dias = request.args.get('dias', 7, type=int)
    agendamentos = obter_proximos_agendamentos(get_empresa_id(), dias)
    
    return jsonify(agendamentos), 200


@app.route('/api/agendamentos/atrasados', methods=['GET'])
@login_required
def api_agendamentos_atrasados():
    """Retorna agendamentos atrasados"""
    if not AGENDAMENTO_MODULO_CARREGADO:
        return jsonify([]), 200
    
    agendamentos = obter_agendamentos_atrasados(get_empresa_id())
    
    return jsonify(agendamentos), 200


# (notificações já definidas acima — rotas duplicadas removidas)


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS PARA EXPORTAÇÃO DE RELATÓRIOS (NOVO)
# ═══════════════════════════════════════════════════════════════

@app.route('/api/exportar/produtos', methods=['GET'])
@login_required
def api_exportar_produtos():
    """Exportação removida para manter o estoque apenas no sistema."""
    return jsonify({'sucesso': False, 'mensagem': 'Exportação removida. Use o inventário dentro do sistema.'}), 410



# ═══════════════════════════════════════════
# START
# ═══════════════════════════════════════════

init_db()

if __name__ == '__main__':
    app.run(debug=True, port=8080)
