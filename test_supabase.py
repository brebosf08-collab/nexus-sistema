import os
import sys

try:
    from supabase import create_client, Client
except ImportError:
    print("ERRO: Pacote supabase nao encontrado. Rode: pip install supabase")
    sys.exit(1)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://gtctfqphvsczeenpysco.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
if not SUPABASE_KEY:
    print("ERRO: SUPABASE_KEY não definido. Defina a variável de ambiente SUPABASE_KEY.")
    sys.exit(1)

print("Testando conexao...")
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    res = supabase.table('empresas').select('id').limit(1).execute()
    print("SUCESSO: Conseguiu ler a tabela empresas! O Banco de dados esta configurado corretamente.")
except Exception as e:
    print(f"ERRO DE CONEXAO OU BANCO DE DADOS: {e}")
