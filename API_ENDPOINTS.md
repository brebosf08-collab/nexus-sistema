# 📚 Referência Rápida de Endpoints - API v2

## 🏭 Produtos e Inventário

### Criar Produto com Validação
```http
POST /api/v2/produtos
Content-Type: application/json

{
  "nome": "Produto XYZ",
  "sku": "PROD-001",
  "categoria_id": 1,
  "custo": 100.00,
  "preco": 250.00,
  "quantidade": 50,
  "minimo": 10,
  "descricao": "Descrição do produto",
  "imagem_url": "url-da-imagem",
  "codigo_barras": "1234567890"
}

Response:
{
  "sucesso": true,
  "produto_id": 123,
  "produto": {...},
  "mensagem": "Produto criado com sucesso"
}
```

### Atualizar Estoque
```http
PUT /api/v2/estoque/123
Content-Type: application/json

{
  "quantidade": 75,
  "motivo": "Compra de fornecedor"
}

Response:
{
  "sucesso": true,
  "diferenca": 25,
  "novo_estoque": 75
}
```

### Ver Histórico de Movimentos
```http
GET /api/v2/movimentos/123?limite=20

Response:
[
  {
    "id": 456,
    "produto_id": 123,
    "tipo": "entrada",
    "quantidade": 25,
    "motivo": "Compra",
    "data": "2026-05-18T10:30:00"
  },
  ...
]
```

### Obter Estatísticas de Inventário
```http
GET /api/v2/inventario/estadisticas

Response:
{
  "total_produtos": 50,
  "valor_total_custo": 50000.00,
  "valor_total_venda": 125000.00,
  "valor_lucro_potencial": 75000.00,
  "quantidade_total": 1250,
  "alertas_abertos": 3,
  "rotatividade": "Alta"
}
```

### Alertas de Estoque
```http
GET /api/v2/alertas-estoque?status=aberto

Response:
[
  {
    "id": 789,
    "produto_id": 123,
    "nome_produto": "Produto XYZ",
    "estoque_atual": 5,
    "estoque_minimo": 10,
    "status": "aberto"
  }
]
```

---

## 📅 Agendamentos

### Criar Agendamento
```http
POST /api/agendamentos
Content-Type: application/json

{
  "titulo": "Visita ao Cliente",
  "tipo": "visita",
  "descricao": "Reunião de revisão de pedidos",
  "data": "2026-05-25",
  "hora": "14:30",
  "local": "Rua Principal, 100",
  "contato": "João da Silva",
  "telefone": "(11) 98765-4321",
  "email": "joao@email.com"
}

Response:
{
  "sucesso": true,
  "agendamento_id": 999,
  "mensagem": "Agendamento criado com sucesso"
}
```

### Listar Agendamentos com Filtros
```http
GET /api/agendamentos?data=semana&status=pendente

Query Params:
- data: hoje, semana, mes, atrasado (opcional)
- status: pendente, confirmado, concluído, cancelado (opcional)

Response:
[
  {
    "id": 999,
    "titulo": "Visita ao Cliente",
    "data": "2026-05-25",
    "hora": "14:30",
    "status": "pendente",
    "contato": "João",
    ...
  }
]
```

### Marcar Agendamento como Concluído
```http
PUT /api/agendamentos/999/concluir
Content-Type: application/json

{
  "observacoes": "Reunião realizada com sucesso"
}

Response:
{
  "sucesso": true,
  "agendamento": {...}
}
```

### Cancelar Agendamento
```http
PUT /api/agendamentos/999/cancelar
Content-Type: application/json

{
  "motivo": "Cliente pediu reagendamento"
}

Response:
{
  "sucesso": true,
  "agendamento": {...}
}
```

### Próximos Agendamentos
```http
GET /api/agendamentos/proximos?dias=7

Response: [lista de agendamentos dos próximos 7 dias]
```

### Agendamentos Atrasados
```http
GET /api/agendamentos/atrasados

Response: [lista de agendamentos pendentes vencidos]
```

---

## 🔔 Notificações

### Listar Notificações
```http
GET /api/notificacoes?nao_lidas=1&limite=20

Query Params:
- nao_lidas: 0 ou 1 (opcional)
- limite: número (default 50)

Response:
[
  {
    "id": 111,
    "titulo": "Alerta de Estoque",
    "mensagem": "Produto XYZ estoque baixo",
    "tipo": "aviso",
    "lida": false,
    "data_criacao": "2026-05-18T10:00:00"
  }
]
```

### Contar Não Lidas
```http
GET /api/notificacoes/nao-lidas

Response:
{
  "total": 5
}
```

### Marcar como Lida
```http
PUT /api/notificacoes/111/lida

Response:
{
  "sucesso": true
}
```

### Deletar Notificação
```http
DELETE /api/notificacoes/111

Response:
{
  "sucesso": true
}
```

### Obter Preferências
```http
GET /api/notificacoes/preferencias

Response:
{
  "email_estoque_baixo": true,
  "email_novo_pedido": true,
  "sms_urgente": false,
  "notificar_atrasados": true,
  "horario_silencio": "22:00"
}
```

### Salvar Preferências
```http
PUT /api/notificacoes/preferencias
Content-Type: application/json

{
  "email_estoque_baixo": true,
  "email_novo_pedido": true,
  "sms_urgente": false,
  "notificar_atrasados": true,
  "horario_silencio": "22:00"
}

Response:
{
  "sucesso": true
}
```

---

## 📊 Exportações

### Exportar Produtos
```http
GET /api/exportar/produtos?formato=xlsx

Query Params:
- formato: xlsx, csv, pdf (default xlsx)

Response: Download do arquivo
```

### Exportar Pedidos
```http
GET /api/exportar/pedidos?data_inicio=2026-05-01&data_fim=2026-05-31

Query Params:
- data_inicio: YYYY-MM-DD
- data_fim: YYYY-MM-DD

Response: Download do arquivo Excel
```

### Exportar Relatório de Inventário
```http
GET /api/exportar/relatorio-inventario

Response: Download com múltiplas abas
- Resumo geral
- Produtos detalhados
- Alertas de estoque
```

---

## 📈 Dashboard

### Obter Dados Consolidados
```http
GET /api/dashboard

Response:
{
  "inventario": {
    "total_produtos": 50,
    "valor_total_custo": 50000.00,
    "quantidade_total": 1250,
    "alertas_abertos": 3
  },
  "alertas_estoque": [...],
  "agendamentos_proximos": [...],
  "agendamentos_atrasados": [...],
  "notificacoes_nao_lidas": 5
}
```

---

## 🔐 Autenticação

Todos os endpoints (exceto públicos) requerem sessão de login:
```python
# Cookie de sessão automático após login
POST /api/login
```

---

## ❌ Tratamento de Erros

Todos os endpoints retornam:
```json
{
  "sucesso": false,
  "erro": "Descrição do erro",
  "mensagem": "Mensagem alternativa"
}
```

Status HTTP:
- `200`: Sucesso (GET)
- `201`: Criado (POST)
- `400`: Erro na requisição
- `401`: Não autenticado
- `403`: Sem permissão
- `503`: Serviço indisponível

---

## 📝 Exemplos em JavaScript

### Criar Agendamento
```javascript
const dados = {
  titulo: "Reunião Importante",
  tipo: "reuniao",
  data: "2026-05-25",
  hora: "10:00",
  local: "Sala de Reunião 1"
};

fetch('/api/agendamentos', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify(dados)
})
.then(r => r.json())
.then(resultado => {
  if (resultado.sucesso) {
    console.log('✓ Agendamento criado:', resultado.agendamento_id);
  } else {
    console.error('Erro:', resultado.erro);
  }
});
```

### Atualizar Estoque
```javascript
fetch('/api/v2/estoque/123', {
  method: 'PUT',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    quantidade: 100,
    motivo: 'Recebimento de pedido'
  })
})
.then(r => r.json())
.then(resultado => console.log(resultado));
```

### Exportar Relatório
```javascript
// Download direto do navegador
window.location.href = '/api/exportar/relatorio-inventario';
```

---

**Última atualização:** Maio 2026
