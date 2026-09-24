-- ============================================================
-- NEXUS v2 - Schema limpo do zero
-- Rode este arquivo inteiro no SQL Editor do Supabase (novo projeto)
-- ============================================================

create extension if not exists "pgcrypto";

-- Empresas (fornecedores) que usam o sistema
create table empresas (
    id uuid primary key default gen_random_uuid(),
    nome text not null,
    email text not null unique,
    senha_hash text not null,
    criado_em timestamptz not null default now()
);

-- Categorias de produto (opcional, pra organizar)
create table categorias (
    id uuid primary key default gen_random_uuid(),
    empresa_id uuid not null references empresas(id) on delete cascade,
    nome text not null,
    criado_em timestamptz not null default now()
);

-- Matérias-primas (farinha, açúcar, recheio, etc) - estoque PRÓPRIO, separado de produto
create table materias_primas (
    id uuid primary key default gen_random_uuid(),
    empresa_id uuid not null references empresas(id) on delete cascade,
    nome text not null,
    unidade text not null default 'un',          -- kg, l, un, g, ml...
    estoque_atual numeric not null default 0,
    estoque_minimo numeric not null default 0,
    custo_unitario numeric not null default 0,
    criado_em timestamptz not null default now()
);

-- Produtos prontos (biscoito, bolo, etc) - estoque PRÓPRIO, separado de matéria-prima
create table produtos (
    id uuid primary key default gen_random_uuid(),
    empresa_id uuid not null references empresas(id) on delete cascade,
    categoria_id uuid references categorias(id) on delete set null,
    nome text not null,
    preco numeric not null default 0,
    unidade text not null default 'un',
    estoque_atual numeric not null default 0,
    estoque_minimo numeric not null default 0,
    ativo boolean not null default true,
    criado_em timestamptz not null default now()
);

-- Composição: quais matérias-primas (e quanto de cada) um produto usa
-- Isso permite: biscoito usa farinha + açúcar + recheio, cada um com sua quantidade
create table produto_materias_primas (
    id uuid primary key default gen_random_uuid(),
    produto_id uuid not null references produtos(id) on delete cascade,
    materia_prima_id uuid not null references materias_primas(id) on delete cascade,
    quantidade_necessaria numeric not null,   -- quanto dessa matéria-prima p/ produzir 1 unidade do produto
    unique(produto_id, materia_prima_id)
);

-- Histórico/auditoria unificado de TODAS as movimentações de estoque
-- (entrada, saída, produção, ajuste manual) - de produto OU de matéria-prima
create table movimentos_estoque (
    id uuid primary key default gen_random_uuid(),
    empresa_id uuid not null references empresas(id) on delete cascade,
    tipo_item text not null check (tipo_item in ('produto', 'materia_prima')),
    item_id uuid not null,
    item_nome text not null,               -- guardado aqui pra o histórico não sumir se o item for excluído
    tipo_movimento text not null check (tipo_movimento in ('entrada', 'saida', 'producao_consumo', 'producao_gerado', 'ajuste', 'pedido')),
    quantidade numeric not null,
    estoque_resultante numeric not null,
    motivo text not null default '',
    criado_em timestamptz not null default now()
);

-- Pedidos (vendas de produtos prontos)
create table pedidos (
    id uuid primary key default gen_random_uuid(),
    empresa_id uuid not null references empresas(id) on delete cascade,
    cliente_nome text not null default 'Cliente balcão',
    status text not null default 'confirmado',
    total numeric not null default 0,
    criado_em timestamptz not null default now()
);

create table pedido_itens (
    id uuid primary key default gen_random_uuid(),
    pedido_id uuid not null references pedidos(id) on delete cascade,
    produto_id uuid not null references produtos(id),
    produto_nome text not null,
    quantidade numeric not null,
    preco_unitario numeric not null,
    subtotal numeric not null
);

-- Avisos / notificações (painel do fornecedor lê SÓ esta tabela - sistema único, sem duplicidade)
create table avisos (
    id uuid primary key default gen_random_uuid(),
    empresa_id uuid not null references empresas(id) on delete cascade,
    tipo text not null default 'info',
    titulo text not null,
    mensagem text not null default '',
    prioridade text not null default 'normal',
    lido boolean not null default false,
    criado_em timestamptz not null default now()
);

-- Índices para as consultas mais comuns
create index idx_produtos_empresa on produtos(empresa_id);
create index idx_materias_empresa on materias_primas(empresa_id);
create index idx_composicao_produto on produto_materias_primas(produto_id);
create index idx_movimentos_empresa on movimentos_estoque(empresa_id, criado_em desc);
create index idx_pedidos_empresa on pedidos(empresa_id, criado_em desc);
create index idx_avisos_empresa on avisos(empresa_id, criado_em desc);

-- NOTA SOBRE SEGURANÇA:
-- Este app usa a chave "service_role" do Supabase, guardada só no servidor (nunca no navegador),
-- e faz o controle de acesso (login, isolar dados por empresa) inteiramente dentro do Flask.
-- Por isso NÃO habilitamos Row Level Security aqui: a chave service_role já ignora RLS,
-- e não existe nenhuma chave pública/anon exposta no navegador neste sistema.
