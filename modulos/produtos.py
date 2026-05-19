"""
Módulo de Gestão de Produtos com Inventário
Integrado com Dashboard e Notificações de Estoque
"""

import os
from datetime import datetime
from supabase_db import supabase

# ═══════════════════════════════════════════
# PRODUTOS COM VALIDAÇÃO
# ═══════════════════════════════════════════

def criar_produto_completo(empresa_id, dados_produto):
    """
    Cria um produto com validações completas
    
    Args:
        empresa_id: ID da empresa (fornecedor)
        dados_produto: dict com {nome, sku, categoria_id, custo, preco, quantidade, 
                                   minimo, descricao, imagem_url, codigo_barras}
    """
    try:
        # Validações
        if not dados_produto.get('nome') or len(dados_produto['nome'].strip()) < 3:
            return {'sucesso': False, 'erro': 'Nome do produto deve ter pelo menos 3 caracteres'}
        
        if dados_produto.get('preco', 0) <= 0:
            return {'sucesso': False, 'erro': 'Preço deve ser maior que zero'}
        
        if dados_produto.get('custo', 0) < 0:
            return {'sucesso': False, 'erro': 'Custo não pode ser negativo'}
        
        if dados_produto.get('quantidade', 0) < 0:
            return {'sucesso': False, 'erro': 'Quantidade não pode ser negativa'}
        
        # Verificar SKU duplicado
        if dados_produto.get('sku'):
            sku_check = supabase.table('produtos').select('id').eq(
                'empresa_id', empresa_id
            ).eq('sku', dados_produto['sku']).execute()
            
            if sku_check.data:
                return {'sucesso': False, 'erro': 'SKU já existe para este fornecedor'}
        
        margem_lucro = round(((float(dados_produto.get('preco', 0)) - float(dados_produto.get('custo', 0))) / float(dados_produto.get('preco', 1)) * 100), 2) if dados_produto.get('preco', 0) > 0 else 0
        imagem = dados_produto.get('imagem_url', '') or dados_produto.get('imagem', '')

        # Dados garantidos no schema principal atual do projeto.
        produto_base = {
            'empresa_id': empresa_id,
            'nome': dados_produto['nome'].strip(),
            'sku': dados_produto.get('sku', '').strip() or None,
            'categoria_id': dados_produto.get('categoria_id'),
            'custo': float(dados_produto.get('custo', 0)),
            'preco': float(dados_produto.get('preco', 0)),
            'quantidade': int(dados_produto.get('quantidade', 0)),
            'minimo': int(dados_produto.get('minimo', 0)),
            'descricao': dados_produto.get('descricao', '').strip(),
            'imagem': imagem
        }

        # Campos novos: são usados quando a tabela já recebeu a migração.
        produto_completo = {
            **produto_base,
            'ativo': True,
            'imagem_url': dados_produto.get('imagem_url', ''),
            'codigo_barras': dados_produto.get('codigo_barras', '').strip() or None,
            'margem_lucro': margem_lucro
        }
        
        # Criar produto. Se o Supabase ainda não tiver as colunas novas,
        # salva com o schema base para o produto aparecer no inventário.
        try:
            res = supabase.table('produtos').insert(produto_completo).execute()
        except Exception:
            res = supabase.table('produtos').insert(produto_base).execute()
        
        if not res.data:
            return {'sucesso': False, 'erro': 'Erro ao criar produto'}
        
        novo_produto = res.data[0]
        
        # Criar histórico de inventário inicial
        criar_movimento_inventario(
            produto_id=novo_produto['id'],
            tipo='entrada',
            quantidade=novo_produto['quantidade'],
            motivo='Criação inicial de produto',
            usuario_id=None,
            observacoes='Estoque inicial'
        )
        
        return {
            'sucesso': True,
            'produto_id': novo_produto['id'],
            'produto': novo_produto,
            'mensagem': 'Produto criado com sucesso'
        }
    
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


def atualizar_estoque(produto_id, quantidade_nova, motivo='Ajuste manual'):
    """Atualiza estoque e cria histórico"""
    try:
        # Obter estoque atual
        res = supabase.table('produtos').select('quantidade').eq('id', produto_id).execute()
        if not res.data:
            return {'sucesso': False, 'erro': 'Produto não encontrado'}
        
        estoque_atual = res.data[0]['quantidade']
        diferenca = quantidade_nova - estoque_atual
        
        # Atualizar estoque
        upd = supabase.table('produtos').update(
            {'quantidade': quantidade_nova}
        ).eq('id', produto_id).execute()
        
        if not upd.data:
            return {'sucesso': False, 'erro': 'Erro ao atualizar estoque'}
        
        # Registrar movimento
        tipo_mov = 'entrada' if diferenca > 0 else 'saida'
        criar_movimento_inventario(
            produto_id=produto_id,
            tipo=tipo_mov,
            quantidade=abs(diferenca),
            motivo=motivo,
            observacoes=f'Estoque anterior: {estoque_atual}, Novo: {quantidade_nova}'
        )
        
        # Verificar nível mínimo e criar notificação se necessário
        produto = supabase.table('produtos').select('*').eq('id', produto_id).execute()
        if produto.data:
            p = produto.data[0]
            if quantidade_nova <= p.get('minimo', 0):
                criar_alerta_estoque_baixo(p)
        
        return {'sucesso': True, 'diferenca': diferenca, 'novo_estoque': quantidade_nova}
    
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


def criar_movimento_inventario(produto_id, tipo, quantidade, motivo, usuario_id=None, observacoes=''):
    """
    Registra movimento de estoque (entrada/saída)
    
    Args:
        tipo: 'entrada' ou 'saida'
    """
    try:
        movimento = {
            'produto_id': produto_id,
            'tipo': tipo,
            'quantidade': quantidade,
            'motivo': motivo,
            'usuario_id': usuario_id,
            'observacoes': observacoes,
            'data': datetime.now().isoformat()
        }
        
        res = supabase.table('movimentacoes_estoque').insert(movimento).execute()
        return {'sucesso': bool(res.data), 'id': res.data[0]['id'] if res.data else None}
    
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


def obter_movimentos_produto(produto_id, limite=50):
    """Retorna histórico de movimentações do produto"""
    try:
        res = supabase.table('movimentacoes_estoque').select('*').eq(
            'produto_id', produto_id
        ).order('data', desc=True).limit(limite).execute()
        return res.data or []
    except Exception as e:
        return []


def criar_alerta_estoque_baixo(produto):
    """Cria alerta quando estoque atinge nível mínimo"""
    try:
        # Verificar se não existe alerta recente
        existe = supabase.table('alertas_estoque').select('id').eq(
            'produto_id', produto['id']
        ).eq('status', 'aberto').execute()
        
        if existe.data:
            return {'sucesso': False, 'erro': 'Alerta já existe'}
        
        alerta = {
            'produto_id': produto['id'],
            'empresa_id': produto['empresa_id'],
            'nome_produto': produto['nome'],
            'estoque_atual': produto['quantidade'],
            'estoque_minimo': produto.get('minimo', 0),
            'mensagem': f"Estoque baixo: {produto['nome']} - Atual: {produto['quantidade']}, Mínimo: {produto.get('minimo', 0)}",
            'status': 'aberto',
            'data_criacao': datetime.now().isoformat()
        }
        
        res = supabase.table('alertas_estoque').insert(alerta).execute()
        return {'sucesso': bool(res.data), 'alerta_id': res.data[0]['id'] if res.data else None}
    
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


def obter_alertas_estoque(empresa_id, filtro_status='aberto'):
    """Retorna alertas de estoque da empresa"""
    try:
        query = supabase.table('alertas_estoque').select('*').eq('empresa_id', empresa_id)
        
        if filtro_status:
            query = query.eq('status', filtro_status)
        
        res = query.order('data_criacao', desc=True).execute()
        return res.data or []
    
    except Exception as e:
        return []


def obter_estatisticas_inventario(empresa_id):
    """Retorna estatísticas de inventário"""
    try:
        # Total de produtos
        produtos = supabase.table('produtos').select('id, quantidade, custo, preco').eq(
            'empresa_id', empresa_id
        ).execute()
        
        if not produtos.data:
            return {
                'total_produtos': 0,
                'valor_total_custo': 0,
                'valor_total_venda': 0,
                'quantidade_total': 0,
                'alertas_abertos': 0
            }
        
        total_custo = sum(p.get('quantidade', 0) * p.get('custo', 0) for p in produtos.data)
        total_venda = sum(p.get('quantidade', 0) * p.get('preco', 0) for p in produtos.data)
        total_qtd = sum(p.get('quantidade', 0) for p in produtos.data)
        
        # Contar alertas
        alertas = supabase.table('alertas_estoque').select(
            'id', count='exact'
        ).eq('empresa_id', empresa_id).eq('status', 'aberto').execute()
        
        alertas_count = len(alertas.data) if alertas.data else 0
        
        return {
            'total_produtos': len(produtos.data),
            'valor_total_custo': round(total_custo, 2),
            'valor_total_venda': round(total_venda, 2),
            'valor_lucro_potencial': round(total_venda - total_custo, 2),
            'quantidade_total': total_qtd,
            'alertas_abertos': alertas_count,
            'rotatividade': 'Alta' if total_qtd > 1000 else 'Média' if total_qtd > 100 else 'Baixa'
        }
    
    except Exception as e:
        return {'erro': str(e)}
