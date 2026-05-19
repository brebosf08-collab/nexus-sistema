-- ═══════════════════════════════════════════════════════════════
-- SCHEMA PARA NOVAS FUNCIONALIDADES
-- Execute estas queries no SQL Editor do Supabase
-- ═══════════════════════════════════════════════════════════════

-- ═══════════════════════════════════════════
-- TABELA DE ALERTAS DE ESTOQUE
-- ═══════════════════════════════════════════
CREATE TABLE IF NOT EXISTS alertas_estoque (
    id BIGSERIAL PRIMARY KEY,
    produto_id BIGINT NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    nome_produto VARCHAR(255),
    estoque_atual INTEGER DEFAULT 0,
    estoque_minimo INTEGER DEFAULT 0,
    mensagem TEXT,
    status VARCHAR(50) DEFAULT 'aberto',  -- aberto, resolvido, ignorado
    data_criacao TIMESTAMP DEFAULT NOW(),
    data_resolucao TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_alertas_empresa ON alertas_estoque(empresa_id);
CREATE INDEX idx_alertas_status ON alertas_estoque(status);


-- ═══════════════════════════════════════════
-- TABELA DE MOVIMENTAÇÕES DE ESTOQUE
-- ═══════════════════════════════════════════
CREATE TABLE IF NOT EXISTS movimentacoes_estoque (
    id BIGSERIAL PRIMARY KEY,
    produto_id BIGINT NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
    tipo VARCHAR(20) NOT NULL,  -- entrada, saida, ajuste
    quantidade INTEGER NOT NULL,
    motivo VARCHAR(255),  -- compra, venda, devolução, perda, etc
    usuario_id BIGINT REFERENCES usuarios(id),
    observacoes TEXT,
    data TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_movimentacoes_produto ON movimentacoes_estoque(produto_id);
CREATE INDEX idx_movimentacoes_data ON movimentacoes_estoque(data);


-- ═══════════════════════════════════════════
-- TABELA DE AGENDAMENTOS
-- ═══════════════════════════════════════════
CREATE TABLE IF NOT EXISTS agendamentos (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    tipo VARCHAR(50),  -- entrega, reunião, visita, ligação, outro
    titulo VARCHAR(255) NOT NULL,
    descricao TEXT,
    data DATE NOT NULL,
    hora TIME DEFAULT '09:00',
    local VARCHAR(255),
    contato VARCHAR(255),
    telefone VARCHAR(20),
    email VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pendente',  -- pendente, confirmado, cancelado, concluído
    motivo_cancelamento TEXT,
    observacoes_conclusao TEXT,
    data_criacao TIMESTAMP DEFAULT NOW(),
    data_cancelamento TIMESTAMP,
    data_conclusao TIMESTAMP,
    lembrete_enviado BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_agendamentos_empresa ON agendamentos(empresa_id);
CREATE INDEX idx_agendamentos_data ON agendamentos(data);
CREATE INDEX idx_agendamentos_status ON agendamentos(status);


-- ═══════════════════════════════════════════
-- TABELA DE NOTIFICAÇÕES IN-APP
-- ═══════════════════════════════════════════
CREATE TABLE IF NOT EXISTS notificacoes (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    titulo VARCHAR(255) NOT NULL,
    mensagem TEXT,
    tipo VARCHAR(50) DEFAULT 'info',  -- info, sucesso, aviso, erro, urgente
    link TEXT,
    dados_extras JSONB,
    lida BOOLEAN DEFAULT FALSE,
    data_criacao TIMESTAMP DEFAULT NOW(),
    data_leitura TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_notificacoes_empresa ON notificacoes(empresa_id);
CREATE INDEX idx_notificacoes_lida ON notificacoes(lida);
CREATE INDEX idx_notificacoes_data ON notificacoes(data_criacao);


-- ═══════════════════════════════════════════
-- TABELA DE PREFERÊNCIAS DE NOTIFICAÇÃO
-- ═══════════════════════════════════════════
CREATE TABLE IF NOT EXISTS preferencias_notificacao (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL UNIQUE REFERENCES empresas(id) ON DELETE CASCADE,
    email_estoque_baixo BOOLEAN DEFAULT TRUE,
    email_novo_pedido BOOLEAN DEFAULT TRUE,
    sms_urgente BOOLEAN DEFAULT FALSE,
    notificar_atrasados BOOLEAN DEFAULT TRUE,
    horario_silencio TIME,
    data_atualizacao TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);


-- ═══════════════════════════════════════════
-- TABELA DE HISTÓRICO DE NOTIFICAÇÕES
-- ═══════════════════════════════════════════
CREATE TABLE IF NOT EXISTS historico_notificacoes (
    id BIGSERIAL PRIMARY KEY,
    tipo VARCHAR(50),  -- email, sms, push
    destinatario VARCHAR(255),
    status VARCHAR(50),  -- enviado, falha, pendente
    motivo TEXT,
    data_hora TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_historico_tipo ON historico_notificacoes(tipo);
CREATE INDEX idx_historico_status ON historico_notificacoes(status);


-- ═══════════════════════════════════════════
-- TABELA DE HISTÓRICO DE EXPORTAÇÕES
-- ═══════════════════════════════════════════
CREATE TABLE IF NOT EXISTS historico_exportacoes (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    tipo VARCHAR(50),  -- produtos, pedidos, relatorio, etc
    nome_arquivo VARCHAR(255),
    formato VARCHAR(20),  -- xlsx, pdf, csv
    quantidade_registros INTEGER,
    tamanho_bytes INTEGER,
    data_exportacao TIMESTAMP DEFAULT NOW(),
    usuario_id BIGINT REFERENCES usuarios(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_historico_exp_empresa ON historico_exportacoes(empresa_id);
CREATE INDEX idx_historico_exp_data ON historico_exportacoes(data_exportacao);


-- ═══════════════════════════════════════════
-- ATUALIZAR TABELA DE PRODUTOS (se necessário)
-- ═══════════════════════════════════════════
-- Adicione esta coluna se ainda não existir:
-- ALTER TABLE produtos ADD COLUMN IF NOT EXISTS margem_lucro DECIMAL(5,2);
-- ALTER TABLE produtos ADD COLUMN IF NOT EXISTS codigo_barras VARCHAR(50);
-- ALTER TABLE produtos ADD COLUMN IF NOT EXISTS ativo BOOLEAN DEFAULT TRUE;


-- ═══════════════════════════════════════════
-- RLS POLICIES - Segurança
-- ═══════════════════════════════════════════

-- Habilitar RLS para as novas tabelas
ALTER TABLE alertas_estoque ENABLE ROW LEVEL SECURITY;
ALTER TABLE movimentacoes_estoque ENABLE ROW LEVEL SECURITY;
ALTER TABLE agendamentos ENABLE ROW LEVEL SECURITY;
ALTER TABLE notificacoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE preferencias_notificacao ENABLE ROW LEVEL SECURITY;
ALTER TABLE historico_notificacoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE historico_exportacoes ENABLE ROW LEVEL SECURITY;

-- Policies para alertas_estoque
CREATE POLICY "Empresas podem ver seus próprios alertas" ON alertas_estoque
    FOR SELECT USING (empresa_id IN (SELECT id FROM empresas WHERE id = auth.uid()));

-- Policies para agendamentos
CREATE POLICY "Empresas podem gerenciar seus agendamentos" ON agendamentos
    FOR ALL USING (empresa_id IN (SELECT id FROM empresas WHERE id = auth.uid()));

-- Policies para notificacoes
CREATE POLICY "Empresas podem ver suas notificações" ON notificacoes
    FOR SELECT USING (empresa_id IN (SELECT id FROM empresas WHERE id = auth.uid()));

-- ═══════════════════════════════════════════
-- VIEWS ÚTEIS
-- ═══════════════════════════════════════════

-- View: Estoque em risco
CREATE OR REPLACE VIEW v_estoque_em_risco AS
SELECT 
    p.id,
    p.nome,
    p.quantidade,
    p.minimo,
    (p.minimo - p.quantidade) as quantidade_necessaria,
    e.nome as empresa_nome
FROM produtos p
JOIN empresas e ON p.empresa_id = e.id
WHERE p.quantidade <= p.minimo AND p.ativo = TRUE
ORDER BY p.quantidade ASC;

-- View: Agendamentos próximos
CREATE OR REPLACE VIEW v_agendamentos_proximos AS
SELECT 
    a.*,
    e.nome as empresa_nome
FROM agendamentos a
JOIN empresas e ON a.empresa_id = e.id
WHERE a.status IN ('pendente', 'confirmado')
    AND a.data <= CURRENT_DATE + INTERVAL '7 days'
ORDER BY a.data, a.hora;
