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

## 🛠️ Instalação e stack técnica

### Requisitos

* Python 3.11+
* PostgreSQL (produção: [Supabase](https://supabase.com/) — use a connection string em `DATABASE_URL`)
* Redis (broker Celery)
* Conta [Asaas](https://www.asaas.com/) (sandbox ou produção) e bot [Telegram](https://core.telegram.org/bots)

### Configuração

```bash
cd FL-Enterprise
cp .env.example .env
# Edite .env: DATABASE_URL, JWT_SECRET, REDIS_URL, ASAAS_*, TELEGRAM_BOT_TOKEN, ASAAS_WEBHOOK_TOKEN
py -m pip install -e .

# Se 'alembic' der erro de "module not found", use o caminho completo do executável:
# Exemplo Windows: .../Scripts/alembic upgrade head
alembic upgrade head
# Inclui 003_operacao_multas (multa/juros % por operação, usados nas cobranças).

PYTHONPATH=. py scripts/seed_admin.py
```

Credenciais padrão do seed (altere em produção): admin `admin@motopay.local` / `adminadmin`, dono `dono@motopay.local` / `donodono`.

### Executar em desenvolvimento

Terminal 1 — API:

```bash
py -m uvicorn motopay.interfaces.api.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 — worker Celery:

```bash
py -m celery -A motopay.infrastructure.messaging.celery_app worker -l INFO
```

Terminal 3 — agendador (Beat):

```bash
py -m celery -A motopay.infrastructure.messaging.celery_app beat -l INFO
```

Terminal 4 — bot Telegram (polling):

```bash
py -m motopay.infrastructure.telegram.bot_main
```

Terminal 5 — dashboard Streamlit:

```bash
py -m streamlit run apps/streamlit_dashboard/app.py
```

Defina `API_PUBLIC_BASE_URL` (ex.: `http://localhost:8000`) para o dashboard. Administradores podem informar `operacao_id` na barra lateral para filtrar dados globais. O painel principal usa **Plotly** (gráficos de pizza, barras e ranking de motos); a página **Financeiro** mostra linha do tempo receita/despesa.

### Webhook Asaas

Configure na Asaas a URL:

`POST {API_PUBLIC_BASE_URL}/webhooks/asaas?token={ASAAS_WEBHOOK_TOKEN}`

O corpo JSON esperado segue o padrão Asaas (`event`, `payment`). Eventos `PAYMENT_RECEIVED` / `PAYMENT_CONFIRMED` atualizam `cobrancas`, lançam `financeiro`, recalculam score e enfileiram notificação Telegram.

### Docker

```bash
docker compose up --build
```

Serviços: `api`, `worker`, `beat`, `bot`, `streamlit`, `redis`. Ajuste `.env` antes (incluindo `DATABASE_URL` apontando para um Postgres acessível pelo container).

**Erro ao baixar `python:3.12-slim` / `registry-1.docker.io` / proxy:**

Mensagens como `lookup proxycamg...: no such host` indicam que o Docker está usando um **proxy** (`HTTP_PROXY`/`HTTPS_PROXY` ou configuração no Docker Desktop) cujo hostname **não resolve** na sua rede (ex.: fora da VPN corporativa).

1. **Proxy só no shell** — limpa `HTTP_PROXY`/`HTTPS_PROXY` **só nesta execução** e roda o compose:
   - PowerShell: `.\scripts\docker_compose_up.ps1`
   - Bash: `bash scripts/docker_compose_up.sh`
   Se o pull **ainda** falhar, o daemon do Docker pode estar usando proxy nas configurações do Desktop (passo seguinte).

2. **Docker Desktop** → *Settings* → *Resources* → *Proxies*: desative proxy manual incorreto ou *Apply & Restart* após corrigir.

3. **VPN / TI** — se o proxy for só na intranet, conecte à VPN ou peça o endereço correto.

4. **Sem Docker** — use `py -m pip install -e .` e os comandos da seção “Executar em desenvolvimento”.

### Estrutura de código

* `motopay/domain` — enums e erros
* `motopay/services` — regras de negócio e casos de uso
* `motopay/infrastructure` — SQLAlchemy, Celery, Asaas, Telegram
* `motopay/interfaces/api` — FastAPI, DTOs Pydantic
* `motopay/interfaces/events` — publicação de eventos
* `apps/streamlit_dashboard` — UI administrativa (somente HTTP na API)

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
