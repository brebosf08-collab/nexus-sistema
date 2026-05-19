"""
Módulo de Agendamento de Tarefas
Permite agendar entregas, compromissos, reuniões, etc.
"""

from datetime import datetime, timedelta
from supabase_db import supabase

# ═══════════════════════════════════════════
# AGENDAMENTOS
# ═══════════════════════════════════════════

def criar_agendamento(empresa_id, dados_agenda):
    """
    Cria um agendamento (entrega, reunião, visita, etc)
    
    Args:
        dados_agenda: dict com {tipo, titulo, descricao, data, hora, 
                                local, contato, telefone, email, status}
    """
    try:
        # Validações
        if not dados_agenda.get('titulo') or len(dados_agenda['titulo'].strip()) < 3:
            return {'sucesso': False, 'erro': 'Título deve ter pelo menos 3 caracteres'}
        
        if not dados_agenda.get('data'):
            return {'sucesso': False, 'erro': 'Data é obrigatória'}
        
        # Validar que a data não é no passado
        try:
            data_agenda = datetime.fromisoformat(dados_agenda['data'])
            if data_agenda < datetime.now():
                return {'sucesso': False, 'erro': 'Data não pode ser no passado'}
        except:
            return {'sucesso': False, 'erro': 'Data inválida (formato: YYYY-MM-DD)'}
        
        agendamento = {
            'empresa_id': empresa_id,
            'tipo': dados_agenda.get('tipo', 'outro'),  # entrega, reunião, visita, ligação, etc
            'titulo': dados_agenda['titulo'].strip(),
            'descricao': dados_agenda.get('descricao', '').strip(),
            'data': dados_agenda['data'],
            'hora': dados_agenda.get('hora', '09:00'),
            'local': dados_agenda.get('local', '').strip(),
            'contato': dados_agenda.get('contato', '').strip(),
            'telefone': dados_agenda.get('telefone', '').strip(),
            'email': dados_agenda.get('email', '').strip(),
            'status': 'pendente',  # pendente, confirmado, cancelado, concluído
            'data_criacao': datetime.now().isoformat(),
            'lembrete_enviado': False
        }
        
        res = supabase.table('agendamentos').insert(agendamento).execute()
        
        if not res.data:
            return {'sucesso': False, 'erro': 'Erro ao criar agendamento'}
        
        return {
            'sucesso': True,
            'agendamento_id': res.data[0]['id'],
            'agendamento': res.data[0],
            'mensagem': 'Agendamento criado com sucesso'
        }
    
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


def obter_agendamentos(empresa_id, filtro_data=None, filtro_status=None, limite=100):
    """
    Retorna agendamentos da empresa
    
    Args:
        filtro_data: 'hoje', 'semana', 'mes', 'atrasado' ou None para todos
        filtro_status: 'pendente', 'confirmado', 'cancelado', 'concluído'
    """
    try:
        agora = datetime.now()
        query = supabase.table('agendamentos').select('*').eq('empresa_id', empresa_id)
        
        # Aplicar filtros de data
        if filtro_data == 'hoje':
            data_hoje = agora.date().isoformat()
            query = query.eq('data', data_hoje)
        
        elif filtro_data == 'semana':
            data_inicio = agora.date().isoformat()
            data_fim = (agora + timedelta(days=7)).date().isoformat()
            query = query.gte('data', data_inicio).lte('data', data_fim)
        
        elif filtro_data == 'mes':
            data_inicio = agora.date().isoformat()
            data_fim = (agora + timedelta(days=30)).date().isoformat()
            query = query.gte('data', data_inicio).lte('data', data_fim)
        
        elif filtro_data == 'atrasado':
            data_hoje = agora.date().isoformat()
            query = query.lt('data', data_hoje).eq('status', 'pendente')
        
        # Aplicar filtro de status
        if filtro_status:
            query = query.eq('status', filtro_status)
        
        res = query.order('data', desc=False).limit(limite).execute()
        
        return res.data or []
    
    except Exception as e:
        return []


def atualizar_agendamento(agendamento_id, atualizacoes):
    """Atualiza um agendamento"""
    try:
        res = supabase.table('agendamentos').update(atualizacoes).eq(
            'id', agendamento_id
        ).execute()
        
        if not res.data:
            return {'sucesso': False, 'erro': 'Agendamento não encontrado'}
        
        return {'sucesso': True, 'agendamento': res.data[0]}
    
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


def cancelar_agendamento(agendamento_id, motivo=''):
    """Cancela um agendamento"""
    try:
        atualizacoes = {
            'status': 'cancelado',
            'motivo_cancelamento': motivo,
            'data_cancelamento': datetime.now().isoformat()
        }
        
        return atualizar_agendamento(agendamento_id, atualizacoes)
    
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


def concluir_agendamento(agendamento_id, observacoes=''):
    """Marca um agendamento como concluído"""
    try:
        atualizacoes = {
            'status': 'concluído',
            'observacoes_conclusao': observacoes,
            'data_conclusao': datetime.now().isoformat()
        }
        
        return atualizar_agendamento(agendamento_id, atualizacoes)
    
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


def obter_proximos_agendamentos(empresa_id, dias_afrente=7):
    """Retorna próximos agendamentos"""
    try:
        agora = datetime.now()
        data_inicio = agora.date().isoformat()
        data_fim = (agora + timedelta(days=dias_afrente)).date().isoformat()
        
        res = supabase.table('agendamentos').select('*').eq(
            'empresa_id', empresa_id
        ).gte('data', data_inicio).lte(
            'data', data_fim
        ).eq('status', 'pendente').order('data', desc=False).execute()
        
        return res.data or []
    
    except Exception as e:
        return []


def obter_agendamentos_atrasados(empresa_id):
    """Retorna agendamentos pendentes que estão vencidos"""
    try:
        agora = datetime.now()
        data_hoje = agora.date().isoformat()
        
        res = supabase.table('agendamentos').select('*').eq(
            'empresa_id', empresa_id
        ).lt('data', data_hoje).eq('status', 'pendente').execute()
        
        return res.data or []
    
    except Exception as e:
        return []


def obter_calendar_mês(empresa_id, ano, mes):
    """
    Retorna agendamentos do mês para visualização em calendário
    
    Returns: dict {data: [agendamentos]}
    """
    try:
        from calendar import monthrange
        
        # Calcular primeira e última data do mês
        dias = monthrange(ano, mes)[1]
        data_inicio = f"{ano:04d}-{mes:02d}-01"
        data_fim = f"{ano:04d}-{mes:02d}-{dias:02d}"
        
        res = supabase.table('agendamentos').select('*').eq(
            'empresa_id', empresa_id
        ).gte('data', data_inicio).lte('data', data_fim).execute()
        
        # Agrupar por data
        agendamentos_por_data = {}
        for ag in (res.data or []):
            data = ag['data']
            if data not in agendamentos_por_data:
                agendamentos_por_data[data] = []
            agendamentos_por_data[data].append(ag)
        
        return agendamentos_por_data
    
    except Exception as e:
        return {}


def deletar_agendamento(agendamento_id):
    """Deleta um agendamento"""
    try:
        res = supabase.table('agendamentos').delete().eq('id', agendamento_id).execute()
        return {'sucesso': True}
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}
