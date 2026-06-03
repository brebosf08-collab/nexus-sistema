-- Ajuste para o sistema aceitar kg, gramas convertidas e porcentagens com decimal.
-- Rode no Supabase SQL Editor uma vez.

ALTER TABLE IF EXISTS materias_primas
  ALTER COLUMN quantidade TYPE NUMERIC(12,3) USING quantidade::numeric,
  ALTER COLUMN minimo TYPE NUMERIC(12,3) USING minimo::numeric,
  ALTER COLUMN custo_unitario TYPE NUMERIC(12,2) USING custo_unitario::numeric;

ALTER TABLE IF EXISTS produto_materias_primas
  ALTER COLUMN quantidade_por_produto TYPE NUMERIC(12,3) USING quantidade_por_produto::numeric,
  ALTER COLUMN percentual TYPE NUMERIC(8,3) USING percentual::numeric;

ALTER TABLE IF EXISTS historico_materias_primas
  ALTER COLUMN quantidade TYPE NUMERIC(12,3) USING quantidade::numeric;
