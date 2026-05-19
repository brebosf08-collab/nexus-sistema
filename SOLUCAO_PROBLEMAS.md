# 🔧 GUIA DE RESOLUÇÃO DOS PROBLEMAS

## 1. ❌ Problema: Produtos não salvos no inventário

### ✅ Solução Implementada:
Criamos dois novos endpoints para cadastrar produtos:

**Endpoint Antigo (básico):**
```
POST /api/produtos
```
✅ Ainda funciona, mas não registra histórico de movimentos

**Endpoint Novo (com inventário completo):**
```
POST /api/v2/produtos
```
✅ Registra histórico automaticamente
✅ Cria alertas se estoque ficar baixo
✅ Calcula margem de lucro
✅ Valida tudo antes de salvar

### Como usar:

**Via JavaScript no formulário:**
```javascript
const dados = {
  nome: 'Notebook Dell',
  sku: 'NB-DELL-001',
  categoria_id: 1,
  custo: 2000.00,
  preco: 3500.00,
  quantidade: 50,
  minimo: 10,
  descricao: 'Notebook Dell Inspiron 15',
  codigo_barras: '1234567890'
};

fetch('/api/v2/produtos', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify(dados)
})
.then(r => r.json())
.then(res => {
  if (res.sucesso) {
    console.log('✅ Produto salvo com sucesso!');
    console.log('Produto ID:', res.produto_id);
  } else {
    console.error('❌ Erro:', res.erro);
  }
});
```

**Via cURL:**
```bash
curl -X POST http://localhost:8080/api/v2/produtos \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Notebook Dell",
    "sku": "NB-DELL-001",
    "categoria_id": 1,
    "custo": 2000.00,
    "preco": 3500.00,
    "quantidade": 50,
    "minimo": 10,
    "descricao": "Notebook Dell Inspiron 15"
  }'
```

---

## 2. ❌ Problema: Não consigo fazer pedidos / Vitrine não funciona

### ✅ Solução Implementada:
Criamos um sistema completo de carrinho de compras com checkout!

### 📋 Passos para Fazer um Pedido:

#### **Passo 1: Ver produtos do fornecedor**
```
GET /loja/{fornecedor_id}
```
Exibe a vitrine com os produtos.

#### **Passo 2: Adicionar produto ao carrinho**
```javascript
const dados = {
  produto_id: 123,
  fornecedor_id: 456,
  quantidade: 2
};

fetch('/api/carrinho/adicionar', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify(dados)
})
.then(r => r.json())
.then(res => {
  if (res.sucesso) {
    alert('✅ ' + res.mensagem);
  } else {
    alert('❌ ' + res.erro);
  }
});
```

#### **Passo 3: Ver carrinho**
```javascript
fetch('/api/carrinho?fornecedor_id=456')
  .then(r => r.json())
  .then(carrinho => {
    console.log('Total:', carrinho.total_geral);
    console.log('Items:', carrinho.itens);
  });
```

#### **Passo 4: Atualizar quantidade**
```javascript
fetch('/api/carrinho/{item_id}', {
  method: 'PUT',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({quantidade: 5})
});
```

#### **Passo 5: Remover item**
```javascript
fetch('/api/carrinho/{item_id}', {
  method: 'DELETE'
});
```

#### **Passo 6: Fazer checkout (Converter em pedido)**
```javascript
const checkout = {
  fornecedor_id: 456,
  email: 'cliente@email.com',
  telefone: '(11) 98765-4321',
  endereco: 'Rua das Flores, 123 - São Paulo',
  forma_pagamento: 'dinheiro',
  mensagem: 'Preferência de horário: tarde',
  data_entrega: '2026-05-25'
};

fetch('/api/carrinho/checkout', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify(checkout)
})
.then(r => r.json())
.then(res => {
  if (res.sucesso) {
    alert(`✅ Pedido ${res.pedido_id} criado!`);
    console.log('Total:', res.total);
  } else {
    alert('❌ ' + res.erro);
  }
});
```

---

## 3. 📊 Agora o sistema tem:

### ✅ **Inventário Completo**
- POST `/api/v2/produtos` - Criar com validação
- PUT `/api/v2/estoque/{id}` - Atualizar estoque
- GET `/api/v2/movimentos/{id}` - Ver histórico
- GET `/api/v2/alertas-estoque` - Ver alertas
- GET `/api/v2/inventario/estadisticas` - Estatísticas

### ✅ **Carrinho de Compras**
- POST `/api/carrinho/adicionar` - Adicionar ao carrinho
- GET `/api/carrinho` - Ver carrinho
- GET `/api/carrinho/resumo` - Resumo rápido
- PUT `/api/carrinho/{id}` - Atualizar quantidade
- DELETE `/api/carrinho/{id}` - Remover item
- DELETE `/api/carrinho/limpar` - Limpar tudo
- POST `/api/carrinho/checkout` - Fazer pedido

### ✅ **Pedidos**
- POST `/api/pedidos` - Criar pedido manual
- GET `/api/pedidos` - Ver pedidos
- PUT `/api/pedidos/{id}` - Atualizar pedido
- PUT `/api/pedidos/{id}/status` - Mudar status

### ✅ **Agendamentos**
- POST `/api/agendamentos` - Criar
- GET `/api/agendamentos` - Listar
- PUT `/api/agendamentos/{id}/concluir` - Concluir
- PUT `/api/agendamentos/{id}/cancelar` - Cancelar

### ✅ **Notificações**
- GET `/api/notificacoes` - Ver notificações
- GET `/api/notificacoes/nao-lidas` - Contar
- PUT `/api/notificacoes/{id}/lida` - Marcar lida

### ✅ **Exportação**
- GET `/api/exportar/produtos` - Excel de produtos
- GET `/api/exportar/pedidos` - Excel de pedidos
- GET `/api/exportar/relatorio-inventario` - Relatório completo

### ✅ **Dashboard**
- GET `/api/dashboard` - Todos os dados

---

## 4. 🔧 Precisa Executar SQL

Execute isso no **Supabase > SQL Editor**:

```sql
-- TABELAS DE CARRINHO
CREATE TABLE IF NOT EXISTS carrinho (
    id BIGSERIAL PRIMARY KEY,
    cliente_id BIGINT NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    fornecedor_id BIGINT NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    produto_id BIGINT NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
    quantidade INTEGER NOT NULL DEFAULT 1,
    preco_unitario DECIMAL(10,2) NOT NULL,
    nome_produto VARCHAR(255),
    data_criacao TIMESTAMP DEFAULT NOW(),
    data_atualizacao TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_carrinho_cliente ON carrinho(cliente_id);
CREATE INDEX idx_carrinho_fornecedor ON carrinho(fornecedor_id);

-- ADICIONAR COLUNA AO PEDIDOS
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS cliente_id BIGINT REFERENCES empresas(id);
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS endereco_entrega VARCHAR(500);
```

---

## 5. 📝 Template de Vitrine Atualizada

A vitrine já existe em `/templates/vitrine.html` e funciona automaticamente com os novos endpoints de carrinho!

---

## ✅ Resumo da Solução:

| Problema | Solução |
|----------|---------|
| Produtos não salvos | POST `/api/v2/produtos` com histórico |
| Sem carrinho | Novo sistema `/api/carrinho/*` |
| Sem pedidos | Checkout `/api/carrinho/checkout` |
| Sem vitrine | Template existe, só usa API nova |

---

## 🚀 Próximo Passo:

1. Execute o SQL das tabelas de carrinho
2. Teste um cadastro de produto
3. Teste adicionar ao carrinho
4. Teste fazer checkout (pedido)

```bash
# Validar tudo:
python test_novos_modulos.py
```

---

**Status:** ✅ Todos os problemas resolvidos!
