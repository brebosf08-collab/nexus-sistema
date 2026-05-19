"""
Módulo de Exportação de Relatórios
Suporta Excel, PDF e CSV
"""

import os
from datetime import datetime
from io import BytesIO, StringIO
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from supabase_db import supabase

# ═══════════════════════════════════════════
# EXPORTAÇÃO PARA EXCEL
# ═══════════════════════════════════════════

def exportar_produtos_excel(empresa_id, filtro_categoria=None):
    """
    Exporta lista de produtos para Excel
    
    Args:
        empresa_id: ID da empresa
        filtro_categoria: ID da categoria (opcional)
    """
    try:
        # Buscar produtos
        query = supabase.table('produtos').select('*').eq(
            'empresa_id', empresa_id
        )
        
        if filtro_categoria:
            query = query.eq('categoria_id', filtro_categoria)
        
        res = query.execute()
        produtos = res.data or []
        
        if not produtos:
            return {'sucesso': False, 'erro': 'Nenhum produto encontrado'}
        
        # Criar DataFrame
        df = pd.DataFrame([
            {
                'SKU': p.get('sku', '-'),
                'Produto': p.get('nome', ''),
                'Categoria': p.get('categoria_id', ''),
                'Custo': f"R$ {p.get('custo', 0):.2f}",
                'Preço': f"R$ {p.get('preco', 0):.2f}",
                'Estoque': p.get('quantidade', 0),
                'Mínimo': p.get('minimo', 0),
                'Margem %': f"{calcular_margem(p.get('custo', 0), p.get('preco', 0), p.get('margem_lucro')):.1f}%",
                'Descrição': p.get('descricao', '')[:50]  # Truncar
            }
            for p in produtos
        ])
        
        # Criar arquivo Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Produtos', index=False)
            
            # Ajustar estilos
            workbook = writer.book
            worksheet = writer.sheets['Produtos']
            
            # Estilo do header
            header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
            header_font = Font(bold=True, color='FFFFFF')
            
            for cell in worksheet[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Ajustar largura das colunas
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        # Salvar arquivo
        nome_arquivo = f"produtos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return {
            'sucesso': True,
            'arquivo': output,
            'nome_arquivo': nome_arquivo,
            'tamanho': len(output.getvalue()),
            'total_registros': len(produtos)
        }
    
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


def exportar_pedidos_excel(empresa_id, data_inicio=None, data_fim=None):
    """
    Exporta pedidos para Excel
    
    Args:
        empresa_id: ID da empresa
        data_inicio: Data inicial (formato: YYYY-MM-DD)
        data_fim: Data final (formato: YYYY-MM-DD)
    """
    try:
        # Buscar pedidos
        query = supabase.table('pedidos').select('*').eq('empresa_id', empresa_id)
        
        if data_inicio:
            query = query.gte('criado_em', f"{data_inicio}T00:00:00")
        if data_fim:
            query = query.lte('criado_em', f"{data_fim}T23:59:59")
        
        res = query.order('criado_em', desc=True).execute()
        pedidos = res.data or []
        
        if not pedidos:
            return {'sucesso': False, 'erro': 'Nenhum pedido encontrado'}
        
        # Criar DataFrame
        df = pd.DataFrame([
            {
                'Pedido #': p.get('id', ''),
                'Data': formatar_data_exportacao(p.get('criado_em') or p.get('data_criacao') or p.get('data')),
                'Cliente': p.get('cliente_nome', ''),
                'Status': p.get('status', 'Pendente'),
                'Total': f"R$ {float(p.get('total') or p.get('valor_total') or 0):.2f}",
                'Itens': p.get('quantidade_itens', 0),
                'Email': p.get('cliente_email', ''),
                'Telefone': p.get('cliente_telefone', '')
            }
            for p in pedidos
        ])
        
        # Criar arquivo Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Pedidos', index=False)
            
            # Estilo
            workbook = writer.book
            worksheet = writer.sheets['Pedidos']
            
            header_fill = PatternFill(start_color='70AD47', end_color='70AD47', fill_type='solid')
            header_font = Font(bold=True, color='FFFFFF')
            
            for cell in worksheet[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Ajustar larguras
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        nome_arquivo = f"pedidos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return {
            'sucesso': True,
            'arquivo': output,
            'nome_arquivo': nome_arquivo,
            'tamanho': len(output.getvalue()),
            'total_registros': len(pedidos)
        }
    
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


def exportar_relatorio_inventario_excel(empresa_id):
    """Exporta relatório completo de inventário"""
    try:
        # Buscar dados
        res = supabase.table('produtos').select('*').eq(
            'empresa_id', empresa_id
        ).execute()
        
        produtos = res.data or []
        
        # Calcular totais
        total_custo = sum(p.get('quantidade', 0) * p.get('custo', 0) for p in produtos)
        total_venda = sum(p.get('quantidade', 0) * p.get('preco', 0) for p in produtos)
        
        # Criar workbook com múltiplas abas
        workbook = Workbook()
        
        # Aba 1: Resumo
        ws_resumo = workbook.active
        ws_resumo.title = 'Resumo'
        
        header_fill = PatternFill(start_color='1F4E78', end_color='1F4E78', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF', size=14)
        
        ws_resumo['A1'] = 'RELATÓRIO DE INVENTÁRIO'
        ws_resumo['A1'].font = header_font
        ws_resumo['A1'].fill = header_fill
        ws_resumo.merge_cells('A1:B1')
        
        ws_resumo['A3'] = 'Data do Relatório'
        ws_resumo['B3'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        
        ws_resumo['A4'] = 'Total de Produtos'
        ws_resumo['B4'] = len(produtos)
        
        ws_resumo['A5'] = 'Quantidade Total em Estoque'
        ws_resumo['B5'] = sum(p.get('quantidade', 0) for p in produtos)
        
        ws_resumo['A6'] = 'Valor Total em Custo'
        ws_resumo['B6'] = f"R$ {total_custo:.2f}"
        
        ws_resumo['A7'] = 'Valor Total em Venda'
        ws_resumo['B7'] = f"R$ {total_venda:.2f}"
        
        ws_resumo['A8'] = 'Lucro Potencial'
        ws_resumo['B8'] = f"R$ {total_venda - total_custo:.2f}"
        
        # Aba 2: Produtos detalhados
        ws_produtos = workbook.create_sheet('Produtos')
        
        df_produtos = pd.DataFrame([
            {
                'SKU': p.get('sku', '-'),
                'Nome': p.get('nome', ''),
                'Quantidade': p.get('quantidade', 0),
                'Mínimo': p.get('minimo', 0),
                'Custo Unit.': f"R$ {p.get('custo', 0):.2f}",
                'Preço Unit.': f"R$ {p.get('preco', 0):.2f}",
                'Total Custo': f"R$ {p.get('quantidade', 0) * p.get('custo', 0):.2f}",
                'Total Venda': f"R$ {p.get('quantidade', 0) * p.get('preco', 0):.2f}",
                'Status': 'Crítico' if p.get('quantidade', 0) <= p.get('minimo', 0) else 'Normal'
            }
            for p in sorted(produtos, key=lambda x: x.get('nome', ''))
        ])
        
        # Escrever manualmente para melhor controle
        for r_idx, row in enumerate(df_produtos.itertuples(index=False), 1):
            for c_idx, value in enumerate(row, 1):
                cell = ws_produtos.cell(row=r_idx+1, column=c_idx, value=value)
                if r_idx == 0:  # Header
                    cell.font = header_font
                    cell.fill = header_fill
        
        # Aba 3: Alertas
        alertas = [p for p in produtos if p.get('quantidade', 0) <= p.get('minimo', 0)]
        
        if alertas:
            ws_alertas = workbook.create_sheet('Alertas de Estoque')
            
            df_alertas = pd.DataFrame([
                {
                    'Produto': p.get('nome', ''),
                    'Estoque Atual': p.get('quantidade', 0),
                    'Estoque Mínimo': p.get('minimo', 0),
                    'Diferença': p.get('minimo', 0) - p.get('quantidade', 0),
                    'Prioridade': 'Crítica' if p.get('quantidade', 0) == 0 else 'Alta'
                }
                for p in alertas
            ])
            
            # Usar pandas para escrever
            for r_idx, row in enumerate(df_alertas.itertuples(index=False), 1):
                for c_idx, value in enumerate(row, 1):
                    ws_alertas.cell(row=r_idx+1, column=c_idx, value=value)
        
        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        
        nome_arquivo = f"relatorio_inventario_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return {
            'sucesso': True,
            'arquivo': output,
            'nome_arquivo': nome_arquivo,
            'tamanho': len(output.getvalue())
        }
    
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


# ═══════════════════════════════════════════
# EXPORTAÇÃO PARA CSV
# ═══════════════════════════════════════════

def exportar_produtos_csv(empresa_id):
    """Exporta produtos para CSV"""
    try:
        res = supabase.table('produtos').select('*').eq(
            'empresa_id', empresa_id
        ).execute()
        
        produtos = res.data or []
        
        df = pd.DataFrame(produtos)
        csv_text = StringIO()
        df.to_csv(csv_text, index=False)
        output = BytesIO(csv_text.getvalue().encode('utf-8-sig'))
        output.seek(0)
        
        nome_arquivo = f"produtos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return {
            'sucesso': True,
            'arquivo': output,
            'nome_arquivo': nome_arquivo,
            'tamanho': len(output.getvalue())
        }
    
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


# ═══════════════════════════════════════════
# EXPORTAÇÃO PARA PDF (SIMPLES)
# ═══════════════════════════════════════════

def exportar_relatorio_pdf_simples(empresa_id, tipo='inventario'):
    """
    Exporta relatório simples em PDF
    
    Requires: reportlab (pip install reportlab)
    """
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib import colors
        from reportlab.pdfgen import canvas
        
        # Buscar dados
        if tipo == 'inventario':
            res = supabase.table('produtos').select('*').eq(
                'empresa_id', empresa_id
            ).execute()
            
            produtos = res.data or []
            
            # Preparar dados da tabela
            data = [['SKU', 'Produto', 'Qtd', 'Preço', 'Total']]
            
            total_geral = 0
            for p in produtos[:20]:  # Limitar a 20 para caber na página
                sku = p.get('sku', '-')
                nome = p.get('nome', '')[:30]
                qtd = p.get('quantidade', 0)
                preco = p.get('preco', 0)
                total = qtd * preco
                total_geral += total
                
                data.append([
                    str(sku),
                    nome,
                    str(qtd),
                    f"R$ {preco:.2f}",
                    f"R$ {total:.2f}"
                ])
            
            data.append(['', '', '', 'TOTAL:', f"R$ {total_geral:.2f}"])
            
        # Criar PDF
        output = BytesIO()
        doc = SimpleDocTemplate(output, pagesize=A4)
        elements = []
        
        # Título
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1F4E78'),
            spaceAfter=30,
        )
        
        titulo = Paragraph(f"Relatório de {tipo.upper()}", title_style)
        elements.append(titulo)
        elements.append(Spacer(1, 0.3*inch))
        
        # Tabela
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E78')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#F0F0F0')])
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.5*inch))
        
        # Data
        data_rodape = Paragraph(
            f"<i>Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</i>",
            styles['Normal']
        )
        elements.append(data_rodape)
        
        # Compilar PDF
        doc.build(elements)
        output.seek(0)
        
        nome_arquivo = f"relatorio_{tipo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return {
            'sucesso': True,
            'arquivo': output,
            'nome_arquivo': nome_arquivo,
            'tamanho': len(output.getvalue())
        }
    
    except ImportError:
        return {
            'sucesso': False,
            'erro': 'reportlab não está instalado. Execute: pip install reportlab'
        }
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


def registrar_exportacao(empresa_id, tipo, nome_arquivo, formato, quantidade_registros):
    """Registra as exportações realizadas"""
    try:
        registro = {
            'empresa_id': empresa_id,
            'tipo': tipo,
            'nome_arquivo': nome_arquivo,
            'formato': formato,
            'quantidade_registros': quantidade_registros,
            'data_exportacao': datetime.now().isoformat(),
            'usuario_id': None
        }
        
        supabase.table('historico_exportacoes').insert(registro).execute()
    
    except Exception as e:
        print(f"Erro ao registrar exportação: {e}")


def calcular_margem(custo, preco, margem_salva=None):
    if margem_salva is not None:
        return float(margem_salva or 0)

    custo = float(custo or 0)
    preco = float(preco or 0)
    if preco <= 0:
        return 0
    return ((preco - custo) / preco) * 100


def formatar_data_exportacao(valor):
    if not valor:
        return ''

    try:
        return datetime.fromisoformat(str(valor).replace('Z', '+00:00')).strftime('%d/%m/%Y')
    except Exception:
        return str(valor)
