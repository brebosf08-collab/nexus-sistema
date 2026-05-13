import os
from supabase import create_client, Client
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configure essas variáveis no seu ambiente ou .env
# Se não houver no ambiente, usa os valores padrão (fallback)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://gtctfqphvsczeenpysco.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
if not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_KEY must be defined as an environment variable")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def init_db():
    """No Supabase as tabelas são gerenciadas no dashboard/SQL Editor."""
    pass

# ═══════════════════════════════════════════
# EMPRESAS & AUTH
# ═══════════════════════════════════════════

def registrar_empresa(nome, documento, tipo_documento, tipo, endereco='', telefone='', email='', senha=''):
    try:
        # 0. Verificar se o e-mail já existe na tabela de usuários
        check_user = supabase.table('usuarios').select('id').eq('login', email).execute()
        if check_user.data:
            return {'sucesso': False, 'mensagem': 'Este e-mail já está vinculado a uma conta ativa.'}

        doc = (documento or '').strip() or None
        # Se houver documento, verifica se já existe na tabela de empresas
        if doc:
            r = supabase.table('empresas').select('id').eq('documento', doc).execute()
            if r.data:
                return {'sucesso': False, 'mensagem': 'Documento (CPF/CNPJ) já cadastrado.'}
        
        # 1. Registrar no Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": senha
        })
        
        if not auth_response.user:
            return {'sucesso': False, 'mensagem': 'Erro ao criar conta de acesso. Verifique se o e-mail é válido.'}

        # 2. Criar a empresa
        emp_data = {
            "nome": nome,
            "documento": doc,
            "tipo_documento": tipo_documento,
            "tipo": tipo,
            "endereco": endereco,
            "telefone": telefone,
            "email": email
        }
        res_empresa = supabase.table('empresas').insert(emp_data).execute()
        if not res_empresa.data:
            return {'sucesso': False, 'mensagem': 'Erro ao registrar dados da empresa.'}
            
        empresa_id = res_empresa.data[0]['id']
        auth_id = auth_response.user.id
            
        # 3. Criar usuário vinculado
        user_data = {
            "auth_id": auth_id,
            "empresa_id": empresa_id,
            "nome": email.split('@')[0],
            "login": email,
            "cargo": "admin"
        }
        res_user = supabase.table('usuarios').insert(user_data).execute()
        
        if not res_user.data:
             return {'sucesso': False, 'mensagem': 'Erro ao vincular usuário à empresa.'}

        return {'sucesso': True, 'id': empresa_id, 'user_id': res_user.data[0]['id']}
    except Exception as e:
        print(f"Erro no registro: {e}")
        return {'sucesso': False, 'mensagem': f"Falha no cadastro: {str(e)}"}

def autenticar_usuario(login, senha):
    try:
        # 1. Logar no Supabase Auth
        auth_res = supabase.auth.sign_in_with_password({
            "email": login,
            "password": senha
        })
        
        if not auth_res.user:
            return None
            
        # 2. Buscar dados da empresa vinculada
        user_res = supabase.table('usuarios').select('*, empresas(nome, tipo, documento)').eq('login', login).execute()
        if not user_res.data:
            return None
            
        u = user_res.data[0]
        return {
            'id': u['id'],
            'nome': u['nome'],
            'empresa_id': u['empresa_id'],
            'empresa_nome': u['empresas']['nome'],
            'empresa_tipo': u['empresas']['tipo'],
            'empresa_documento': u['empresas']['documento']
        }
    except Exception as e:
        print("Auth error:", e)
        return None

def obter_empresa(empresa_id):
    try:
        res = supabase.table('empresas').select('*').eq('id', empresa_id).execute()
        return res.data[0] if res.data else None
    except:
        return None

# ═══════════════════════════════════════════
# CATEGORIAS
# ═══════════════════════════════════════════

def criar_categoria(empresa_id, nome):
    try:
        if not empresa_id:
            return {'sucesso': False, 'mensagem': 'Empresa não identificada na sessão.'}
        nome = (nome or '').strip()
        if not nome:
            return {'sucesso': False, 'mensagem': 'Nome da categoria é obrigatório.'}

        # Reutiliza categoria existente para evitar duplicação
        existing = supabase.table('categorias').select('id').eq('empresa_id', empresa_id).eq('nome', nome).limit(1).execute()
        if existing.data:
            return {'sucesso': True, 'id': existing.data[0]['id'], 'nome': nome}

        res = supabase.table('categorias').insert({"empresa_id": empresa_id, "nome": nome}).execute()
        if res.data:
            return {'sucesso': True, 'id': res.data[0]['id'], 'nome': nome}
        return {'sucesso': False, 'mensagem': 'Não foi possível criar a categoria.'}
    except Exception as e:
        return {'sucesso': False, 'mensagem': f'Erro no Banco: {str(e)}'}

def obter_categorias(empresa_id):
    try:
        res = supabase.table('categorias').select('*').eq('empresa_id', empresa_id).order('nome').execute()
        return res.data
    except:
        return []

def deletar_categoria(empresa_id, categoria_id):
    try:
        supabase.table('categorias').delete().eq('id', categoria_id).eq('empresa_id', empresa_id).execute()
        return {'sucesso': True}
    except Exception as e:
        return {'sucesso': False, 'mensagem': str(e)}

# ═══════════════════════════════════════════
# PRODUTOS
# ═══════════════════════════════════════════

def criar_produto(empresa_id, nome, sku='', categoria_id=None, custo=0, preco=0, quantidade=0, minimo=0, descricao='', imagem=None):
    try:
        if not empresa_id: return {'sucesso': False, 'mensagem': 'Empresa não identificada.'}
        
        data = {
            "empresa_id": empresa_id, 
            "nome": nome.strip(), 
            "sku": (sku or '').strip() or None,
            "categoria_id": categoria_id if categoria_id else None, 
            "custo": float(custo or 0), 
            "preco": float(preco or 0),
            "quantidade": int(quantidade or 0), 
            "minimo": int(minimo or 0),
            "descricao": (descricao or '').strip(), 
            "imagem": imagem
        }
        res = supabase.table('produtos').insert(data).execute()
        if not res.data:
            return {'sucesso': False, 'mensagem': 'Erro ao inserir produto no banco.'}
            
        pid = res.data[0]['id']
        
        # Registrar no histórico de forma segura
        try:
            supabase.table('historico').insert({
                "empresa_id": empresa_id, "produto_id": pid, "tipo": 'entrada',
                "quantidade": int(quantidade or 0), "observacoes": 'Cadastro inicial'
            }).execute()
        except: pass # Se falhar o histórico, não trava o cadastro do produto
        
        return {'sucesso': True, 'id': pid}
    except Exception as e:
        return {'sucesso': False, 'mensagem': f'Erro no Banco: {str(e)}'}

def obter_produtos(empresa_id):
    try:
        res = supabase.table('produtos').select('*').eq('empresa_id', empresa_id).order('id', desc=True).execute()
        produtos = res.data or []
        # Buscar categorias separadamente para garantir dados
        if produtos:
            cat_ids = set(p.get('categoria_id') for p in produtos if p.get('categoria_id'))
            if cat_ids:
                cats = supabase.table('categorias').select('id, nome').eq('empresa_id', empresa_id).execute().data or []
                cat_map = {c['id']: c['nome'] for c in cats}
                for p in produtos:
                    p['categoria_nome'] = cat_map.get(p.get('categoria_id'), '')
            else:
                for p in produtos:
                    p['categoria_nome'] = ''
        return produtos
    except Exception as e:
        print(f"Erro em obter_produtos: {e}")
        return []

def obter_produto(empresa_id, produto_id):
    try:
        res = supabase.table('produtos').select('*').eq('id', produto_id).eq('empresa_id', empresa_id).execute()
        return res.data[0] if res.data else None
    except:
        return None

def atualizar_produto(empresa_id, produto_id, dados):
    permitidos = ['nome', 'sku', 'categoria_id', 'custo', 'preco', 'minimo', 'descricao', 'imagem']
    atualizacoes = {k: v for k, v in dados.items() if k in permitidos}
    if not atualizacoes: return {'sucesso': False, 'mensagem': 'Nada para atualizar'}
    try:
        supabase.table('produtos').update(atualizacoes).eq('id', produto_id).eq('empresa_id', empresa_id).execute()
        return {'sucesso': True}
    except Exception as e:
        return {'sucesso': False, 'mensagem': str(e)}

def deletar_produto(empresa_id, produto_id):
    try:
        supabase.table('historico').delete().eq('produto_id', produto_id).eq('empresa_id', empresa_id).execute()
        supabase.table('itens_pedido').delete().eq('produto_id', produto_id).execute()
        supabase.table('produtos').delete().eq('id', produto_id).eq('empresa_id', empresa_id).execute()
        return {'sucesso': True}
    except Exception as e:
        return {'sucesso': False, 'mensagem': str(e)}

def adicionar_estoque(empresa_id, produto_id, quantidade, observacoes=''):
    try:
        r = supabase.table('produtos').select('quantidade').eq('id', produto_id).eq('empresa_id', empresa_id).execute()
        if not r.data: return {'sucesso': False, 'mensagem': 'Produto não encontrado'}
        nova_qtd = r.data[0]['quantidade'] + int(quantidade)
        supabase.table('produtos').update({'quantidade': nova_qtd}).eq('id', produto_id).execute()
        supabase.table('historico').insert({
            "empresa_id": empresa_id, "produto_id": produto_id, "tipo": 'entrada', 
            "quantidade": int(quantidade), "observacoes": observacoes or 'Entrada'
        }).execute()
        return {'sucesso': True, 'nova_quantidade': nova_qtd}
    except Exception as e:
        return {'sucesso': False, 'mensagem': str(e)}

def retirar_estoque(empresa_id, produto_id, quantidade, observacoes=''):
    try:
        r = supabase.table('produtos').select('quantidade').eq('id', produto_id).eq('empresa_id', empresa_id).execute()
        if not r.data: return {'sucesso': False, 'mensagem': 'Produto não encontrado'}
        if r.data[0]['quantidade'] < int(quantidade): return {'sucesso': False, 'mensagem': 'Estoque insuficiente'}
        nova_qtd = r.data[0]['quantidade'] - int(quantidade)
        supabase.table('produtos').update({'quantidade': nova_qtd}).eq('id', produto_id).execute()
        supabase.table('historico').insert({
            "empresa_id": empresa_id, "produto_id": produto_id, "tipo": 'saida', 
            "quantidade": int(quantidade), "observacoes": observacoes or 'Saída'
        }).execute()
        return {'sucesso': True, 'nova_quantidade': nova_qtd}
    except Exception as e:
        return {'sucesso': False, 'mensagem': str(e)}

# ═══════════════════════════════════════════
# VENDEDORES
# ═══════════════════════════════════════════

def criar_vendedor(empresa_id, nome, email='', telefone='', comissao=0):
    try:
        res = supabase.table('vendedores').insert({
            "empresa_id": empresa_id, "nome": nome, "email": email, 
            "telefone": telefone, "comissao": float(comissao or 0)
        }).execute()
        return {'sucesso': True, 'id': res.data[0]['id']}
    except Exception as e:
        return {'sucesso': False, 'mensagem': str(e)}

def obter_vendedores(empresa_id):
    try:
        res = supabase.table('vendedores').select('*').eq('empresa_id', empresa_id).order('nome').execute()
        return res.data
    except:
        return []

def deletar_vendedor(empresa_id, vendedor_id):
    try:
        supabase.table('vendedores').delete().eq('id', vendedor_id).eq('empresa_id', empresa_id).execute()
        return {'sucesso': True}
    except Exception as e:
        return {'sucesso': False, 'mensagem': str(e)}

# ═══════════════════════════════════════════
# PEDIDOS
# ═══════════════════════════════════════════

def criar_pedido(empresa_id, cliente_nome, data, itens, vendedor_id=None, observacoes='', cliente_id=None, data_entrega=None, mensagem_cliente='', forma_pagamento=None, comissao_valor=0):
    try:
        total = sum(float(i['subtotal']) for i in itens)
        qtd_itens = sum(int(i['quantidade']) for i in itens)
        
        p_data = {
            "empresa_id": empresa_id,
            "cliente_nome": cliente_nome,
            "vendedor_id": vendedor_id or None,
            "data": data,
            "data_entrega": data_entrega or None,
            "forma_pagamento": forma_pagamento or None,
            "total": total,
            "quantidade_itens": qtd_itens,
            "status": 'pendente',
            "observacoes": observacoes,
            "mensagem_cliente": mensagem_cliente,
            "comissao_valor": float(comissao_valor or 0),
            "cliente_id": cliente_id
        }
        res = supabase.table('pedidos').insert(p_data).execute()
        pedido_id = res.data[0]['id']
        
        for item in itens:
            supabase.table('itens_pedido').insert({
                "pedido_id": pedido_id,
                "produto_id": item['produto_id'],
                "quantidade": int(item['quantidade']),
                "preco_unitario": float(item['preco']),
                "subtotal": float(item['subtotal'])
            }).execute()
            
            # Atualizar estoque
            r = supabase.table('produtos').select('quantidade').eq('id', item['produto_id']).eq('empresa_id', empresa_id).execute()
            if r.data:
                nova_qtd = max(0, r.data[0]['quantidade'] - int(item['quantidade']))
                supabase.table('produtos').update({'quantidade': nova_qtd}).eq('id', item['produto_id']).execute()
                supabase.table('historico').insert({
                    "empresa_id": empresa_id,
                    "produto_id": item['produto_id'],
                    "tipo": 'saida',
                    "quantidade": int(item['quantidade']),
                    "observacoes": f'Pedido #{pedido_id} - {cliente_nome}'
                }).execute()
                
        return {'sucesso': True, 'id': pedido_id}
    except Exception as e:
        return {'sucesso': False, 'mensagem': str(e)}

def obter_pedidos(empresa_id=None, cliente_id=None):
    try:
        if cliente_id:
            res = supabase.table('pedidos').select('*, vendedores(nome), empresas!pedidos_empresa_id_fkey(nome)').eq('cliente_id', cliente_id).order('id', desc=True).execute()
            ps = res.data
            for p in ps:
                p['vendedor_nome'] = p.get('vendedores', {}).get('nome', '') if p.get('vendedores') else ''
                p['fornecedor_nome'] = p.get('empresas', {}).get('nome', '') if p.get('empresas') else ''
            return ps
        else:
            res = supabase.table('pedidos').select('*, vendedores(nome)').eq('empresa_id', empresa_id).order('id', desc=True).execute()
            ps = res.data
            for p in ps:
                p['vendedor_nome'] = p.get('vendedores', {}).get('nome', '') if p.get('vendedores') else ''
            return ps
    except:
        return []

def obter_pedido_detalhado(empresa_id, pedido_id):
    try:
        res = supabase.table('pedidos').select('*').eq('id', pedido_id).eq('empresa_id', empresa_id).execute()
        if not res.data: return None
        pedido = res.data[0]
        ires = supabase.table('itens_pedido').select('*, produtos(nome)').eq('pedido_id', pedido_id).execute()
        itens = ires.data
        for i in itens:
            i['produto_nome'] = i.get('produtos', {}).get('nome', '') if i.get('produtos') else ''
        return {'pedido': pedido, 'itens': itens}
    except:
        return None

def atualizar_status_pedido(empresa_id, pedido_id, status):
    try:
        supabase.table('pedidos').update({'status': status}).eq('id', pedido_id).eq('empresa_id', empresa_id).execute()
        return {'sucesso': True}
    except Exception as e:
        return {'sucesso': False, 'mensagem': str(e)}

def atualizar_pedido(empresa_id, pedido_id, dados):
    permitidos = ['status', 'vendedor_id', 'data_entrega', 'mensagem_cliente', 'observacoes', 'comissao_valor', 'forma_pagamento']
    atualizacoes = {k: v for k, v in dados.items() if k in permitidos}
    if not atualizacoes:
        return {'sucesso': False, 'mensagem': 'Nada para atualizar'}
    try:
        if 'comissao_valor' in atualizacoes:
            atualizacoes['comissao_valor'] = float(atualizacoes['comissao_valor'] or 0)
        supabase.table('pedidos').update(atualizacoes).eq('id', pedido_id).eq('empresa_id', empresa_id).execute()
        return {'sucesso': True}
    except Exception as e:
        return {'sucesso': False, 'mensagem': str(e)}

# ═══════════════════════════════════════════
# HISTÓRICO, REUNIÕES, CONTATOS, DASHBOARD
# ═══════════════════════════════════════════

def obter_historico(empresa_id, filtro_tipo=None, data_inicio=None, data_fim=None):
    try:
        q = supabase.table('historico').select('*, produtos(nome)').eq('empresa_id', empresa_id)
        if filtro_tipo: q = q.eq('tipo', filtro_tipo)
        if data_inicio: q = q.gte('data_hora', data_inicio)
        if data_fim: q = q.lte('data_hora', data_fim + ' 23:59:59')
        res = q.order('data_hora', desc=True).execute()
        hs = res.data
        for h in hs: h['produto_nome'] = h.get('produtos', {}).get('nome', '') if h.get('produtos') else ''
        return hs
    except:
        return []

def criar_reuniao(empresa_id, titulo, descricao, data_hora, local_r='', participantes=''):
    try:
        res = supabase.table('reunioes').insert({"empresa_id": empresa_id, "titulo": titulo, "descricao": descricao, "data_hora": data_hora, "local": local_r, "participantes": participantes}).execute()
        return {'sucesso': True, 'id': res.data[0]['id']}
    except Exception as e:
        return {'sucesso': False, 'mensagem': str(e)}

def obter_reunioes(empresa_id):
    try:
        return supabase.table('reunioes').select('*').eq('empresa_id', empresa_id).order('data_hora', desc=True).execute().data
    except:
        return []

def atualizar_status_reuniao(empresa_id, reuniao_id, status):
    try:
        supabase.table('reunioes').update({'status': status}).eq('id', reuniao_id).eq('empresa_id', empresa_id).execute()
        return {'sucesso': True}
    except Exception as e:
        return {'sucesso': False, 'mensagem': str(e)}

def deletar_reuniao(empresa_id, reuniao_id):
    try:
        supabase.table('reunioes').delete().eq('id', reuniao_id).eq('empresa_id', empresa_id).execute()
        return {'sucesso': True}
    except Exception as e:
        return {'sucesso': False, 'mensagem': str(e)}

def criar_contato(empresa_id, nome, documento='', email='', telefone='', endereco='', tipo='cliente'):
    try:
        res = supabase.table('contatos').insert({"empresa_id": empresa_id, "nome": nome, "documento": documento, "email": email, "telefone": telefone, "endereco": endereco, "tipo": tipo}).execute()
        return {'sucesso': True, 'id': res.data[0]['id']}
    except Exception as e:
        return {'sucesso': False, 'mensagem': str(e)}

def obter_contatos(empresa_id):
    try:
        return supabase.table('contatos').select('*').eq('empresa_id', empresa_id).order('nome').execute().data
    except:
        return []

def deletar_contato(empresa_id, contato_id):
    try:
        supabase.table('contatos').delete().eq('id', contato_id).eq('empresa_id', empresa_id).execute()
        return {'sucesso': True}
    except Exception as e:
        return {'sucesso': False, 'mensagem': str(e)}

def obter_dashboard(empresa_id):
    try:
        # Usando Python para contagens por limitação do Supabase no client básico (aggregate functions)
        p_res = supabase.table('produtos').select('quantidade, preco, minimo').eq('empresa_id', empresa_id).execute().data or []
        pd_res = supabase.table('pedidos').select('total').eq('empresa_id', empresa_id).execute().data or []
        v_res = supabase.table('vendedores').select('id').eq('empresa_id', empresa_id).execute().data or []
        r_res = supabase.table('reunioes').select('id').eq('empresa_id', empresa_id).eq('status', 'agendada').execute().data or []
        
        total_produtos = len(p_res)
        valor_total = sum(p['quantidade'] * p['preco'] for p in p_res)
        sem_estoque = sum(1 for p in p_res if p['quantidade'] <= 0)
        produtos_baixos = sum(1 for p in p_res if p['quantidade'] <= p.get('minimo', 0) and p['quantidade'] > 0)
        
        return {
            'total_produtos': total_produtos,
            'valor_total': valor_total,
            'produtos_baixos': produtos_baixos,
            'sem_estoque': sem_estoque,
            'total_pedidos': len(pd_res),
            'valor_pedidos': sum(p['total'] for p in pd_res),
            'total_vendedores': len(v_res),
            'reunioes_pendentes': len(r_res),
        }
    except Exception as e:
        print(f"Erro no dashboard: {e}")
        return {
            'total_produtos': 0, 'valor_total': 0, 'produtos_baixos': 0, 'sem_estoque': 0,
            'total_pedidos': 0, 'valor_pedidos': 0, 'total_vendedores': 0, 'reunioes_pendentes': 0
        }

# ═══════════════════════════════════════════
# AVISOS E NOTIFICAÇÕES
# ═══════════════════════════════════════════

def criar_aviso(empresa_id, tipo, titulo, mensagem='', prioridade='normal', data_agendada=None):
    """Cria um aviso/notificação para a empresa"""
    try:
        data = {
            "empresa_id": empresa_id,
            "tipo": tipo,
            "titulo": titulo,
            "mensagem": mensagem,
            "prioridade": prioridade
        }
        if data_agendada:
            data["data_agendada"] = data_agendada
        
        res = supabase.table('avisos').insert(data).execute()
        return {'sucesso': True, 'id': res.data[0]['id']}
    except Exception as e:
        return {'sucesso': False, 'mensagem': str(e)}

def obter_avisos(empresa_id, nao_lidos_somente=False):
    """Obtém avisos da empresa"""
    try:
        q = supabase.table('avisos').select('*').eq('empresa_id', empresa_id)
        if nao_lidos_somente:
            q = q.eq('lido', False)
        res = q.order('data_criacao', desc=True).execute()
        return res.data
    except:
        return []

def contar_avisos_nao_lidos(empresa_id):
    """Conta avisos não lidos"""
    try:
        res = supabase.table('avisos').select('id', count='exact').eq('empresa_id', empresa_id).eq('lido', False).execute()
        return res.count or 0
    except:
        return 0

def marcar_aviso_lido(empresa_id, aviso_id):
    """Marca um aviso como lido"""
    try:
        supabase.table('avisos').update({'lido': True}).eq('id', aviso_id).eq('empresa_id', empresa_id).execute()
        return {'sucesso': True}
    except Exception as e:
        return {'sucesso': False, 'mensagem': str(e)}

def deletar_aviso(empresa_id, aviso_id):
    """Deleta um aviso"""
    try:
        supabase.table('avisos').delete().eq('id', aviso_id).eq('empresa_id', empresa_id).execute()
        return {'sucesso': True}
    except Exception as e:
        return {'sucesso': False, 'mensagem': str(e)}

# ═══════════════════════════════════════════
# PERFIL DA LOJA
# ═══════════════════════════════════════════

def salvar_perfil_loja(empresa_id, nome_loja=None, descricao=None, foto_loja=None, foto_banner=None, cor_principal=None, cor_secundaria=None, horario_funcionamento=None, formas_pagamento=None, link_whatsapp=None, link_instagram=None, link_facebook=None):
    """Salva ou atualiza o perfil da loja"""
    try:
        data = {"data_atualizacao": "now()"}
        if nome_loja: data["nome_loja"] = nome_loja
        if descricao: data["descricao"] = descricao
        if foto_loja: data["foto_loja"] = foto_loja
        if foto_banner: data["foto_banner"] = foto_banner
        if cor_principal: data["cor_principal"] = cor_principal
        if cor_secundaria: data["cor_secundaria"] = cor_secundaria
        if horario_funcionamento: data["horario_funcionamento"] = horario_funcionamento
        if formas_pagamento: data["formas_pagamento"] = formas_pagamento
        if link_whatsapp: data["link_whatsapp"] = link_whatsapp
        if link_instagram: data["link_instagram"] = link_instagram
        if link_facebook: data["link_facebook"] = link_facebook
        
        res = supabase.table('perfil_loja').upsert({"empresa_id": empresa_id, **data}, on_conflict='empresa_id').execute()
        return {'sucesso': True}
    except Exception as e:
        return {'sucesso': False, 'mensagem': str(e)}

def obter_perfil_loja(empresa_id):
    """Obtém o perfil da loja"""
    try:
        res = supabase.table('perfil_loja').select('*').eq('empresa_id', empresa_id).execute()
        return res.data[0] if res.data else None
    except:
        return None

def listar_fornecedores():
    """Lista todos os fornecedores"""
    try:
        res = supabase.table('empresas').select('id, nome, tipo, telefone, email, endereco').eq('tipo', 'fornecedor').order('nome').execute()
        return res.data
    except:
        return []

def listar_clientes():
    """Lista todos os clientes"""
    try:
        res = supabase.table('empresas').select('id, nome, tipo, telefone, email, endereco').eq('tipo', 'cliente').order('nome').execute()
        return res.data
    except:
        return []

# ═══════════════════════════════════════════
# NOTIFICAÇÕES DIRECIONADAS
# ═══════════════════════════════════════════

def criar_notificacao(empresa_id, tipo, titulo, mensagem='', cliente_id=None, fornecedor_id=None):
    """Cria notificação direcionada para cliente específico"""
    try:
        data = {
            'empresa_id': empresa_id,
            'tipo': tipo,  # 'novo_produto', 'promocao', 'convite', 'pedido_atualizado'
            'titulo': titulo,
            'mensagem': mensagem,
            'cliente_id': cliente_id,
            'fornecedor_id': fornecedor_id,
            'lida': False
        }
        res = supabase.table('notificacoes').insert(data).execute()
        return {'sucesso': True, 'id': res.data[0]['id'] if res.data else None}
    except Exception as e:
        return {'sucesso': False, 'mensagem': str(e)}

def obter_notificacoes(empresa_id, nao_lidas_somente=False):
    """Obtém notificações para um cliente"""
    try:
        query = supabase.table('notificacoes').select('*').eq('cliente_id', empresa_id)
        if nao_lidas_somente:
            query = query.eq('lida', False)
        res = query.order('criado_em', desc=True).execute()
        return res.data or []
    except:
        return []

def marcar_notificacao_lida(empresa_id, notificacao_id):
    """Marca notificação como lida"""
    try:
        supabase.table('notificacoes').update({'lida': True}).eq('id', notificacao_id).eq('cliente_id', empresa_id).execute()
        return {'sucesso': True}
    except Exception as e:
        return {'sucesso': False, 'mensagem': str(e)}

def deletar_notificacao(empresa_id, notificacao_id):
    """Deleta notificação"""
    try:
        supabase.table('notificacoes').delete().eq('id', notificacao_id).eq('cliente_id', empresa_id).execute()
        return {'sucesso': True}
    except Exception as e:
        return {'sucesso': False, 'mensagem': str(e)}

def contar_notificacoes_nao_lidas(empresa_id):
    """Conta notificações não lidas"""
    try:
        res = supabase.table('notificacoes').select('id', count='exact').eq('cliente_id', empresa_id).eq('lida', False).execute()
        return res.count or 0
    except:
        return 0

# ═══════════════════════════════════════════
# COMPARTILHAMENTO DE VITRINE
# ═══════════════════════════════════════════

def compartilhar_vitrine(fornecedor_id, cliente_id, metodo='convite'):
    """Registra compartilhamento de vitrine (convite ou link)"""
    try:
        # Verifica se já foi compartilhado
        existing = supabase.table('vitrines_compartilhadas').select('id').eq('fornecedor_id', fornecedor_id).eq('cliente_id', cliente_id).execute()
        if existing.data:
            return {'sucesso': True, 'mensagem': 'Já compartilhado', 'id': existing.data[0]['id']}

        data = {
            'fornecedor_id': fornecedor_id,
            'cliente_id': cliente_id,
            'metodo': metodo,  # 'convite' ou 'link'
            'aceito': False
        }
        res = supabase.table('vitrines_compartilhadas').insert(data).execute()
        return {'sucesso': True, 'id': res.data[0]['id'] if res.data else None}
    except Exception as e:
        return {'sucesso': False, 'mensagem': str(e)}

def aceitar_compartilhamento(cliente_id, compartilhamento_id):
    """Cliente aceita compartilhamento de vitrine"""
    try:
        supabase.table('vitrines_compartilhadas').update({'aceito': True}).eq('id', compartilhamento_id).eq('cliente_id', cliente_id).execute()
        return {'sucesso': True}
    except Exception as e:
        return {'sucesso': False, 'mensagem': str(e)}

def obter_fornecedores_compartilhados(cliente_id, aceitos_somente=False):
    """Obtém fornecedores que compartilharam vitrine com cliente"""
    try:
        query = supabase.table('vitrines_compartilhadas').select('*, empresas(id, nome, email, telefone, endereco)').eq('cliente_id', cliente_id)
        if aceitos_somente:
            query = query.eq('aceito', True)
        res = query.order('criado_em', desc=True).execute()

        fornecedores = []
        for item in (res.data or []):
            if item.get('empresas'):
                forn = item['empresas']
                forn['compartilhamento_id'] = item['id']
                forn['aceito'] = item['aceito']
                forn['metodo'] = item['metodo']
                forn['criado_em'] = item['criado_em']
                fornecedores.append(forn)
        return fornecedores
    except Exception as e:
        print(f"Erro em obter_fornecedores_compartilhados: {e}")
        return []

def registrar_visita_vitrine(fornecedor_id, cliente_id):
    """Registra quando um cliente visita a vitrine de um fornecedor"""
    try:
        data = {
            'fornecedor_id': fornecedor_id,
            'cliente_id': cliente_id,
            'visitado_em': 'now()'
        }
        supabase.table('visitantes_vitrine').insert(data).execute()
        return {'sucesso': True}
    except:
        pass  # Não interrompe se falhar

def obter_visitantes_vitrine(fornecedor_id):
    """Obtém lista de visitantes da vitrine de um fornecedor"""
    try:
        res = supabase.table('visitantes_vitrine').select('*, empresas(id, nome, email, telefone)').eq('fornecedor_id', fornecedor_id).order('visitado_em', desc=True).execute()

        visitantes = []
        for item in (res.data or []):
            if item.get('empresas'):
                vis = item['empresas']
                vis['visitado_em'] = item['visitado_em']
                visitantes.append(vis)
        return visitantes
    except:
        return []

# ═══════════════════════════════════════════
# RELATÓRIOS
# ═══════════════════════════════════════════

def obter_relatorio_fornecedor(fornecedor_id):
    """Relatório completo para fornecedor"""
    try:
        prods = supabase.table('produtos').select('id, quantidade, preco, custo').eq('empresa_id', fornecedor_id).execute().data or []
        pedidos = supabase.table('pedidos').select('id, total, status, criado_em').eq('empresa_id', fornecedor_id).execute().data or []
        visitantes = obter_visitantes_vitrine(fornecedor_id)
        compartilhamentos = supabase.table('vitrines_compartilhadas').select('id, cliente_id, aceito, criado_em').eq('fornecedor_id', fornecedor_id).execute().data or []

        total_produtos = len(prods)
        valor_estoque = sum(p.get('quantidade', 0) * p.get('preco', 0) for p in prods)
        total_vendas = sum(p.get('total', 0) for p in pedidos)
        total_pedidos = len(pedidos)
        pedidos_pendentes = sum(1 for p in pedidos if p.get('status') == 'pendente')

        return {
            'total_produtos': total_produtos,
            'valor_estoque': valor_estoque,
            'total_pedidos': total_pedidos,
            'total_vendas': total_vendas,
            'pedidos_pendentes': pedidos_pendentes,
            'visitantes_vitrine': len(visitantes),
            'compartilhamentos_total': len(compartilhamentos),
            'compartilhamentos_aceitos': sum(1 for c in compartilhamentos if c.get('aceito')),
            'visitantes': visitantes[:10],  # Últimos 10
            'pedidos_recentes': pedidos[-5:] if pedidos else []  # Últimos 5
        }
    except Exception as e:
        print(f"Erro em obter_relatorio_fornecedor: {e}")
        return {}

def obter_relatorio_cliente(cliente_id):
    """Relatório completo para cliente"""
    try:
        pedidos = supabase.table('pedidos').select('id, total, status, criado_em').eq('cliente_id', cliente_id).execute().data or []
        fornecedores = obter_fornecedores_compartilhados(cliente_id)
        notificacoes = supabase.table('notificacoes').select('id, lida, criado_em').eq('cliente_id', cliente_id).execute().data or []

        total_pedidos = len(pedidos)
        total_gasto = sum(p.get('total', 0) for p in pedidos)
        pedidos_pendentes = sum(1 for p in pedidos if p.get('status') == 'pendente')

        return {
            'total_pedidos': total_pedidos,
            'total_gasto': total_gasto,
            'pedidos_pendentes': pedidos_pendentes,
            'fornecedores_compartilhados': len(fornecedores),
            'fornecedores_aceitos': sum(1 for f in fornecedores if f.get('aceito')),
            'notificacoes_nao_lidas': sum(1 for n in notificacoes if not n.get('lida')),
            'fornecedores': fornecedores[:10],  # Últimos 10
            'pedidos_recentes': pedidos[-5:] if pedidos else []  # Últimos 5
        }
    except Exception as e:
        print(f"Erro em obter_relatorio_cliente: {e}")
        return {}

