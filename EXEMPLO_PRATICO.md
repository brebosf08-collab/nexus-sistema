# 🎓 EXEMPLO PRÁTICO - Fluxo Completo do Sistema

## 📖 Cenário Real: Loja de Eletrônicos

Você gerencia uma loja de eletrônicos e precisa:
1. Cadastrar um novo produto (Notebook)
2. Agendar entrega para um cliente
3. Receber alertas quando estoque ficar baixo
4. Exportar relatório de vendas

---

## ✏️ Passo a Passo

### **Passo 1: Cadastrar um Novo Produto**

#### Via cURL:
```bash
curl -X POST http://localhost:8080/api/v2/produtos \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Notebook Dell Inspiron 15",
    "sku": "NB-DELL-INS-15-2026",
    "categoria_id": 1,
    "custo": 2500.00,
    "preco": 4200.00,
    "quantidade": 25,
    "minimo": 5,
    "descricao": "Notebook Dell Inspiron 15 com processador i7",
    "codigo_barras": "784643000024",
    "imagem_url": "https://images.example.com/notebook.jpg"
  }'
```

#### Resposta:
```json
{
  "sucesso": true,
  "produto_id": 156,
  "produto": {
    "id": 156,
    "nome": "Notebook Dell Inspiron 15",
    "sku": "NB-DELL-INS-15-2026",
    "quantidade": 25,
    "minimo": 5,
    "margem_lucro": 40.48,
    "preco": 4200.00,
    "custo": 2500.00
  },
  "mensagem": "Produto criado com sucesso"
}
```

✅ **O que acontece automaticamente:**
- Produto criado no banco
- Movimento de estoque registrado
- Notificação in-app enviada para gerentes
- Email de confirmação enviado

---

### **Passo 2: Vender 5 Unidades (Atualizar Estoque)**

Uma venda é feita. Você precisa atualizar o estoque:

```bash
curl -X PUT http://localhost:8080/api/v2/estoque/156 \
  -H "Content-Type: application/json" \
  -d '{
    "quantidade": 20,
    "motivo": "Venda PedidoID#12345 - Cliente João da Silva"
  }'
```

#### Resposta:
```json
{
  "sucesso": true,
  "diferenca": -5,
  "novo_estoque": 20
}
```

✅ **O que acontece:**
- Estoque atualizado de 25 → 20
- Movimento registrado no histórico
- Notificação enviada
- Cálculo de margem de lucro: (4200 - 2500) / 4200 = 40.48%

---

### **Passo 3: Agendar Entrega**

Agora você precisa agendar a entrega para o cliente:

```bash
curl -X POST http://localhost:8080/api/agendamentos \
  -H "Content-Type: application/json" \
  -d '{
    "titulo": "Entrega Notebook Dell - PedidoID#12345",
    "tipo": "entrega",
    "descricao": "Entrega do Notebook pedido por João da Silva. Trazer fatura e manual.",
    "data": "2026-05-20",
    "hora": "14:00",
    "local": "Rua das Flores, 789 - Apartamento 42 - São Paulo, SP",
    "contato": "João da Silva",
    "telefone": "(11) 98765-4321",
    "email": "joao@email.com"
  }'
```

#### Resposta:
```json
{
  "sucesso": true,
  "agendamento_id": 789,
  "agendamento": {
    "id": 789,
    "titulo": "Entrega Notebook Dell - PedidoID#12345",
    "data": "2026-05-20",
    "hora": "14:00",
    "status": "pendente",
    "local": "Rua das Flores, 789...",
    "contato": "João da Silva"
  },
  "mensagem": "Agendamento criado com sucesso"
}
```

✅ **O que acontece:**
- Agendamento criado
- Notificação "📅 Agendamento Criado" enviada
- Email de confirmação para joao@email.com
- Alerta aparece no dashboard do time

---

### **Passo 4: Estoque Fica Baixo (Alerta Automático)**

Vende mais 16 unidades. Estoque vai para 4 (abaixo do mínimo de 5):

```bash
curl -X PUT http://localhost:8080/api/v2/estoque/156 \
  -H "Content-Type: application/json" \
  -d '{
    "quantidade": 4,
    "motivo": "Venda PedidoID#12346, PedidoID#12347, PedidoID#12348"
  }'
```

✅ **O que acontece AUTOMATICAMENTE:**
1. ⚠️ **Alerta criado** na tabela `alertas_estoque`
2. 🔔 **Notificação in-app** criada com tipo "aviso"
3. 📧 **Email enviado** com template de alerta:
   ```
   ⚠️ Alerta de Estoque Baixo
   
   Estoque Atual: 4 unidades
   Estoque Mínimo: 5 unidades
   Diferença: -1 unidade
   
   Por favor, reponha o estoque de "Notebook Dell Inspiron 15"
   ```
4. 📱 **SMS enviado** (se configurado):
   ```
   Estoque baixo! Notebook Dell: 4 un. (mín 5). Reponha logo!
   ```

---

### **Passo 5: Visualizar Alertas**

```bash
curl -X GET "http://localhost:8080/api/v2/alertas-estoque?status=aberto"
```

#### Resposta:
```json
[
  {
    "id": 42,
    "produto_id": 156,
    "empresa_id": 1,
    "nome_produto": "Notebook Dell Inspiron 15",
    "estoque_atual": 4,
    "estoque_minimo": 5,
    "mensagem": "Estoque baixo: Notebook Dell Inspiron 15 - Atual: 4, Mínimo: 5",
    "status": "aberto",
    "data_criacao": "2026-05-18T15:30:00"
  }
]
```

---

### **Passo 6: Agendar Entrega (Confirmar)**

Às 13:50 do dia 20, você confirma que vai sair:

```bash
curl -X PUT http://localhost:8080/api/agendamentos/789/concluir \
  -H "Content-Type: application/json" \
  -d '{
    "observacoes": "Entrega realizada com sucesso! Cliente recebeu em bom estado. Assinatura: João da Silva."
  }'
```

✅ **O que acontece:**
- Status muda de "pendente" → "concluído"
- Email de confirmação enviado para joao@email.com
- Notificação "✓ Agendamento Concluído" enviada
- Movimento fica no histórico

---

### **Passo 7: Exportar Relatório**

Seu gerente pede um relatório de vendas do mês:

```bash
curl -X GET "http://localhost:8080/api/exportar/relatorio-inventario" \
  -o "relatorio_inventario_maio_2026.xlsx"
```

📊 **Arquivo gerado com 3 abas:**

**Aba 1: Resumo**
```
Data do Relatório: 18/05/2026 15:30:00
Total de Produtos: 50
Quantidade Total em Estoque: 1250
Valor Total em Custo: R$ 125.000,00
Valor Total em Venda: R$ 312.500,00
Lucro Potencial: R$ 187.500,00
```

**Aba 2: Produtos Detalhados**
```
SKU | Nome | Qtd | Mínimo | Custo Unit | Preço Unit | Total Custo | Total Venda | Status
NB-DELL-INS-15-2026 | Notebook Dell Inspiron 15 | 4 | 5 | R$2.500 | R$4.200 | R$10.000 | R$16.800 | Crítico
...
```

**Aba 3: Alertas de Estoque**
```
Produto | Estoque Atual | Estoque Mínimo | Diferença | Prioridade
Notebook Dell Inspiron 15 | 4 | 5 | -1 | Crítica
...
```

---

### **Passo 8: Ver Dashboard**

Seu gerente acessa o dashboard com todos os dados consolidados:

```bash
curl -X GET http://localhost:8080/api/dashboard
```

#### Resposta:
```json
{
  "inventario": {
    "total_produtos": 50,
    "valor_total_custo": 125000.00,
    "valor_total_venda": 312500.00,
    "valor_lucro_potencial": 187500.00,
    "quantidade_total": 1250,
    "alertas_abertos": 1,
    "rotatividade": "Alta"
  },
  "alertas_estoque": [
    {
      "id": 42,
      "nome_produto": "Notebook Dell Inspiron 15",
      "estoque_atual": 4,
      "estoque_minimo": 5
    }
  ],
  "agendamentos_proximos": [
    {
      "id": 800,
      "titulo": "Visita ao Cliente ABC",
      "data": "2026-05-22",
      "status": "pendente"
    }
  ],
  "agendamentos_atrasados": [],
  "notificacoes_nao_lidas": 3
}
```

---

## 📱 Interface de Agendamentos

Você também pode acessar via browser:

```
http://localhost:8080/templates/agendamentos.html
```

**Recursos visuais:**
- 📅 Calendário com os agendamentos
- 📋 Lista filtrada por data/status
- ➕ Botão para criar novo agendamento
- ⚠️ Alerta visual de agendamentos atrasados
- ✅ Botões de ação (Concluir, Cancelar, Deletar)

---

## 🔄 Resumo do Fluxo Completo

```
┌─────────────────────────────────────────────────────────────┐
│ 1. CRIAR PRODUTO                                            │
│    └─ Estoque inicial: 25 un                                │
│       └─ Notificação: "Produto Criado"                      │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│ 2. VENDER & ATUALIZAR ESTOQUE                               │
│    └─ Estoque: 25 → 20 → 4                                  │
│       └─ Histórico: 2 movimentos registrados                │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│ 3. ALERTA AUTOMÁTICO                                        │
│    └─ Estoque 4 < Mínimo 5                                  │
│       ├─ 🔔 Notificação in-app                              │
│       ├─ 📧 Email enviado                                   │
│       └─ 📱 SMS enviado (opcional)                          │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│ 4. AGENDAR ENTREGA                                          │
│    └─ Data: 20/05 às 14:00                                  │
│       ├─ 🔔 Notificação criada                              │
│       └─ 📧 Email confirmação                               │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│ 5. MARCAR COMO CONCLUÍDO                                    │
│    └─ Status: pendente → concluído                          │
│       ├─ 🔔 Notificação enviada                             │
│       └─ 📊 Histórico atualizado                            │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│ 6. EXPORTAR RELATÓRIO                                       │
│    └─ Arquivo: relatorio_inventario_maio_2026.xlsx          │
│       ├─ Resumo executivo                                   │
│       ├─ Produtos detalhados                                │
│       └─ Alertas de estoque                                 │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│ 7. VER DASHBOARD                                            │
│    └─ Endpoint: /api/dashboard                              │
│       ├─ Estatísticas                                       │
│       ├─ Alertas                                            │
│       ├─ Agendamentos                                       │
│       └─ Notificações                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Resultado Final

✅ **Tudo integrado e automático:**
- Produto cadastrado com sucesso
- Inventário controlado
- Alertas enviados (email, SMS, in-app)
- Agendamento gerenciado
- Relatório exportado
- Dashboard atualizado em tempo real

---

**Este é o poder do Sistema Nexus! 🚀**
