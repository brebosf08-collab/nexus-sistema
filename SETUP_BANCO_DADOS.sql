-- ═══════════════════════════════════════════════════════════════
-- TABELAS PARA SISTEMA DE NOTIFICAÇÕES E COMPARTILHAMENTO
-- Execute estes comandos SQL no Supabase SQL Editor
-- ═══════════════════════════════════════════════════════════════

-- Tabela de Notificações Direcionadas
CREATE TABLE IF NOT EXISTS notificacoes (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    cliente_id BIGINT REFERENCES empresas(id) ON DELETE CASCADE,
    fornecedor_id BIGINT REFERENCES empresas(id) ON DELETE CASCADE,
    tipo VARCHAR(50) NOT NULL,  -- 'novo_produto', 'promocao', 'convite', 'pedido_atualizado', 'info'
    titulo VARCHAR(255) NOT NULL,
    mensagem TEXT,
    lida BOOLEAN DEFAULT FALSE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notificacoes_cliente ON notificacoes(cliente_id);
CREATE INDEX idx_notificacoes_lida ON notificacoes(cliente_id, lida);

-- Tabela de Vitrines Compartilhadas
CREATE TABLE IF NOT EXISTS vitrines_compartilhadas (
    id BIGSERIAL PRIMARY KEY,
    fornecedor_id BIGINT NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    cliente_id BIGINT NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    metodo VARCHAR(20) NOT NULL,  -- 'convite' ou 'link'
    aceito BOOLEAN DEFAULT FALSE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(fornecedor_id, cliente_id)
);

CREATE INDEX idx_vitrines_cliente ON vitrines_compartilhadas(cliente_id);
CREATE INDEX idx_vitrines_fornecedor ON vitrines_compartilhadas(fornecedor_id);

-- Tabela de Visitantes da Vitrine
CREATE TABLE IF NOT EXISTS visitantes_vitrine (
    id BIGSERIAL PRIMARY KEY,
    fornecedor_id BIGINT NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    cliente_id BIGINT REFERENCES empresas(id) ON DELETE SET NULL,
    visitado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_visitantes_fornecedor ON visitantes_vitrine(fornecedor_id);
CREATE INDEX idx_visitantes_cliente ON visitantes_vitrine(cliente_id);

-- ═══════════════════════════════════════════════════════════════
-- Permissões RLS (Row Level Security) - OPCIONAL
-- Se você estiver usando RLS, descomentar abaixo:
-- ═══════════════════════════════════════════════════════════════

-- ALTER TABLE notificacoes ENABLE ROW LEVEL SECURITY;
--
-- CREATE POLICY "Usuarios podem ver suas proprias notificacoes" ON notificacoes
-- FOR SELECT USING (cliente_id = (SELECT empresa_id FROM usuarios WHERE id = auth.uid()));
--
-- ALTER TABLE vitrines_compartilhadas ENABLE ROW LEVEL SECURITY;
--
-- CREATE POLICY "Clientes podem ver compartilhamentos com eles" ON vitrines_compartilhadas
-- FOR SELECT USING (cliente_id = (SELECT empresa_id FROM usuarios WHERE id = auth.uid()));
--
-- ALTER TABLE visitantes_vitrine ENABLE ROW LEVEL SECURITY;
--
-- CREATE POLICY "Fornecedores podem ver visitantes de sua vitrine" ON visitantes_vitrine
-- FOR SELECT USING (fornecedor_id = (SELECT empresa_id FROM usuarios WHERE id = auth.uid()));
