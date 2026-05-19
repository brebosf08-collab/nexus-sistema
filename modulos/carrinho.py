"""
Módulo de Carrinho de Compras
Permite clientes adicionar produtos ao carrinho e fazer pedidos
"""

from datetime import datetime
from supabase_db import supabase, criar_pedido

# ═══════════════════════════════════════════
# CARRINHO DE COMPRAS
# ═══════════════════════════════════════════

def adicionar_ao_carrinho(cliente_id, produto_id, quantidade, fornecedor_id):
    """Adiciona um produto ao carrinho do cliente"""
    try:
        # Validações
        if quantidade <= 0:
            return {'sucesso': False, 'erro': 'Quantidade deve ser maior que zero'}
        
        # Buscar produto para validar
        produto = supabase.table('produtos').select('*').eq('id', produto_id).eq('empresa_id', fornecedor_id).execute()
        if not produto.data:
            return {'sucesso': False, 'erro': 'Produto não encontrado'}
        
        prod = produto.data[0]
        
        # Verificar estoque
        if prod.get('quantidade', 0) < quantidade:
            return {
                'sucesso': False, 
                'erro': f'Estoque insuficiente. Disponível: {prod.get("quantidade", 0)} unidades'
            }
        
        # Verificar se já existe no carrinho
        existe = supabase.table('carrinho').select('id, quantidade').eq(
            'cliente_id', cliente_id
        ).eq('produto_id', produto_id).eq(
            'fornecedor_id', fornecedor_id
        ).execute()
        
        if existe.data:
            # Atualizar quantidade
            item_id = existe.data[0]['id']
            nova_qtd = existe.data[0].get('quantidade', 0) + quantidade
            
            # Verificar nova quantidade contra estoque
            if nova_qtd > prod.get('quantidade', 0):
                return {
                    'sucesso': False,
                    'erro': f'Quantidade total excede o estoque. Máximo: {prod.get("quantidade", 0)}'
                }
            
            upd = supabase.table('carrinho').update({
                'quantidade': nova_qtd,
                'data_atualizacao': datetime.now().isoformat()
            }).eq('id', item_id).execute()
            
            return {'sucesso': bool(upd.data), 'mensagem': 'Quantidade atualizada no carrinho'}
        
        # Criar novo item
        item = {
            'cliente_id': cliente_id,
            'produto_id': produto_id,
            'fornecedor_id': fornecedor_id,
            'quantidade': quantidade,
            'preco_unitario': prod.get('preco', 0),
            'nome_produto': prod.get('nome', ''),
            'data_criacao': datetime.now().isoformat(),
            'data_atualizacao': datetime.now().isoformat()
        }
        
        res = supabase.table('carrinho').insert(item).execute()
        
        if res.data:
            return {
                'sucesso': True,
                'item_id': res.data[0]['id'],
                'mensagem': f'{prod.get("nome", "Produto")} adicionado ao carrinho'
            }
        
        return {'sucesso': False, 'erro': 'Erro ao adicionar ao carrinho'}
    
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


def obter_carrinho(cliente_id, fornecedor_id=None):
    """Retorna items do carrinho do cliente"""
    try:
        query = supabase.table('carrinho').select('*').eq('cliente_id', cliente_id)
        
        if fornecedor_id:
            query = query.eq('fornecedor_id', fornecedor_id)
        
        res = query.order('data_criacao', desc=False).execute()
        
        # Calcular totais
        items = res.data or []
        total_geral = 0
        total_itens = 0
        
        for item in items:
            subtotal = item.get('quantidade', 0) * item.get('preco_unitario', 0)
            item['subtotal'] = round(subtotal, 2)
            total_geral += subtotal
            total_itens += item.get('quantidade', 0)
        
        return {
            'itens': items,
            'total_itens': total_itens,
            'total_geral': round(total_geral, 2),
            'quantidade_produtos': len(items)
        }
    
    except Exception as e:
        return {'itens': [], 'total_itens': 0, 'total_geral': 0, 'quantidade_produtos': 0}


def remover_do_carrinho(item_id, cliente_id=None):
    """Remove um item do carrinho"""
    try:
        query = supabase.table('carrinho').delete().eq('id', item_id)
        if cliente_id:
            query = query.eq('cliente_id', cliente_id)
        query.execute()
        return {'sucesso': True, 'mensagem': 'Item removido do carrinho'}
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


def atualizar_quantidade_carrinho(item_id, nova_quantidade, cliente_id=None):
    """Atualiza a quantidade de um item no carrinho"""
    try:
        if nova_quantidade <= 0:
            # Se quantidade é 0 ou negativa, remove
            return remover_do_carrinho(item_id, cliente_id)
        
        # Verificar estoque antes de atualizar
        query = supabase.table('carrinho').select('*').eq('id', item_id)
        if cliente_id:
            query = query.eq('cliente_id', cliente_id)
        item = query.execute()
        if not item.data:
            return {'sucesso': False, 'erro': 'Item não encontrado'}
        
        item_data = item.data[0]
        produto = supabase.table('produtos').select('quantidade').eq(
            'id', item_data['produto_id']
        ).execute()
        
        if not produto.data or produto.data[0]['quantidade'] < nova_quantidade:
            return {
                'sucesso': False,
                'erro': f'Estoque insuficiente. Máximo disponível: {produto.data[0]["quantidade"] if produto.data else 0}'
            }
        
        # Atualizar
        upd_query = supabase.table('carrinho').update({
            'quantidade': nova_quantidade,
            'data_atualizacao': datetime.now().isoformat()
        }).eq('id', item_id)
        if cliente_id:
            upd_query = upd_query.eq('cliente_id', cliente_id)
        upd = upd_query.execute()
        
        return {'sucesso': bool(upd.data)}
    
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


def limpar_carrinho(cliente_id, fornecedor_id=None):
    """Remove todos os items do carrinho"""
    try:
        query = supabase.table('carrinho').delete().eq('cliente_id', cliente_id)
        
        if fornecedor_id:
            query = query.eq('fornecedor_id', fornecedor_id)
        
        query.execute()
        return {'sucesso': True, 'mensagem': 'Carrinho limpo'}
    
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


def converter_carrinho_em_pedido(cliente_id, fornecedor_id, dados_pedido):
    """
    Converte items do carrinho em um pedido
    
    Args:
        dados_pedido: dict com {forma_pagamento, data_entrega, mensagem, endereco, telefone}
    """
    try:
        # Obter items do carrinho
        carrinho = obter_carrinho(cliente_id, fornecedor_id)
        
        if not carrinho['itens']:
            return {'sucesso': False, 'erro': 'Carrinho vazio'}
        
        # Validar estoque para todos os items
        for item in carrinho['itens']:
            produto = supabase.table('produtos').select('quantidade').eq(
                'id', item['produto_id']
            ).execute()
            
            if not produto.data or produto.data[0]['quantidade'] < item['quantidade']:
                return {
                    'sucesso': False,
                    'erro': f'Estoque insuficiente para {item["nome_produto"]}'
                }
        
        itens_pedido = [
            {
                'produto_id': item['produto_id'],
                'quantidade': item['quantidade'],
                'preco': item['preco_unitario'],
                'subtotal': item['subtotal']
            }
            for item in carrinho['itens']
        ]

        pedido = criar_pedido(
            fornecedor_id,
            dados_pedido.get('cliente_nome', 'Cliente'),
            datetime.now().date().isoformat(),
            itens_pedido,
            cliente_id=cliente_id,
            data_entrega=dados_pedido.get('data_entrega', None),
            mensagem_cliente=dados_pedido.get('mensagem', ''),
            forma_pagamento=dados_pedido.get('forma_pagamento', 'pendente')
        )

        if not pedido.get('sucesso'):
            return {'sucesso': False, 'erro': pedido.get('mensagem') or pedido.get('erro') or 'Erro ao criar pedido'}

        pedido_id = pedido.get('id')
        
        # Limpar carrinho
        limpar_carrinho(cliente_id, fornecedor_id)
        
        return {
            'sucesso': True,
            'pedido_id': pedido_id,
            'total': carrinho['total_geral'],
            'mensagem': f'Pedido #{pedido_id} criado com sucesso'
        }
    
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


def obter_resumo_carrinho(cliente_id):
    """Retorna resumo do carrinho (total, quantidade de items)"""
    try:
        carrinho = obter_carrinho(cliente_id)
        return {
            'total_itens': carrinho['total_itens'],
            'total_geral': carrinho['total_geral'],
            'quantidade_produtos': carrinho['quantidade_produtos']
        }
    except:
        return {
            'total_itens': 0,
            'total_geral': 0,
            'quantidade_produtos': 0
        }
