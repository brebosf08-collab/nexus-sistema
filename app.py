import os
import uuid
from functools import wraps

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client, Client

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL e SUPABASE_SERVICE_KEY precisam estar definidos como variável de ambiente")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-troque-em-producao")


# ============================================================
# Helpers
# ============================================================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("empresa_id"):
            if request.path.startswith("/api/"):
                return jsonify({"sucesso": False, "mensagem": "Sessão expirada, faça login novamente"}), 401
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated


def empresa_id():
    return session["empresa_id"]


def log_erro(origem, e):
    print(f"[ERRO] {origem}: {e}")


def registrar_movimento(tipo_item, item_id, item_nome, tipo_movimento, quantidade, estoque_resultante, motivo=""):
    try:
        supabase.table("movimentos_estoque").insert({
            "empresa_id": empresa_id(),
            "tipo_item": tipo_item,
            "item_id": item_id,
            "item_nome": item_nome,
            "tipo_movimento": tipo_movimento,
            "quantidade": quantidade,
            "estoque_resultante": estoque_resultante,
            "motivo": motivo,
        }).execute()
    except Exception as e:
        log_erro("registrar_movimento", e)


def verificar_alerta_estoque(tipo_item, nome, unidade, novo_estoque, estoque_minimo):
    """Dispara aviso quando o estoque zera (sempre) ou fica no/abaixo do mínimo (se definido)."""
    rotulo = "produto" if tipo_item == "produto" else "matéria-prima"
    if novo_estoque <= 0:
        criar_aviso("estoque_zerado", f"🔴 Estoque zerado de {rotulo}",
                    f"'{nome}' chegou a zero. Produção/venda desse item vai parar até repor.", "alta")
    elif estoque_minimo > 0 and novo_estoque <= estoque_minimo:
        criar_aviso("estoque_baixo", f"⚠️ Estoque baixo de {rotulo}",
                    f"'{nome}' está com {novo_estoque} {unidade} (mínimo definido: {estoque_minimo})", "alta")


def criar_aviso(tipo, titulo, mensagem="", prioridade="normal"):
    try:
        supabase.table("avisos").insert({
            "empresa_id": empresa_id(),
            "tipo": tipo,
            "titulo": titulo,
            "mensagem": mensagem,
            "prioridade": prioridade,
        }).execute()
    except Exception as e:
        log_erro("criar_aviso", e)


def num(v, default=0):
    try:
        if v is None or v == "":
            return default
        return float(str(v).replace(",", "."))
    except (ValueError, TypeError):
        return default


# ============================================================
# Páginas
# ============================================================

@app.route("/")
def home():
    if session.get("empresa_id"):
        return redirect(url_for("painel"))
    return redirect(url_for("login_page"))


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/painel")
@login_required
def painel():
    return render_template("painel.html", empresa_nome=session.get("empresa_nome", ""))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))


# ============================================================
# Autenticação
# ============================================================

@app.route("/api/registrar", methods=["POST"])
def api_registrar():
    data = request.get_json(force=True, silent=True) or {}
    nome = (data.get("nome") or "").strip()
    email = (data.get("email") or "").strip().lower()
    senha = data.get("senha") or ""

    if not nome:
        return jsonify({"sucesso": False, "mensagem": "Nome da empresa é obrigatório"}), 400
    if not email or "@" not in email:
        return jsonify({"sucesso": False, "mensagem": "E-mail inválido"}), 400
    if len(senha) < 6:
        return jsonify({"sucesso": False, "mensagem": "Senha precisa ter pelo menos 6 caracteres"}), 400

    try:
        existente = supabase.table("empresas").select("id").eq("email", email).execute()
        if existente.data:
            return jsonify({"sucesso": False, "mensagem": "Já existe uma conta com esse e-mail"}), 400

        res = supabase.table("empresas").insert({
            "nome": nome,
            "email": email,
            "senha_hash": generate_password_hash(senha),
        }).execute()

        empresa = res.data[0]
        session["empresa_id"] = empresa["id"]
        session["empresa_nome"] = empresa["nome"]
        return jsonify({"sucesso": True}), 201
    except Exception as e:
        log_erro("api_registrar", e)
        return jsonify({"sucesso": False, "mensagem": f"Falha no cadastro: {e}"}), 400


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    senha = data.get("senha") or ""

    try:
        res = supabase.table("empresas").select("*").eq("email", email).execute()
        if not res.data:
            return jsonify({"sucesso": False, "mensagem": "E-mail ou senha incorretos"}), 401

        empresa = res.data[0]
        if not check_password_hash(empresa["senha_hash"], senha):
            return jsonify({"sucesso": False, "mensagem": "E-mail ou senha incorretos"}), 401

        session["empresa_id"] = empresa["id"]
        session["empresa_nome"] = empresa["nome"]
        return jsonify({"sucesso": True})
    except Exception as e:
        log_erro("api_login", e)
        return jsonify({"sucesso": False, "mensagem": f"Falha no login: {e}"}), 400


# ============================================================
# Matérias-primas
# ============================================================

@app.route("/api/materias-primas", methods=["GET"])
@login_required
def api_listar_materias():
    try:
        res = supabase.table("materias_primas").select("*").eq("empresa_id", empresa_id()).order("nome").execute()
        return jsonify(res.data)
    except Exception as e:
        log_erro("api_listar_materias", e)
        return jsonify([])


@app.route("/api/materias-primas", methods=["POST"])
@login_required
def api_criar_materia():
    data = request.get_json(force=True, silent=True) or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"sucesso": False, "mensagem": "Nome é obrigatório"}), 400

    try:
        res = supabase.table("materias_primas").insert({
            "empresa_id": empresa_id(),
            "nome": nome,
            "unidade": data.get("unidade") or "un",
            "estoque_atual": num(data.get("estoque_atual"), 0),
            "estoque_minimo": num(data.get("estoque_minimo"), 0),
            "custo_unitario": num(data.get("custo_unitario"), 0),
        }).execute()
        materia = res.data[0]

        if materia["estoque_atual"] > 0:
            registrar_movimento("materia_prima", materia["id"], materia["nome"], "entrada",
                                 materia["estoque_atual"], materia["estoque_atual"], "Estoque inicial")

        criar_aviso("materia_prima", "📦 Matéria-prima cadastrada", f"'{nome}' foi cadastrada")
        return jsonify({"sucesso": True, "materia_prima": materia}), 201
    except Exception as e:
        log_erro("api_criar_materia", e)
        return jsonify({"sucesso": False, "mensagem": f"Erro ao cadastrar: {e}"}), 400


@app.route("/api/materias-primas/<materia_id>/estoque", methods=["POST"])
@login_required
def api_ajustar_estoque_materia(materia_id):
    data = request.get_json(force=True, silent=True) or {}
    quantidade = num(data.get("quantidade"))
    tipo = data.get("tipo", "entrada")  # entrada | saida
    motivo = data.get("motivo", "Ajuste manual")

    if quantidade <= 0:
        return jsonify({"sucesso": False, "mensagem": "Quantidade precisa ser maior que zero"}), 400

    try:
        res = supabase.table("materias_primas").select("*").eq("id", materia_id).eq("empresa_id", empresa_id()).execute()
        if not res.data:
            return jsonify({"sucesso": False, "mensagem": "Matéria-prima não encontrada"}), 404
        materia = res.data[0]

        novo_estoque = materia["estoque_atual"] + quantidade if tipo == "entrada" else materia["estoque_atual"] - quantidade
        if novo_estoque < 0:
            return jsonify({"sucesso": False, "mensagem": "Estoque insuficiente para essa saída"}), 400

        supabase.table("materias_primas").update({"estoque_atual": novo_estoque}).eq("id", materia_id).execute()
        registrar_movimento("materia_prima", materia_id, materia["nome"], tipo, quantidade, novo_estoque, motivo)
        verificar_alerta_estoque("materia_prima", materia["nome"], materia["unidade"], novo_estoque, materia["estoque_minimo"])

        return jsonify({"sucesso": True, "estoque_atual": novo_estoque})
    except Exception as e:
        log_erro("api_ajustar_estoque_materia", e)
        return jsonify({"sucesso": False, "mensagem": f"Erro: {e}"}), 400


@app.route("/api/materias-primas/<materia_id>", methods=["DELETE"])
@login_required
def api_excluir_materia(materia_id):
    try:
        supabase.table("materias_primas").delete().eq("id", materia_id).eq("empresa_id", empresa_id()).execute()
        return jsonify({"sucesso": True})
    except Exception as e:
        log_erro("api_excluir_materia", e)
        return jsonify({"sucesso": False, "mensagem": f"Erro: {e}"}), 400


# ============================================================
# Produtos (+ composição de matérias-primas)
# ============================================================

@app.route("/api/produtos", methods=["GET"])
@login_required
def api_listar_produtos():
    try:
        res = supabase.table("produtos").select(
            "*, produto_materias_primas(id, materia_prima_id, quantidade_necessaria, "
            "materias_primas(nome, unidade, custo_unitario, estoque_atual))"
        ).eq("empresa_id", empresa_id()).order("nome").execute()
        return jsonify(res.data)
    except Exception as e:
        log_erro("api_listar_produtos", e)
        return jsonify([])


@app.route("/api/produtos", methods=["POST"])
@login_required
def api_criar_produto():
    data = request.get_json(force=True, silent=True) or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"sucesso": False, "mensagem": "Nome é obrigatório"}), 400

    composicao = data.get("composicao") or []  # [{materia_prima_id, quantidade_necessaria}, ...]

    try:
        res = supabase.table("produtos").insert({
            "empresa_id": empresa_id(),
            "nome": nome,
            "categoria_id": data.get("categoria_id") or None,
            "preco": num(data.get("preco"), 0),
            "unidade": data.get("unidade") or "un",
            "estoque_atual": num(data.get("estoque_atual"), 0),
            "estoque_minimo": num(data.get("estoque_minimo"), 0),
        }).execute()
        produto = res.data[0]

        for item in composicao:
            mid = item.get("materia_prima_id")
            qtd = num(item.get("quantidade_necessaria"))
            if mid and qtd > 0:
                supabase.table("produto_materias_primas").insert({
                    "produto_id": produto["id"],
                    "materia_prima_id": mid,
                    "quantidade_necessaria": qtd,
                }).execute()

        if produto["estoque_atual"] > 0:
            registrar_movimento("produto", produto["id"], produto["nome"], "entrada",
                                 produto["estoque_atual"], produto["estoque_atual"], "Estoque inicial")

        criar_aviso("produto", "✓ Produto cadastrado", f"'{nome}' foi cadastrado com sucesso")
        return jsonify({"sucesso": True, "produto": produto}), 201
    except Exception as e:
        log_erro("api_criar_produto", e)
        return jsonify({"sucesso": False, "mensagem": f"Erro ao cadastrar: {e}"}), 400


@app.route("/api/produtos/<produto_id>", methods=["DELETE"])
@login_required
def api_excluir_produto(produto_id):
    try:
        supabase.table("produtos").delete().eq("id", produto_id).eq("empresa_id", empresa_id()).execute()
        return jsonify({"sucesso": True})
    except Exception as e:
        log_erro("api_excluir_produto", e)
        return jsonify({"sucesso": False, "mensagem": f"Erro: {e}"}), 400


@app.route("/api/produtos/<produto_id>/saida", methods=["POST"])
@login_required
def api_saida_produto(produto_id):
    """Baixa manual de estoque de produto pronto (perda, quebra, ajuste) - não mexe em matéria-prima."""
    data = request.get_json(force=True, silent=True) or {}
    quantidade = num(data.get("quantidade"))
    motivo = data.get("motivo") or "Ajuste manual"

    if quantidade <= 0:
        return jsonify({"sucesso": False, "mensagem": "Quantidade precisa ser maior que zero"}), 400

    try:
        res = supabase.table("produtos").select("*").eq("id", produto_id).eq("empresa_id", empresa_id()).execute()
        if not res.data:
            return jsonify({"sucesso": False, "mensagem": "Produto não encontrado"}), 404
        produto = res.data[0]

        novo_estoque = produto["estoque_atual"] - quantidade
        if novo_estoque < 0:
            return jsonify({"sucesso": False, "mensagem": "Estoque insuficiente para essa saída"}), 400

        supabase.table("produtos").update({"estoque_atual": novo_estoque}).eq("id", produto_id).execute()
        registrar_movimento("produto", produto_id, produto["nome"], "ajuste", quantidade, novo_estoque, motivo)
        verificar_alerta_estoque("produto", produto["nome"], produto["unidade"], novo_estoque, produto["estoque_minimo"])

        return jsonify({"sucesso": True, "estoque_atual": novo_estoque})
    except Exception as e:
        log_erro("api_saida_produto", e)
        return jsonify({"sucesso": False, "mensagem": f"Erro: {e}"}), 400


@app.route("/api/produtos/<produto_id>/produzir", methods=["POST"])
@login_required
def api_produzir(produto_id):
    """Consome as matérias-primas da composição e gera estoque do produto pronto."""
    data = request.get_json(force=True, silent=True) or {}
    quantidade_produzir = num(data.get("quantidade"))
    if quantidade_produzir <= 0:
        return jsonify({"sucesso": False, "mensagem": "Quantidade precisa ser maior que zero"}), 400

    try:
        prod_res = supabase.table("produtos").select("*").eq("id", produto_id).eq("empresa_id", empresa_id()).execute()
        if not prod_res.data:
            return jsonify({"sucesso": False, "mensagem": "Produto não encontrado"}), 404
        produto = prod_res.data[0]

        comp_res = supabase.table("produto_materias_primas").select("*, materias_primas(*)").eq("produto_id", produto_id).execute()
        composicao = comp_res.data

        if not composicao:
            return jsonify({"sucesso": False, "mensagem": "Esse produto não tem matérias-primas cadastradas na composição"}), 400

        # Verifica se há matéria-prima suficiente para TODOS os itens antes de mexer em qualquer estoque
        faltas = []
        for item in composicao:
            materia = item["materias_primas"]
            necessario = item["quantidade_necessaria"] * quantidade_produzir
            if materia["estoque_atual"] < necessario:
                faltas.append(f"{materia['nome']} (precisa {necessario}, tem {materia['estoque_atual']} {materia['unidade']})")

        if faltas:
            return jsonify({"sucesso": False, "mensagem": "Matéria-prima insuficiente: " + "; ".join(faltas)}), 400

        # Consome cada matéria-prima
        for item in composicao:
            materia = item["materias_primas"]
            necessario = item["quantidade_necessaria"] * quantidade_produzir
            novo_estoque_materia = materia["estoque_atual"] - necessario
            supabase.table("materias_primas").update({"estoque_atual": novo_estoque_materia}).eq("id", materia["id"]).execute()
            registrar_movimento("materia_prima", materia["id"], materia["nome"], "producao_consumo",
                                 necessario, novo_estoque_materia, f"Usado para produzir {quantidade_produzir} de {produto['nome']}")
            verificar_alerta_estoque("materia_prima", materia["nome"], materia["unidade"], novo_estoque_materia, materia["estoque_minimo"])

        # Gera o estoque do produto pronto
        novo_estoque_produto = produto["estoque_atual"] + quantidade_produzir
        supabase.table("produtos").update({"estoque_atual": novo_estoque_produto}).eq("id", produto_id).execute()
        registrar_movimento("produto", produto_id, produto["nome"], "producao_gerado",
                             quantidade_produzir, novo_estoque_produto, "Produção")

        criar_aviso("producao", "🏭 Produção concluída", f"{quantidade_produzir} {produto['unidade']} de '{produto['nome']}' produzido(s)")

        return jsonify({"sucesso": True, "estoque_atual": novo_estoque_produto})
    except Exception as e:
        log_erro("api_produzir", e)
        return jsonify({"sucesso": False, "mensagem": f"Erro: {e}"}), 400


# ============================================================
# Estoque / Inventário
# ============================================================

@app.route("/api/estoque", methods=["GET"])
@login_required
def api_estoque():
    try:
        produtos = supabase.table("produtos").select("id, nome, unidade, estoque_atual, estoque_minimo, preco").eq("empresa_id", empresa_id()).order("nome").execute().data
        materias = supabase.table("materias_primas").select("id, nome, unidade, estoque_atual, estoque_minimo, custo_unitario").eq("empresa_id", empresa_id()).order("nome").execute().data
        return jsonify({"produtos": produtos, "materias_primas": materias})
    except Exception as e:
        log_erro("api_estoque", e)
        return jsonify({"produtos": [], "materias_primas": []})


@app.route("/api/historico", methods=["GET"])
@login_required
def api_historico():
    try:
        res = supabase.table("movimentos_estoque").select("*").eq("empresa_id", empresa_id()).order("criado_em", desc=True).limit(200).execute()
        return jsonify(res.data)
    except Exception as e:
        log_erro("api_historico", e)
        return jsonify([])


# ============================================================
# Pedidos
# ============================================================

@app.route("/api/pedidos", methods=["GET"])
@login_required
def api_listar_pedidos():
    try:
        res = supabase.table("pedidos").select("*, pedido_itens(*)").eq("empresa_id", empresa_id()).order("criado_em", desc=True).execute()
        return jsonify(res.data)
    except Exception as e:
        log_erro("api_listar_pedidos", e)
        return jsonify([])


@app.route("/api/pedidos", methods=["POST"])
@login_required
def api_criar_pedido():
    data = request.get_json(force=True, silent=True) or {}
    itens = data.get("itens") or []
    cliente_nome = (data.get("cliente_nome") or "Cliente balcão").strip()

    if not itens:
        return jsonify({"sucesso": False, "mensagem": "Adicione ao menos um item ao pedido"}), 400

    try:
        # Confere estoque de produto pronto suficiente para TODOS os itens antes de criar o pedido
        produtos_cache = {}
        faltas = []
        for item in itens:
            pid = item.get("produto_id")
            qtd = num(item.get("quantidade"))
            res = supabase.table("produtos").select("*").eq("id", pid).eq("empresa_id", empresa_id()).execute()
            if not res.data:
                return jsonify({"sucesso": False, "mensagem": "Produto não encontrado"}), 400
            produto = res.data[0]
            produtos_cache[pid] = produto
            if produto["estoque_atual"] < qtd:
                faltas.append(f"{produto['nome']} (pedido: {qtd}, disponível: {produto['estoque_atual']})")

        if faltas:
            return jsonify({"sucesso": False, "mensagem": "Estoque insuficiente: " + "; ".join(faltas)}), 400

        total = 0
        itens_para_salvar = []
        for item in itens:
            pid = item.get("produto_id")
            qtd = num(item.get("quantidade"))
            produto = produtos_cache[pid]
            preco_unit = produto["preco"]
            subtotal = preco_unit * qtd
            total += subtotal
            itens_para_salvar.append({
                "produto_id": pid, "produto_nome": produto["nome"],
                "quantidade": qtd, "preco_unitario": preco_unit, "subtotal": subtotal,
            })

        pedido_res = supabase.table("pedidos").insert({
            "empresa_id": empresa_id(), "cliente_nome": cliente_nome, "total": total,
        }).execute()
        pedido = pedido_res.data[0]

        for item in itens_para_salvar:
            item["pedido_id"] = pedido["id"]
            supabase.table("pedido_itens").insert(item).execute()

            produto = produtos_cache[item["produto_id"]]
            novo_estoque = produto["estoque_atual"] - item["quantidade"]
            supabase.table("produtos").update({"estoque_atual": novo_estoque}).eq("id", item["produto_id"]).execute()
            registrar_movimento("produto", item["produto_id"], produto["nome"], "pedido",
                                 item["quantidade"], novo_estoque, f"Pedido #{pedido['id'][:8]}")
            verificar_alerta_estoque("produto", produto["nome"], produto["unidade"], novo_estoque, produto["estoque_minimo"])

        criar_aviso("pedido", "🛒 Novo pedido registrado", f"Pedido de {cliente_nome} - Total: R$ {total:.2f}", "alta")

        return jsonify({"sucesso": True, "pedido_id": pedido["id"], "total": total}), 201
    except Exception as e:
        log_erro("api_criar_pedido", e)
        return jsonify({"sucesso": False, "mensagem": f"Erro ao registrar pedido: {e}"}), 400


# ============================================================
# Dashboard
# ============================================================

@app.route("/api/dashboard", methods=["GET"])
@login_required
def api_dashboard():
    try:
        produtos = supabase.table("produtos").select("estoque_atual, estoque_minimo, preco").eq("empresa_id", empresa_id()).execute().data
        materias = supabase.table("materias_primas").select("estoque_atual, estoque_minimo, custo_unitario").eq("empresa_id", empresa_id()).execute().data
        pedidos = supabase.table("pedidos").select("total, criado_em").eq("empresa_id", empresa_id()).execute().data

        produtos_zerados = sum(1 for p in produtos if p["estoque_atual"] <= 0)
        produtos_baixos = sum(1 for p in produtos if 0 < p["estoque_atual"] <= p["estoque_minimo"])
        materias_zeradas = sum(1 for m in materias if m["estoque_atual"] <= 0)
        materias_baixas = sum(1 for m in materias if 0 < m["estoque_atual"] <= m["estoque_minimo"])

        return jsonify({
            "total_produtos": len(produtos),
            "total_materias_primas": len(materias),
            "valor_estoque_produtos": sum(p["estoque_atual"] * p["preco"] for p in produtos),
            "valor_estoque_materias": sum(m["estoque_atual"] * m["custo_unitario"] for m in materias),
            "produtos_zerados": produtos_zerados,
            "produtos_baixos": produtos_baixos,
            "materias_zeradas": materias_zeradas,
            "materias_baixas": materias_baixas,
            "total_pedidos": len(pedidos),
            "valor_total_pedidos": sum(p["total"] for p in pedidos),
        })
    except Exception as e:
        log_erro("api_dashboard", e)
        return jsonify({
            "total_produtos": 0, "total_materias_primas": 0,
            "valor_estoque_produtos": 0, "valor_estoque_materias": 0,
            "produtos_zerados": 0, "produtos_baixos": 0,
            "materias_zeradas": 0, "materias_baixas": 0,
            "total_pedidos": 0, "valor_total_pedidos": 0,
        })


# ============================================================
# Avisos / Notificações
# ============================================================

@app.route("/api/avisos", methods=["GET"])
@login_required
def api_listar_avisos():
    try:
        res = supabase.table("avisos").select("*").eq("empresa_id", empresa_id()).order("criado_em", desc=True).limit(50).execute()
        return jsonify(res.data)
    except Exception as e:
        log_erro("api_listar_avisos", e)
        return jsonify([])


@app.route("/api/avisos/<aviso_id>/lido", methods=["POST"])
@login_required
def api_marcar_lido(aviso_id):
    try:
        supabase.table("avisos").update({"lido": True}).eq("id", aviso_id).eq("empresa_id", empresa_id()).execute()
        return jsonify({"sucesso": True})
    except Exception as e:
        log_erro("api_marcar_lido", e)
        return jsonify({"sucesso": False}), 400


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
