-- ================================================
-- NEXUS — Setup Completo do Banco de Dados
-- Execute no SQL Editor do Supabase
-- ================================================

-- ================================================
-- 1. CRIAR TABELAS (caso não existam)
-- ================================================

CREATE TABLE IF NOT EXISTS empresas (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    documento VARCHAR(30),
    tipo_documento VARCHAR(10) DEFAULT 'cnpj',
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('fornecedor', 'cliente')),
    email VARCHAR(255),
    telefone VARCHAR(30),
    endereco TEXT,
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    auth_id UUID,
    empresa_id INTEGER REFERENCES empresas(id) ON DELETE CASCADE,
    nome VARCHAR(255) NOT NULL,
    login VARCHAR(255) UNIQUE NOT NULL,
    cargo VARCHAR(100) DEFAULT 'admin',
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS categorias (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER REFERENCES empresas(id) ON DELETE CASCADE,
    nome VARCHAR(255) NOT NULL,
    criado_em TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS produtos (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER REFERENCES empresas(id) ON DELETE CASCADE,
    categoria_id INTEGER REFERENCES categorias(id) ON DELETE SET NULL,
    nome VARCHAR(255) NOT NULL,
    sku VARCHAR(100),
    descricao TEXT,
    custo NUMERIC(12,2) DEFAULT 0,
    preco NUMERIC(12,2) DEFAULT 0,
    quantidade INTEGER DEFAULT 0,
    minimo INTEGER DEFAULT 0,
    imagem VARCHAR(500),
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT NOW()
);

ALTER TABLE produtos ADD COLUMN IF NOT EXISTS ativo BOOLEAN DEFAULT TRUE;

-- Tabela de histórico de movimentações de estoque
-- (chamada 'historico' no sistema, NÃO 'estoque_movimentos')
CREATE TABLE IF NOT EXISTS historico (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER REFERENCES empresas(id) ON DELETE CASCADE,
    produto_id INTEGER REFERENCES produtos(id) ON DELETE CASCADE,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('entrada', 'saida')),
    quantidade INTEGER NOT NULL,
    observacoes TEXT,
    data_hora TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS vendedores (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER REFERENCES empresas(id) ON DELETE CASCADE,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    telefone VARCHAR(30),
    comissao NUMERIC(5,2) DEFAULT 0,
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pedidos (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER REFERENCES empresas(id) ON DELETE CASCADE,
    cliente_id INTEGER REFERENCES empresas(id) ON DELETE SET NULL,
    vendedor_id INTEGER REFERENCES vendedores(id) ON DELETE SET NULL,
    cliente_nome VARCHAR(255),
    data DATE NOT NULL,
    data_entrega DATE,
    forma_pagamento VARCHAR(100),
    total NUMERIC(12,2) DEFAULT 0,
    quantidade_itens INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pendente',
    observacoes TEXT,
    criado_em TIMESTAMP DEFAULT NOW()
);

ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS data_entrega DATE;
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS forma_pagamento VARCHAR(100);
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS mensagem_cliente TEXT;
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS comissao_valor NUMERIC(12,2) DEFAULT 0;

CREATE TABLE IF NOT EXISTS itens_pedido (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER REFERENCES pedidos(id) ON DELETE CASCADE,
    produto_id INTEGER REFERENCES produtos(id) ON DELETE SET NULL,
    quantidade INTEGER NOT NULL,
    preco_unitario NUMERIC(12,2) NOT NULL,
    subtotal NUMERIC(12,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS carrinho (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    fornecedor_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    produto_id INTEGER NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
    quantidade INTEGER NOT NULL DEFAULT 1,
    preco_unitario NUMERIC(12,2) NOT NULL,
    nome_produto VARCHAR(255),
    data_criacao TIMESTAMP DEFAULT NOW(),
    data_atualizacao TIMESTAMP DEFAULT NOW(),
    criado_em TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS materias_primas (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER REFERENCES empresas(id) ON DELETE CASCADE,
    nome VARCHAR(255) NOT NULL,
    sku VARCHAR(100),
    unidade VARCHAR(30) DEFAULT 'un',
    quantidade NUMERIC(12,3) DEFAULT 0,
    minimo NUMERIC(12,3) DEFAULT 0,
    custo_unitario NUMERIC(12,2) DEFAULT 0,
    descricao TEXT,
    criado_em TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS produto_materias_primas (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER REFERENCES empresas(id) ON DELETE CASCADE,
    produto_id INTEGER REFERENCES produtos(id) ON DELETE CASCADE,
    materia_prima_id INTEGER REFERENCES materias_primas(id) ON DELETE CASCADE,
    quantidade_por_produto NUMERIC(12,3) NOT NULL DEFAULT 0,
    tipo_calculo VARCHAR(20) DEFAULT 'quantidade',
    percentual NUMERIC(8,3) DEFAULT 0,
    criado_em TIMESTAMP DEFAULT NOW(),
    UNIQUE(produto_id, materia_prima_id)
);

ALTER TABLE produto_materias_primas ADD COLUMN IF NOT EXISTS tipo_calculo VARCHAR(20) DEFAULT 'quantidade';
ALTER TABLE produto_materias_primas ADD COLUMN IF NOT EXISTS percentual NUMERIC(8,3) DEFAULT 0;

CREATE TABLE IF NOT EXISTS historico_materias_primas (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER REFERENCES empresas(id) ON DELETE CASCADE,
    materia_prima_id INTEGER REFERENCES materias_primas(id) ON DELETE CASCADE,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('entrada', 'saida')),
    quantidade NUMERIC(12,3) NOT NULL,
    observacoes TEXT,
    data_hora TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reunioes (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER REFERENCES empresas(id) ON DELETE CASCADE,
    titulo VARCHAR(255) NOT NULL,
    descricao TEXT,
    data_hora TIMESTAMP,
    local VARCHAR(255),
    participantes TEXT,
    status VARCHAR(50) DEFAULT 'agendada',
    criado_em TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS contatos (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER REFERENCES empresas(id) ON DELETE CASCADE,
    nome VARCHAR(255) NOT NULL,
    documento VARCHAR(30),
    email VARCHAR(255),
    telefone VARCHAR(30),
    endereco TEXT,
    tipo VARCHAR(50) DEFAULT 'cliente',
    criado_em TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS avisos (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER REFERENCES empresas(id) ON DELETE CASCADE,
    tipo VARCHAR(50) NOT NULL,
    titulo VARCHAR(255) NOT NULL,
    mensagem TEXT,
    prioridade VARCHAR(20) DEFAULT 'normal',
    lido BOOLEAN DEFAULT FALSE,
    data_agendada TIMESTAMP,
    data_criacao TIMESTAMP DEFAULT NOW(),
    data_leitura TIMESTAMP
);

CREATE TABLE IF NOT EXISTS perfil_loja (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER REFERENCES empresas(id) ON DELETE CASCADE UNIQUE,
    nome_loja VARCHAR(255),
    descricao TEXT,
    foto_loja VARCHAR(500),
    foto_banner VARCHAR(500),
    cor_principal VARCHAR(20) DEFAULT '#6366f1',
    cor_secundaria VARCHAR(20) DEFAULT '#1e1e2e',
    horario_funcionamento VARCHAR(100),
    formas_pagamento TEXT,
    link_whatsapp VARCHAR(50),
    link_instagram VARCHAR(255),
    link_facebook VARCHAR(255),
    ativo BOOLEAN DEFAULT TRUE,
    data_criacao TIMESTAMP DEFAULT NOW(),
    data_atualizacao TIMESTAMP DEFAULT NOW()
);

-- ================================================
-- 2. ÍNDICES PARA PERFORMANCE
-- ================================================

CREATE INDEX IF NOT EXISTS idx_produtos_empresa    ON produtos(empresa_id);
CREATE INDEX IF NOT EXISTS idx_historico_empresa   ON historico(empresa_id);
CREATE INDEX IF NOT EXISTS idx_historico_produto   ON historico(produto_id);
CREATE INDEX IF NOT EXISTS idx_pedidos_empresa     ON pedidos(empresa_id);
CREATE INDEX IF NOT EXISTS idx_pedidos_cliente     ON pedidos(cliente_id);
CREATE INDEX IF NOT EXISTS idx_pedidos_status      ON pedidos(status);
CREATE INDEX IF NOT EXISTS idx_itens_pedido        ON itens_pedido(pedido_id);
CREATE INDEX IF NOT EXISTS idx_carrinho_cliente    ON carrinho(cliente_id);
CREATE INDEX IF NOT EXISTS idx_carrinho_fornecedor ON carrinho(fornecedor_id);
CREATE INDEX IF NOT EXISTS idx_carrinho_produto    ON carrinho(produto_id);
CREATE INDEX IF NOT EXISTS idx_materias_empresa    ON materias_primas(empresa_id);
CREATE INDEX IF NOT EXISTS idx_produto_materias_produto ON produto_materias_primas(produto_id);
CREATE INDEX IF NOT EXISTS idx_produto_materias_materia ON produto_materias_primas(materia_prima_id);
CREATE INDEX IF NOT EXISTS idx_hist_materias_empresa ON historico_materias_primas(empresa_id);
CREATE INDEX IF NOT EXISTS idx_hist_materias_materia ON historico_materias_primas(materia_prima_id);
CREATE INDEX IF NOT EXISTS idx_categorias_empresa  ON categorias(empresa_id);
CREATE INDEX IF NOT EXISTS idx_vendedores_empresa  ON vendedores(empresa_id);
CREATE INDEX IF NOT EXISTS idx_reunioes_empresa    ON reunioes(empresa_id);
CREATE INDEX IF NOT EXISTS idx_contatos_empresa    ON contatos(empresa_id);
CREATE INDEX IF NOT EXISTS idx_avisos_empresa      ON avisos(empresa_id);
CREATE INDEX IF NOT EXISTS idx_avisos_lido         ON avisos(lido);
CREATE INDEX IF NOT EXISTS idx_perfil_loja_empresa ON perfil_loja(empresa_id);
CREATE INDEX IF NOT EXISTS idx_usuarios_login      ON usuarios(login);

-- ================================================
-- 3. POLÍTICAS DE SEGURANÇA (RLS)
-- ================================================

-- empresas
ALTER TABLE empresas ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "rls_empresas_select" ON empresas;
DROP POLICY IF EXISTS "rls_empresas_insert" ON empresas;
DROP POLICY IF EXISTS "rls_empresas_update" ON empresas;
CREATE POLICY "rls_empresas_select" ON empresas FOR SELECT USING (true);
CREATE POLICY "rls_empresas_insert" ON empresas FOR INSERT WITH CHECK (true);
CREATE POLICY "rls_empresas_update" ON empresas FOR UPDATE USING (true);

-- usuarios
ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "rls_usuarios_select" ON usuarios;
DROP POLICY IF EXISTS "rls_usuarios_insert" ON usuarios;
DROP POLICY IF EXISTS "rls_usuarios_update" ON usuarios;
CREATE POLICY "rls_usuarios_select" ON usuarios FOR SELECT USING (true);
CREATE POLICY "rls_usuarios_insert" ON usuarios FOR INSERT WITH CHECK (true);
CREATE POLICY "rls_usuarios_update" ON usuarios FOR UPDATE USING (true);

-- categorias
ALTER TABLE categorias ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "rls_categorias_select" ON categorias;
DROP POLICY IF EXISTS "rls_categorias_insert" ON categorias;
DROP POLICY IF EXISTS "rls_categorias_update" ON categorias;
DROP POLICY IF EXISTS "rls_categorias_delete" ON categorias;
CREATE POLICY "rls_categorias_select" ON categorias FOR SELECT USING (true);
CREATE POLICY "rls_categorias_insert" ON categorias FOR INSERT WITH CHECK (true);
CREATE POLICY "rls_categorias_update" ON categorias FOR UPDATE USING (true);
CREATE POLICY "rls_categorias_delete" ON categorias FOR DELETE USING (true);

-- produtos
ALTER TABLE produtos ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "rls_produtos_select" ON produtos;
DROP POLICY IF EXISTS "rls_produtos_insert" ON produtos;
DROP POLICY IF EXISTS "rls_produtos_update" ON produtos;
DROP POLICY IF EXISTS "rls_produtos_delete" ON produtos;
CREATE POLICY "rls_produtos_select" ON produtos FOR SELECT USING (true);
CREATE POLICY "rls_produtos_insert" ON produtos FOR INSERT WITH CHECK (true);
CREATE POLICY "rls_produtos_update" ON produtos FOR UPDATE USING (true);
CREATE POLICY "rls_produtos_delete" ON produtos FOR DELETE USING (true);

-- historico (movimentações de estoque)
ALTER TABLE historico ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "rls_historico_select" ON historico;
DROP POLICY IF EXISTS "rls_historico_insert" ON historico;
CREATE POLICY "rls_historico_select" ON historico FOR SELECT USING (true);
CREATE POLICY "rls_historico_insert" ON historico FOR INSERT WITH CHECK (true);

-- vendedores
ALTER TABLE vendedores ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "rls_vendedores_select" ON vendedores;
DROP POLICY IF EXISTS "rls_vendedores_insert" ON vendedores;
DROP POLICY IF EXISTS "rls_vendedores_update" ON vendedores;
DROP POLICY IF EXISTS "rls_vendedores_delete" ON vendedores;
CREATE POLICY "rls_vendedores_select" ON vendedores FOR SELECT USING (true);
CREATE POLICY "rls_vendedores_insert" ON vendedores FOR INSERT WITH CHECK (true);
CREATE POLICY "rls_vendedores_update" ON vendedores FOR UPDATE USING (true);
CREATE POLICY "rls_vendedores_delete" ON vendedores FOR DELETE USING (true);

-- pedidos
ALTER TABLE pedidos ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "rls_pedidos_select" ON pedidos;
DROP POLICY IF EXISTS "rls_pedidos_insert" ON pedidos;
DROP POLICY IF EXISTS "rls_pedidos_update" ON pedidos;
CREATE POLICY "rls_pedidos_select" ON pedidos FOR SELECT USING (true);
CREATE POLICY "rls_pedidos_insert" ON pedidos FOR INSERT WITH CHECK (true);
CREATE POLICY "rls_pedidos_update" ON pedidos FOR UPDATE USING (true);

-- itens_pedido
ALTER TABLE itens_pedido ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "rls_itens_pedido_select" ON itens_pedido;
DROP POLICY IF EXISTS "rls_itens_pedido_insert" ON itens_pedido;
CREATE POLICY "rls_itens_pedido_select" ON itens_pedido FOR SELECT USING (true);
CREATE POLICY "rls_itens_pedido_insert" ON itens_pedido FOR INSERT WITH CHECK (true);

-- carrinho
ALTER TABLE carrinho ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "rls_carrinho_select" ON carrinho;
DROP POLICY IF EXISTS "rls_carrinho_insert" ON carrinho;
DROP POLICY IF EXISTS "rls_carrinho_update" ON carrinho;
DROP POLICY IF EXISTS "rls_carrinho_delete" ON carrinho;
CREATE POLICY "rls_carrinho_select" ON carrinho FOR SELECT USING (true);
CREATE POLICY "rls_carrinho_insert" ON carrinho FOR INSERT WITH CHECK (true);
CREATE POLICY "rls_carrinho_update" ON carrinho FOR UPDATE USING (true);
CREATE POLICY "rls_carrinho_delete" ON carrinho FOR DELETE USING (true);

-- materias_primas
ALTER TABLE materias_primas ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "rls_materias_select" ON materias_primas;
DROP POLICY IF EXISTS "rls_materias_insert" ON materias_primas;
DROP POLICY IF EXISTS "rls_materias_update" ON materias_primas;
DROP POLICY IF EXISTS "rls_materias_delete" ON materias_primas;
CREATE POLICY "rls_materias_select" ON materias_primas FOR SELECT USING (true);
CREATE POLICY "rls_materias_insert" ON materias_primas FOR INSERT WITH CHECK (true);
CREATE POLICY "rls_materias_update" ON materias_primas FOR UPDATE USING (true);
CREATE POLICY "rls_materias_delete" ON materias_primas FOR DELETE USING (true);

-- produto_materias_primas
ALTER TABLE produto_materias_primas ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "rls_produto_materias_select" ON produto_materias_primas;
DROP POLICY IF EXISTS "rls_produto_materias_insert" ON produto_materias_primas;
DROP POLICY IF EXISTS "rls_produto_materias_update" ON produto_materias_primas;
DROP POLICY IF EXISTS "rls_produto_materias_delete" ON produto_materias_primas;
CREATE POLICY "rls_produto_materias_select" ON produto_materias_primas FOR SELECT USING (true);
CREATE POLICY "rls_produto_materias_insert" ON produto_materias_primas FOR INSERT WITH CHECK (true);
CREATE POLICY "rls_produto_materias_update" ON produto_materias_primas FOR UPDATE USING (true);
CREATE POLICY "rls_produto_materias_delete" ON produto_materias_primas FOR DELETE USING (true);

-- historico_materias_primas
ALTER TABLE historico_materias_primas ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "rls_hist_materias_select" ON historico_materias_primas;
DROP POLICY IF EXISTS "rls_hist_materias_insert" ON historico_materias_primas;
CREATE POLICY "rls_hist_materias_select" ON historico_materias_primas FOR SELECT USING (true);
CREATE POLICY "rls_hist_materias_insert" ON historico_materias_primas FOR INSERT WITH CHECK (true);

-- reunioes
ALTER TABLE reunioes ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "rls_reunioes_select" ON reunioes;
DROP POLICY IF EXISTS "rls_reunioes_insert" ON reunioes;
DROP POLICY IF EXISTS "rls_reunioes_update" ON reunioes;
DROP POLICY IF EXISTS "rls_reunioes_delete" ON reunioes;
CREATE POLICY "rls_reunioes_select" ON reunioes FOR SELECT USING (true);
CREATE POLICY "rls_reunioes_insert" ON reunioes FOR INSERT WITH CHECK (true);
CREATE POLICY "rls_reunioes_update" ON reunioes FOR UPDATE USING (true);
CREATE POLICY "rls_reunioes_delete" ON reunioes FOR DELETE USING (true);

-- contatos
ALTER TABLE contatos ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "rls_contatos_select" ON contatos;
DROP POLICY IF EXISTS "rls_contatos_insert" ON contatos;
DROP POLICY IF EXISTS "rls_contatos_update" ON contatos;
DROP POLICY IF EXISTS "rls_contatos_delete" ON contatos;
CREATE POLICY "rls_contatos_select" ON contatos FOR SELECT USING (true);
CREATE POLICY "rls_contatos_insert" ON contatos FOR INSERT WITH CHECK (true);
CREATE POLICY "rls_contatos_update" ON contatos FOR UPDATE USING (true);
CREATE POLICY "rls_contatos_delete" ON contatos FOR DELETE USING (true);

-- avisos
ALTER TABLE avisos ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "rls_avisos_select" ON avisos;
DROP POLICY IF EXISTS "rls_avisos_insert" ON avisos;
DROP POLICY IF EXISTS "rls_avisos_update" ON avisos;
DROP POLICY IF EXISTS "rls_avisos_delete" ON avisos;
CREATE POLICY "rls_avisos_select" ON avisos FOR SELECT USING (true);
CREATE POLICY "rls_avisos_insert" ON avisos FOR INSERT WITH CHECK (true);
CREATE POLICY "rls_avisos_update" ON avisos FOR UPDATE USING (true);
CREATE POLICY "rls_avisos_delete" ON avisos FOR DELETE USING (true);

-- perfil_loja
ALTER TABLE perfil_loja ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "rls_perfil_select" ON perfil_loja;
DROP POLICY IF EXISTS "rls_perfil_insert" ON perfil_loja;
DROP POLICY IF EXISTS "rls_perfil_update" ON perfil_loja;
CREATE POLICY "rls_perfil_select" ON perfil_loja FOR SELECT USING (true);
CREATE POLICY "rls_perfil_insert" ON perfil_loja FOR INSERT WITH CHECK (true);
CREATE POLICY "rls_perfil_update" ON perfil_loja FOR UPDATE USING (true);

-- ================================================
-- 4. VERIFICAÇÃO FINAL
-- ================================================

SELECT 
    table_name,
    CASE WHEN table_name IN (
        'empresas','usuarios','categorias','produtos','historico',
        'vendedores','pedidos','itens_pedido','carrinho',
        'materias_primas','produto_materias_primas','historico_materias_primas','reunioes',
        'contatos','avisos','perfil_loja'
    ) THEN '✅ OK' ELSE '⚠️ Extra' END AS status
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE'
ORDER BY table_name;
