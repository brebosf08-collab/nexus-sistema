-- ═══════════════════════════════════════════════════════════════
-- TABELAS ADICIONAIS PARA CARRINHO E PEDIDOS
-- Execute no SQL Editor do Supabase
-- ═══════════════════════════════════════════════════════════════

-- ═══════════════════════════════════════════
-- TABELA DE CARRINHO
-- ═══════════════════════════════════════════
CREATE TABLE IF NOT EXISTS carrinho (
    id BIGSERIAL PRIMARY KEY,
    cliente_id BIGINT NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    fornecedor_id BIGINT NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    produto_id BIGINT NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
    quantidade INTEGER NOT NULL DEFAULT 1,
    preco_unitario DECIMAL(10,2) NOT NULL,
    nome_produto VARCHAR(255),
    data_criacao TIMESTAMP DEFAULT NOW(),
    data_atualizacao TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_carrinho_cliente ON carrinho(cliente_id);
CREATE INDEX idx_carrinho_fornecedor ON carrinho(fornecedor_id);
CREATE INDEX idx_carrinho_produto ON carrinho(produto_id);


-- ═══════════════════════════════════════════
-- ATUALIZAR TABELA DE PEDIDOS
-- ═══════════════════════════════════════════
-- Adicione estas colunas se não existirem:
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS cliente_id BIGINT REFERENCES empresas(id);
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS endereco_entrega VARCHAR(500);


-- ═══════════════════════════════════════════
-- VIEW PARA CARRINHO COM DETALHES
-- ═══════════════════════════════════════════
CREATE OR REPLACE VIEW v_carrinho_detalhado AS
SELECT 
    c.id,
    c.cliente_id,
    c.fornecedor_id,
    c.produto_id,
    c.quantidade,
    c.preco_unitario,
    c.nome_produto,
    (c.quantidade * c.preco_unitario) as subtotal,
    c.data_criacao,
    c.data_atualizacao,
    p.sku,
    p.imagem as imagem_produto,
    f.nome as fornecedor_nome,
    cli.nome as cliente_nome
FROM carrinho c
LEFT JOIN produtos p ON c.produto_id = p.id
LEFT JOIN empresas f ON c.fornecedor_id = f.id
LEFT JOIN empresas cli ON c.cliente_id = cli.id;
