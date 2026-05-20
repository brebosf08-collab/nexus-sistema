CREATE TABLE IF NOT EXISTS materias_primas (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    nome TEXT NOT NULL,
    sku TEXT,
    unidade TEXT NOT NULL DEFAULT 'un',
    quantidade INTEGER NOT NULL DEFAULT 0,
    minimo INTEGER NOT NULL DEFAULT 0,
    custo_unitario NUMERIC(12,2) NOT NULL DEFAULT 0,
    descricao TEXT,
    criado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_materias_primas_empresa
    ON materias_primas (empresa_id);

CREATE TABLE IF NOT EXISTS produto_materias_primas (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    produto_id BIGINT NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
    materia_prima_id BIGINT NOT NULL REFERENCES materias_primas(id) ON DELETE CASCADE,
    quantidade_por_produto NUMERIC(12,3) NOT NULL DEFAULT 0,
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (empresa_id, produto_id, materia_prima_id)
);

CREATE INDEX IF NOT EXISTS idx_produto_materias_empresa
    ON produto_materias_primas (empresa_id);

CREATE INDEX IF NOT EXISTS idx_produto_materias_produto
    ON produto_materias_primas (produto_id);

CREATE INDEX IF NOT EXISTS idx_produto_materias_materia
    ON produto_materias_primas (materia_prima_id);

ALTER TABLE materias_primas ENABLE ROW LEVEL SECURITY;
ALTER TABLE produto_materias_primas ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS materias_primas_all ON materias_primas;
CREATE POLICY materias_primas_all
    ON materias_primas
    FOR ALL
    USING (true)
    WITH CHECK (true);

DROP POLICY IF EXISTS produto_materias_primas_all ON produto_materias_primas;
CREATE POLICY produto_materias_primas_all
    ON produto_materias_primas
    FOR ALL
    USING (true)
    WITH CHECK (true);
