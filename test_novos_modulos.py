"""
Script de Teste para Validar os Novos Módulos
Execute com: python test_novos_modulos.py
"""

import sys
import os

print("=" * 60)
print("🧪 TESTE DE NOVOS MÓDULOS - SISTEMA NEXUS")
print("=" * 60)

# 1. Verificar se as dependências estão instaladas
print("\n1️⃣  Verificando dependências...")
deps = ['pandas', 'openpyxl', 'reportlab', 'schedule', 'requests', 'supabase']
faltando = []

for dep in deps:
    try:
        __import__(dep)
        print(f"   ✅ {dep}")
    except ImportError:
        print(f"   ❌ {dep} - NÃO INSTALADO")
        faltando.append(dep)

if faltando:
    print(f"\n⚠️  Pacotes faltando: {', '.join(faltando)}")
    print("Execute: pip install -r requirements.txt")
    sys.exit(1)

# 2. Verificar módulos locais
print("\n2️⃣  Verificando módulos locais...")
modulos = ['modulos.produtos', 'modulos.agendamento', 'modulos.notificacoes', 'modulos.exportacao']

for mod in modulos:
    try:
        __import__(mod)
        print(f"   ✅ {mod}")
    except ImportError as e:
        print(f"   ❌ {mod} - ERRO: {e}")
        faltando.append(mod)

if faltando:
    print("\n⚠️  Módulos não encontrados! Verifique a estrutura de diretórios.")
    sys.exit(1)

# 3. Importar e testar funções
print("\n3️⃣  Importando funções dos módulos...")
try:
    from modulos.produtos import (
        criar_produto_completo,
        obter_estatisticas_inventario,
        criar_movimento_inventario
    )
    print("   ✅ Módulo de Produtos")
except Exception as e:
    print(f"   ❌ Módulo de Produtos: {e}")

try:
    from modulos.agendamento import (
        criar_agendamento,
        obter_agendamentos,
        obter_proximos_agendamentos
    )
    print("   ✅ Módulo de Agendamentos")
except Exception as e:
    print(f"   ❌ Módulo de Agendamentos: {e}")

try:
    from modulos.notificacoes import (
        criar_notificacao,
        obter_notificacoes,
        enviar_email_notificacao
    )
    print("   ✅ Módulo de Notificações")
except Exception as e:
    print(f"   ❌ Módulo de Notificações: {e}")

try:
    from modulos.exportacao import (
        exportar_produtos_excel,
        exportar_pedidos_excel,
        exportar_relatorio_inventario_excel
    )
    print("   ✅ Módulo de Exportação")
except Exception as e:
    print(f"   ❌ Módulo de Exportação: {e}")

# 4. Verificar endpoints no app.py
print("\n4️⃣  Verificando endpoints em app.py...")
try:
    with open('app.py', 'r', encoding='utf-8') as f:
        conteudo = f.read()
        
    endpoints_esperados = [
        '/api/v2/produtos',
        '/api/v2/estoque',
        '/api/agendamentos',
        '/api/notificacoes',
        '/api/exportar/produtos',
        '/api/dashboard'
    ]
    
    for endpoint in endpoints_esperados:
        if endpoint in conteudo:
            print(f"   ✅ {endpoint}")
        else:
            print(f"   ❌ {endpoint} - NÃO ENCONTRADO")
            
except Exception as e:
    print(f"   ❌ Erro ao verificar app.py: {e}")

# 5. Verificar arquivo de schema
print("\n5️⃣  Verificando arquivo de schema...")
if os.path.exists('SCHEMA_NOVAS_TABELAS.sql'):
    print("   ✅ SCHEMA_NOVAS_TABELAS.sql encontrado")
    with open('SCHEMA_NOVAS_TABELAS.sql', 'r', encoding='utf-8') as f:
        schema = f.read()
        tabelas = ['alertas_estoque', 'movimentacoes_estoque', 'agendamentos', 'notificacoes']
        for tab in tabelas:
            if tab in schema:
                print(f"      ✅ Tabela {tab}")
            else:
                print(f"      ❌ Tabela {tab} não definida")
else:
    print("   ❌ SCHEMA_NOVAS_TABELAS.sql NÃO ENCONTRADO")

# 6. Verificar documentação
print("\n6️⃣  Verificando documentação...")
docs = [
    'GUIA_IMPLEMENTACAO.md',
    'API_ENDPOINTS.md'
]

for doc in docs:
    if os.path.exists(doc):
        print(f"   ✅ {doc}")
    else:
        print(f"   ❌ {doc} não encontrado")

# 7. Verificar ambiente Supabase
print("\n7️⃣  Verificando Supabase...")
try:
    from supabase_db import supabase
    print("   ✅ Supabase conectado")
except Exception as e:
    print(f"   ❌ Erro Supabase: {e}")

print("\n" + "=" * 60)
print("✅ VERIFICAÇÃO COMPLETA!")
print("=" * 60)

print("""
📝 Próximas etapas:

1. Execute SQL em SCHEMA_NOVAS_TABELAS.sql no Supabase
2. Configure .env (email, SMS opcional)
3. Inicie a aplicação: python app.py
4. Acesse http://localhost:8080

📚 Consulte:
   - GUIA_IMPLEMENTACAO.md - Guia completo
   - API_ENDPOINTS.md - Referência de endpoints
   - templates/agendamentos.html - Interface de agendamentos
""")
