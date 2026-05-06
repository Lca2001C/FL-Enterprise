# 🛵 MotoPay Admin

### Gestão de Aluguel & Cobrança Automática

Sistema integrado para **gestão de frotas de motos**, controle financeiro e automação de cobranças via Pix/assinaturas com bot no Telegram e dashboard administrativo.

---

## 🚀 Visão Geral

O **MotoPay Admin** é uma plataforma projetada para transformar operações de locação de motos em um sistema:

* Automatizado
* Escalável
* Orientado a dados
* Com baixo custo operacional

Mais do que um sistema de controle, ele evolui para uma **infraestrutura inteligente de gestão financeira e operacional**.

---

## ⚙️ Funcionalidades Principais

### 🤖 Bot de Atendimento Inteligente

* Envio automático de cobranças
* Lembretes de vencimento (D-1)
* Confirmação de pagamento em tempo real
* Estratégias de cobrança progressiva:

  * Amigável → Alerta → Cobrança firme
* Base para evolução em agente autônomo

---

### 💳 Automação de Pagamentos

* Integração com gateways (Asaas / Mercado Pago)
* Cobranças recorrentes:

  * Semanais
  * Mensais
* Métodos:

  * Pix (automático)
  * Cartão de crédito
* Webhooks para confirmação automática

---

### 📊 Dashboard Administrativo

* Faturamento bruto
* Lucro líquido por moto
* Indicadores de inadimplência
* Visão consolidada da operação

---

### 🛠️ Gestão de Manutenção

* Registro de despesas por veículo
* Classificação de custos
* Impacto automático no lucro
* Histórico completo por moto

---

### 🆔 Gestão de Frota

* Vínculo entre:

  * Cliente
  * Moto
  * Contrato
* Status da moto:

  * Disponível
  * Alugada
  * Em manutenção

---

### 📉 Relatórios Financeiros

* Fluxo de caixa
* Performance por ativo (moto)
* Receita vs despesa
* Base para análises avançadas

---

## 🧠 Evoluções Estruturais (Nova Arquitetura)

### 🔧 Separação de Camadas

* **Frontend:** Streamlit (inicialmente)
* **Backend API:** FastAPI
* **Worker assíncrono:** tarefas de cobrança, notificações e eventos

### 🎯 Benefícios:

* Escalabilidade
* Organização de código
* Base para evolução futura

---

## 🤖 Evolução do Bot → Agente Inteligente

* Adaptação de mensagens por comportamento
* Interação com cliente
* Decisão baseada em histórico

---

## 💰 Inteligência Financeira

* ROI por moto
* Payback
* Identificação de prejuízos
* Ranking de ativos

---

## 📉 Gestão de Risco

* Score de cliente (0–100)
* Baseado em:

  * Pagamentos
  * Atrasos
  * Tempo de contrato

---

## 🔐 Controle de Acesso (RBAC Simplificado)

O sistema possui **dois níveis de permissão**, focando simplicidade e controle total:

### 👑 Admin (Você)

* Acesso total ao sistema
* Visualização global (todas as operações)
* Gerenciamento de usuários
* Auditoria completa
* Configurações críticas (API, integrações, regras)

---

### 🏢 Dono da Operação

* Acesso à sua própria frota
* Gestão de clientes e contratos
* Visualização financeira completa da sua operação
* Registro de manutenção
* Acompanhamento de inadimplência

---

### 🔒 Regras de Segurança

* Isolamento de dados por operação
* Logs de ações críticas
* Permissões restritas por escopo

---

## 🔔 Arquitetura baseada em Eventos

Eventos internos:

* `pagamento_confirmado`
* `cliente_inadimplente`
* `moto_em_manutencao`

Reações automáticas:

* Notificações
* Atualização de dados
* Ações do sistema

---

## 📲 Experiência do Usuário (UX)

* Atual: Streamlit
* Futuro: React / Next.js

---

## 🌐 Multi-Tenant

* Suporte a múltiplas operações
* Separação total de dados
* Base para SaaS

---

## 🗄️ Estrutura do Banco de Dados

### motos

* id
* placa
* modelo
* status

---

### clientes

* nome
* cpf
* telefone
* telegram_id

---

### contratos

* id_cliente
* id_moto
* valor_recorrente
* ciclo

---

### financeiro

* tipo
* valor
* descricao
* data
* id_moto

---

## 🔄 Fluxo de Operação

### 1. Cadastro

* Cliente + moto
* Criação de cobrança

### 2. Cobrança

* D-1 envio
* D-0 verificação
* Confirmação automática

### 3. Financeiro

* Registro de custos
* Atualização de lucro

---

## 🛠️ Como Instalar

```bash
git clone https://github.com/seu-usuario/motopay-admin.git
cd motopay-admin
pip install streamlit supabase python-telegram-bot requests python-dotenv
streamlit run app.py
```

---

## 🔐 Segurança

* Tokenização
* Logs de auditoria
* Backups automáticos

---

## 📈 Direção do Projeto

Sistema → Plataforma → Agente inteligente

---

## 📄 Licença

MIT

---

## 💡 Conclusão

Agora com um modelo de acesso simplificado (**Admin + Dono**), o sistema mantém:

* Controle total
* Segurança
* Escalabilidade

Sem complexidade desnecessária.

---
