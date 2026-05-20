import sqlite3
import json
from datetime import datetime
from contextlib import contextmanager
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE = 'sistema.db'
MATERIA_PRIMA_MARKER = '[DADOS_MATERIA_PRIMA] '


def _normalizar_materia_prima(produto):
    if not produto:
        return produto
    produto = dict(produto)
    descricao = produto.get('descricao') or ''
    if MATERIA_PRIMA_MARKER not in descricao:
        return produto
    descricao_visivel, payload = descricao.split(MATERIA_PRIMA_MARKER, 1)
    try:
        materia = json.loads(payload.strip())
    except Exception:
        materia = {}
    produto['descricao'] = descricao_visivel.strip()
    produto['materia_prima'] = materia
    produto['materia_prima_nome'] = materia.get('nome', '')
    produto['materia_prima_quantidade'] = materia.get('quantidade', 0)
    produto['materia_prima_unidade'] = materia.get('unidade', 'un')
    produto['materia_prima_minimo'] = materia.get('minimo', 0)
    return produto


@contextmanager
def get_db():
    """Gerenciador de conexão com o banco de dados"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_db():
    """Inicializa o banco de dados com todas as tabelas multi-tenant"""
    with get_db() as conn:
        c = conn.cursor()

        # ─── Empresas (Fornecedor ou Cliente) ───
        c.execute('''
            CREATE TABLE IF NOT EXISTS empresas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                documento TEXT,
                tipo_documento TEXT DEFAULT 'cnpj',
                tipo TEXT NOT NULL CHECK(tipo IN ('fornecedor', 'cliente')),
                endereco TEXT,
                telefone TEXT,
                email TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # ─── Usuários vinculados a uma empresa ───
        c.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                login TEXT NOT NULL,
                senha_hash TEXT NOT NULL,
                cargo TEXT DEFAULT 'operador',
                ativo INTEGER DEFAULT 1,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                UNIQUE(login, empresa_id)
            )
        ''')

        # ─── Categorias por empresa ───
        c.execute('''
            CREATE TABLE IF NOT EXISTS categorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                criada_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                UNIQUE(empresa_id, nome)
            )
        ''')

        # ─── Produtos por empresa ───
        c.execute('''
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                sku TEXT,
                categoria_id INTEGER,
                custo REAL NOT NULL DEFAULT 0,
                preco REAL NOT NULL DEFAULT 0,
                quantidade INTEGER NOT NULL DEFAULT 0,
                minimo INTEGER NOT NULL DEFAULT 0,
                descricao TEXT,
                imagem TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                FOREIGN KEY (categoria_id) REFERENCES categorias(id)
            )
        ''')

        # ─── Vendedores por empresa ───
        c.execute('''
            CREATE TABLE IF NOT EXISTS vendedores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                email TEXT,
                telefone TEXT,
                comissao REAL DEFAULT 0,
                ativo INTEGER DEFAULT 1,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id)
            )
        ''')

        # ─── Pedidos por empresa ───
        c.execute('''
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                cliente_nome TEXT NOT NULL,
                vendedor_id INTEGER,
                data DATE NOT NULL,
                total REAL NOT NULL DEFAULT 0,
                quantidade_itens INTEGER NOT NULL DEFAULT 0,
                status TEXT DEFAULT 'pendente',
                observacoes TEXT,
                cliente_id INTEGER,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                FOREIGN KEY (vendedor_id) REFERENCES vendedores(id)
            )
        ''')

        # ─── Itens do Pedido ───
        c.execute('''
            CREATE TABLE IF NOT EXISTS itens_pedido (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER NOT NULL,
                produto_id INTEGER NOT NULL,
                quantidade INTEGER NOT NULL,
                preco_unitario REAL NOT NULL,
                subtotal REAL NOT NULL,
                FOREIGN KEY (pedido_id) REFERENCES pedidos(id),
                FOREIGN KEY (produto_id) REFERENCES produtos(id)
            )
        ''')

        # ─── Histórico de movimentações ───
        c.execute('''
            CREATE TABLE IF NOT EXISTS historico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                produto_id INTEGER NOT NULL,
                tipo TEXT NOT NULL,
                quantidade INTEGER NOT NULL,
                observacoes TEXT,
                data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                FOREIGN KEY (produto_id) REFERENCES produtos(id)
            )
        ''')

        # ─── Reuniões por empresa ───
        c.execute('''
            CREATE TABLE IF NOT EXISTS reunioes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                titulo TEXT NOT NULL,
                descricao TEXT,
                data_hora TEXT NOT NULL,
                local TEXT,
                participantes TEXT,
                status TEXT DEFAULT 'agendada',
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id)
            )
        ''')

        # ─── Contatos / Clientes por empresa fornecedora ───
        c.execute('''
            CREATE TABLE IF NOT EXISTS contatos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                documento TEXT,
                email TEXT,
                telefone TEXT,
                endereco TEXT,
                tipo TEXT DEFAULT 'cliente',
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id)
            )
        ''')

        conn.commit()


# ═══════════════════════════════════════════
# EMPRESAS & AUTH
# ═══════════════════════════════════════════

def registrar_empresa(nome, documento, tipo_documento, tipo, endereco='', telefone='', email=''):
    """Registra uma nova empresa (fornecedor ou cliente)"""
    with get_db() as conn:
        c = conn.cursor()
        doc = (documento or '').strip() or None
        if doc:
            c.execute('SELECT id FROM empresas WHERE documento = ?', (doc,))
            if c.fetchone():
                return {'sucesso': False, 'mensagem': 'Documento já cadastrado no sistema.'}
        c.execute('''
            INSERT INTO empresas (nome, documento, tipo_documento, tipo, endereco, telefone, email)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (nome, doc, tipo_documento, tipo, endereco, telefone, email))
        return {'sucesso': True, 'id': c.lastrowid}


def registrar_usuario(empresa_id, nome, login, senha, cargo='admin'):
    """Cria um usuário vinculado a uma empresa"""
    with get_db() as conn:
        c = conn.cursor()
        try:
            senha_hash = generate_password_hash(senha)
            c.execute('''
                INSERT INTO usuarios (empresa_id, nome, login, senha_hash, cargo)
                VALUES (?, ?, ?, ?, ?)
            ''', (empresa_id, nome, login, senha_hash, cargo))
            return {'sucesso': True, 'id': c.lastrowid}
        except sqlite3.IntegrityError:
            return {'sucesso': False, 'mensagem': 'Login já em uso nesta empresa.'}


def autenticar_usuario(login, senha):
    """Autentica um usuário"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT u.*, e.nome as empresa_nome, e.tipo as empresa_tipo, e.documento as empresa_documento
            FROM usuarios u
            JOIN empresas e ON u.empresa_id = e.id
            WHERE u.login = ? AND u.ativo = 1
        ''', (login,))
        user = c.fetchone()
        if user and check_password_hash(user['senha_hash'], senha):
            return dict(user)
        return None


def obter_empresa(empresa_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM empresas WHERE id = ?', (empresa_id,))
        r = c.fetchone()
        return dict(r) if r else None


# ═══════════════════════════════════════════
# CATEGORIAS
# ═══════════════════════════════════════════

def criar_categoria(empresa_id, nome):
    nome = (nome or '').strip()
    if not nome:
        return {'sucesso': False, 'mensagem': 'Nome da categoria é obrigatório'}
    with get_db() as conn:
        c = conn.cursor()
        try:
            c.execute('INSERT INTO categorias (empresa_id, nome) VALUES (?, ?)', (empresa_id, nome))
            return {'sucesso': True, 'id': c.lastrowid, 'nome': nome}
        except sqlite3.IntegrityError:
            return {'sucesso': False, 'mensagem': 'Categoria já existe'}


def obter_categorias(empresa_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM categorias WHERE empresa_id = ? ORDER BY nome ASC', (empresa_id,))
        return [dict(r) for r in c.fetchall()]


def deletar_categoria(empresa_id, categoria_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM categorias WHERE id = ? AND empresa_id = ?', (categoria_id, empresa_id))
        return {'sucesso': True}


# ═══════════════════════════════════════════
# PRODUTOS
# ═══════════════════════════════════════════

def criar_produto(empresa_id, nome, sku, categoria_id, custo, preco, quantidade, minimo, descricao='', imagem=None):
    with get_db() as conn:
        c = conn.cursor()
        try:
            sku_norm = (sku or '').strip() or None
            c.execute('''
                INSERT INTO produtos (empresa_id, nome, sku, categoria_id, custo, preco, quantidade, minimo, descricao, imagem)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (empresa_id, nome, sku_norm, categoria_id or None, float(custo), float(preco), int(quantidade), int(minimo), descricao, imagem))
            pid = c.lastrowid
            # histórico
            c.execute('''
                INSERT INTO historico (empresa_id, produto_id, tipo, quantidade, observacoes)
                VALUES (?, ?, 'entrada', ?, 'Cadastro inicial')
            ''', (empresa_id, pid, int(quantidade)))
            return {'sucesso': True, 'id': pid}
        except sqlite3.IntegrityError as e:
            return {'sucesso': False, 'mensagem': str(e)}


def obter_produtos(empresa_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT p.*, COALESCE(cat.nome, '') as categoria_nome
            FROM produtos p
            LEFT JOIN categorias cat ON p.categoria_id = cat.id
            WHERE p.empresa_id = ?
            ORDER BY p.id DESC
        ''', (empresa_id,))
        return [_normalizar_materia_prima(r) for r in c.fetchall()]


def obter_produto(empresa_id, produto_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM produtos WHERE id = ? AND empresa_id = ?', (produto_id, empresa_id))
        r = c.fetchone()
        return _normalizar_materia_prima(r) if r else None


def atualizar_produto(empresa_id, produto_id, dados):
    with get_db() as conn:
        c = conn.cursor()
        permitidos = ['nome', 'sku', 'categoria_id', 'custo', 'preco', 'minimo', 'descricao', 'imagem']
        atualizacoes = {k: v for k, v in dados.items() if k in permitidos}
        if not atualizacoes:
            return {'sucesso': False, 'mensagem': 'Nada para atualizar'}
        campos = ', '.join([f'{k} = ?' for k in atualizacoes.keys()])
        valores = list(atualizacoes.values()) + [produto_id, empresa_id]
        c.execute(f'UPDATE produtos SET {campos} WHERE id = ? AND empresa_id = ?', valores)
        return {'sucesso': True}


def deletar_produto(empresa_id, produto_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM historico WHERE produto_id = ? AND empresa_id = ?', (produto_id, empresa_id))
        c.execute('DELETE FROM itens_pedido WHERE produto_id = ?', (produto_id,))
        c.execute('DELETE FROM produtos WHERE id = ? AND empresa_id = ?', (produto_id, empresa_id))
        return {'sucesso': True}


def adicionar_estoque(empresa_id, produto_id, quantidade, observacoes=''):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('SELECT quantidade FROM produtos WHERE id = ? AND empresa_id = ?', (produto_id, empresa_id))
        r = c.fetchone()
        if not r:
            return {'sucesso': False, 'mensagem': 'Produto não encontrado'}
        nova_qtd = r['quantidade'] + int(quantidade)
        c.execute('UPDATE produtos SET quantidade = ? WHERE id = ? AND empresa_id = ?',
                  (nova_qtd, produto_id, empresa_id))
        c.execute('''
            INSERT INTO historico (empresa_id, produto_id, tipo, quantidade, observacoes)
            VALUES (?, ?, 'entrada', ?, ?)
        ''', (empresa_id, produto_id, int(quantidade), observacoes or 'Entrada de estoque'))
        return {'sucesso': True, 'nova_quantidade': nova_qtd}


def retirar_estoque(empresa_id, produto_id, quantidade, observacoes=''):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('SELECT quantidade FROM produtos WHERE id = ? AND empresa_id = ?', (produto_id, empresa_id))
        r = c.fetchone()
        if not r:
            return {'sucesso': False, 'mensagem': 'Produto não encontrado'}
        if r['quantidade'] < int(quantidade):
            return {'sucesso': False, 'mensagem': 'Estoque insuficiente'}
        nova_qtd = r['quantidade'] - int(quantidade)
        c.execute('UPDATE produtos SET quantidade = ? WHERE id = ? AND empresa_id = ?',
                  (nova_qtd, produto_id, empresa_id))
        c.execute('''
            INSERT INTO historico (empresa_id, produto_id, tipo, quantidade, observacoes)
            VALUES (?, ?, 'saida', ?, ?)
        ''', (empresa_id, produto_id, int(quantidade), observacoes or 'Saída de estoque'))
        return {'sucesso': True, 'nova_quantidade': nova_qtd}


# ═══════════════════════════════════════════
# VENDEDORES
# ═══════════════════════════════════════════

def criar_vendedor(empresa_id, nome, email='', telefone='', comissao=0):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO vendedores (empresa_id, nome, email, telefone, comissao)
            VALUES (?, ?, ?, ?, ?)
        ''', (empresa_id, nome, email, telefone, float(comissao)))
        return {'sucesso': True, 'id': c.lastrowid}


def obter_vendedores(empresa_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM vendedores WHERE empresa_id = ? ORDER BY nome', (empresa_id,))
        return [dict(r) for r in c.fetchall()]


def deletar_vendedor(empresa_id, vendedor_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM vendedores WHERE id = ? AND empresa_id = ?', (vendedor_id, empresa_id))
        return {'sucesso': True}


# ═══════════════════════════════════════════
# PEDIDOS
# ═══════════════════════════════════════════

def criar_pedido(empresa_id, cliente_nome, data, itens, vendedor_id=None, observacoes='', cliente_id=None):
    with get_db() as conn:
        c = conn.cursor()
        total = 0
        qtd_itens = 0
        for item in itens:
            total += float(item['subtotal'])
            qtd_itens += int(item['quantidade'])

        c.execute('''
            INSERT INTO pedidos (empresa_id, cliente_nome, vendedor_id, data, total, quantidade_itens, observacoes, cliente_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (empresa_id, cliente_nome, vendedor_id or None, data, total, qtd_itens, observacoes, cliente_id))
        pedido_id = c.lastrowid

        for item in itens:
            c.execute('''
                INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario, subtotal)
                VALUES (?, ?, ?, ?, ?)
            ''', (pedido_id, item['produto_id'], int(item['quantidade']),
                  float(item['preco']), float(item['subtotal'])))
            # Atualizar estoque
            c.execute('SELECT quantidade FROM produtos WHERE id = ? AND empresa_id = ?',
                      (item['produto_id'], empresa_id))
            r = c.fetchone()
            if r:
                nova_qtd = max(0, r['quantidade'] - int(item['quantidade']))
                c.execute('UPDATE produtos SET quantidade = ? WHERE id = ?', (nova_qtd, item['produto_id']))
                c.execute('''
                    INSERT INTO historico (empresa_id, produto_id, tipo, quantidade, observacoes)
                    VALUES (?, ?, 'saida', ?, ?)
                ''', (empresa_id, item['produto_id'], int(item['quantidade']),
                      f'Pedido #{pedido_id} - {cliente_nome}'))

        return {'sucesso': True, 'id': pedido_id}


def obter_pedidos(empresa_id=None, cliente_id=None):
    with get_db() as conn:
        c = conn.cursor()
        if cliente_id:
            c.execute('''
                SELECT p.*, v.nome as vendedor_nome, f.nome as fornecedor_nome
                FROM pedidos p
                LEFT JOIN vendedores v ON p.vendedor_id = v.id
                LEFT JOIN empresas f ON p.empresa_id = f.id
                WHERE p.cliente_id = ?
                ORDER BY p.id DESC
            ''', (cliente_id,))
        else:
            c.execute('''
                SELECT p.*, v.nome as vendedor_nome
                FROM pedidos p
                LEFT JOIN vendedores v ON p.vendedor_id = v.id
                WHERE p.empresa_id = ?
                ORDER BY p.id DESC
            ''', (empresa_id,))
        return [dict(r) for r in c.fetchall()]


def obter_pedido_detalhado(empresa_id, pedido_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM pedidos WHERE id = ? AND empresa_id = ?', (pedido_id, empresa_id))
        pedido = c.fetchone()
        if not pedido:
            return None
        c.execute('''
            SELECT ip.*, pr.nome as produto_nome
            FROM itens_pedido ip
            JOIN produtos pr ON ip.produto_id = pr.id
            WHERE ip.pedido_id = ?
        ''', (pedido_id,))
        itens = [dict(r) for r in c.fetchall()]
        return {'pedido': dict(pedido), 'itens': itens}


def atualizar_status_pedido(pedido_id, status, empresa_id=None, cliente_id=None):
    with get_db() as conn:
        c = conn.cursor()
        if cliente_id:
            c.execute('UPDATE pedidos SET status = ? WHERE id = ? AND cliente_id = ?',
                      (status, pedido_id, cliente_id))
        else:
            c.execute('UPDATE pedidos SET status = ? WHERE id = ? AND empresa_id = ?',
                      (status, pedido_id, empresa_id))
        if c.rowcount == 0:
            return {'sucesso': False, 'mensagem': 'Pedido não encontrado'}
        return {'sucesso': True}


# ═══════════════════════════════════════════
# HISTÓRICO
# ═══════════════════════════════════════════

def obter_historico(empresa_id, filtro_tipo=None, data_inicio=None, data_fim=None):
    with get_db() as conn:
        c = conn.cursor()
        query = '''
            SELECT h.*, p.nome as produto_nome
            FROM historico h
            JOIN produtos p ON h.produto_id = p.id
            WHERE h.empresa_id = ?
        '''
        params = [empresa_id]
        if filtro_tipo:
            query += ' AND h.tipo = ?'
            params.append(filtro_tipo)
        if data_inicio:
            query += ' AND DATE(h.data_hora) >= ?'
            params.append(data_inicio)
        if data_fim:
            query += ' AND DATE(h.data_hora) <= ?'
            params.append(data_fim)
        query += ' ORDER BY h.data_hora DESC'
        c.execute(query, params)
        return [dict(r) for r in c.fetchall()]


# ═══════════════════════════════════════════
# REUNIÕES
# ═══════════════════════════════════════════

def criar_reuniao(empresa_id, titulo, descricao, data_hora, local_r='', participantes=''):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO reunioes (empresa_id, titulo, descricao, data_hora, local, participantes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (empresa_id, titulo, descricao, data_hora, local_r, participantes))
        return {'sucesso': True, 'id': c.lastrowid}


def obter_reunioes(empresa_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM reunioes WHERE empresa_id = ? ORDER BY data_hora DESC', (empresa_id,))
        return [dict(r) for r in c.fetchall()]


def atualizar_status_reuniao(empresa_id, reuniao_id, status):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('UPDATE reunioes SET status = ? WHERE id = ? AND empresa_id = ?',
                  (status, reuniao_id, empresa_id))
        return {'sucesso': True}


def deletar_reuniao(empresa_id, reuniao_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM reunioes WHERE id = ? AND empresa_id = ?', (reuniao_id, empresa_id))
        return {'sucesso': True}


# ═══════════════════════════════════════════
# CONTATOS
# ═══════════════════════════════════════════

def criar_contato(empresa_id, nome, documento='', email='', telefone='', endereco='', tipo='cliente'):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO contatos (empresa_id, nome, documento, email, telefone, endereco, tipo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (empresa_id, nome, documento, email, telefone, endereco, tipo))
        return {'sucesso': True, 'id': c.lastrowid}


def obter_contatos(empresa_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM contatos WHERE empresa_id = ? ORDER BY nome', (empresa_id,))
        return [dict(r) for r in c.fetchall()]


def deletar_contato(empresa_id, contato_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM contatos WHERE id = ? AND empresa_id = ?', (contato_id, empresa_id))
        return {'sucesso': True}


# ═══════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════

def obter_dashboard(empresa_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('SELECT COUNT(*) as total FROM produtos WHERE empresa_id = ?', (empresa_id,))
        total_produtos = c.fetchone()['total']

        c.execute('SELECT COALESCE(SUM(quantidade * preco), 0) as total FROM produtos WHERE empresa_id = ?', (empresa_id,))
        valor_total = c.fetchone()['total']

        c.execute('SELECT COUNT(*) as total FROM produtos WHERE empresa_id = ? AND quantidade <= minimo AND quantidade > 0', (empresa_id,))
        produtos_baixos = c.fetchone()['total']

        c.execute('SELECT COUNT(*) as total FROM produtos WHERE empresa_id = ? AND quantidade = 0', (empresa_id,))
        sem_estoque = c.fetchone()['total']

        c.execute('SELECT COUNT(*) as total FROM pedidos WHERE empresa_id = ?', (empresa_id,))
        total_pedidos = c.fetchone()['total']

        c.execute('SELECT COALESCE(SUM(total), 0) as total FROM pedidos WHERE empresa_id = ?', (empresa_id,))
        valor_pedidos = c.fetchone()['total']

        c.execute('SELECT COUNT(*) as total FROM vendedores WHERE empresa_id = ? AND ativo = 1', (empresa_id,))
        total_vendedores = c.fetchone()['total']

        c.execute('SELECT COUNT(*) as total FROM reunioes WHERE empresa_id = ? AND status = "agendada"', (empresa_id,))
        reunioes_pendentes = c.fetchone()['total']

        return {
            'total_produtos': total_produtos,
            'valor_total': valor_total,
            'produtos_baixos': produtos_baixos,
            'sem_estoque': sem_estoque,
            'total_pedidos': total_pedidos,
            'valor_pedidos': valor_pedidos,
            'total_vendedores': total_vendedores,
            'reunioes_pendentes': reunioes_pendentes,
        }
