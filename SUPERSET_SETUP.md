# Superset Setup for Supabase

Este guia mostra como instalar o Apache Superset localmente e conectar ao banco de dados Supabase.

## 1) Pré-requisitos

- Python 3.14 (já está disponível no `.venv` deste projeto)
- Acesso ao Supabase dashboard para obter a string de conexão Postgres
- Permissão para instalar pacotes Python no ambiente virtual

## 2) Ativar o ambiente virtual

No terminal PowerShell do projeto:

```powershell
cd "C:\Users\breno\OneDrive\Área de Trabalho\test sistema\SISTEMA"
.\.venv\Scripts\Activate.ps1
```

## 3) Instalar Superset e driver Postgres

```powershell
python -m pip install --upgrade pip
python -m pip install apache-superset psycopg[binary]
```

> Se a instalação falhar por dependências, indique o erro aqui. O Superset pode demorar um pouco para baixar tudo.

## 4) Inicializar o Superset

```powershell
superset db upgrade
superset fab create-admin --username admin --firstname Admin --lastname User --email admin@example.com --password SuaSenhaSegura
superset init
```

## 5) Executar o Superset localmente

```powershell
superset run -p 8088 --with-threads --reload --debugger
```

Depois abra `http://localhost:8088` no navegador.

## 6) Conectar Superset ao Supabase

No Superset, vá em `Data` -> `Databases` -> `+ Database`.

Use a conexão Postgres do Supabase obtida em:
- Supabase Dashboard
- Settings > Database > Connection info

### Exemplo de URI SQLAlchemy

```text
postgresql://postgres:<SENHA_DO_SUPABASE>@db.gtctfqphvsczeenpysco.supabase.co:5432/postgres
```

Substitua `<SENHA_DO_SUPABASE>` pela senha do banco.

### Extra JSON para SSL

```json
{"sslmode":"require"}
```

Se precisar, habilite `Allow DML` para leitura/escrita, mas o recomendado é manter somente leitura no Superset enquanto gera relatórios.

## 7) Criar datasets importantes

Pontos de partida:

- `pedidos`
- `itens_pedido`
- `produtos`
- `usuarios` ou `empresas` se quiser dashboards por cliente/fornecedor

## 8) Relatórios inteligentes sugeridos

### Vendas por período

- Dataset: `pedidos`
- Eixo X: data (`criado_em` ou `data`)
- Métrica: `SUM(total)`
- Agrupar por dia, semana ou mês

### Giro de estoque

- Use `itens_pedido` + `produtos`
- Métrica: `SUM(itens_pedido.quantidade)` por produto
- Divida pelas quantidades médias do estoque para calcular giro, ou use consulta SQL customizada no SQL Lab

### Produtos mais pedidos

- Dataset: `itens_pedido`
- Agrupe por `produto_id` ou `produto_nome`
- Métrica: `SUM(quantidade)` ou `COUNT(*)`
- Ordene decrescente

## 9) Criar dashboards

1. Em `Charts`, crie gráficos para cada relatório acima
2. Em `Dashboards`, clique em `+ Dashboard`
3. Adicione os charts criados
4. Ajuste filtros de período e de fornecedor

## 10) Notas de conexão com Supabase

- A URL Supabase pública `https://gtctfqphvsczeenpysco.supabase.co` não é a mesma que a conexão Postgres.
- Você precisa do host DB do Supabase: `db.gtctfqphvsczeenpysco.supabase.co`
- O usuário padrão Supabase costuma ser `postgres`
- Use a senha do banco disponível em `Settings > Database` no dashboard Supabase

## 11) Dica rápida: usar SQL Lab no Superset

Se quiser métricas mais avançadas (giro de estoque, produtos mais pedidos), crie uma query SQL em `SQL Lab` e salve-a como dataset:

```sql
SELECT
  p.nome AS produto,
  SUM(ip.quantidade) AS total_vendido,
  COUNT(*) AS pedidos,
  AVG(p.quantidade) AS estoque_atual
FROM itens_pedido ip
JOIN produtos p ON p.id = ip.produto_id
GROUP BY p.nome
ORDER BY total_vendido DESC
LIMIT 20;
```

Depois use esse dataset para criar gráficos e dashboards.

---

Se quiser, posso criar também um script `superset-start.bat` ou `superset.env` com variáveis de conexão para facilitar a execução no Windows.