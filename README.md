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

* Integração **Mercado Pago** (Pix, assinatura recorrente, webhook)
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

* **Frontend:** React (Vite) — [`apps/motopay-frontend`](apps/motopay-frontend)
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
* **Tour guiado no painel:** após login, use o banner na Visão Geral ou o botão **Tour guiado** no menu lateral para percorrer as telas com explicações sobre frota, cobrança automática, Telegram e ajustes. Para repetir depois, acesse **Minha Conta → Ajuda → Reiniciar tour guiado**.

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

* **Painel web (React/Vite):** [`apps/motopay-frontend`](apps/motopay-frontend) — usado por **admin** e **dono** da operação.
* **Admin — Usuários:** aba **Usuários** lista administradores e donos de operação (filtros por tipo e operação) e permite criar novos donos.
* **Dono:** vê apenas dados da sua operação (`operacao_id` no token). Telas principais:
  * **Contratos** — nova locação (cliente + moto + valor), encerrar, gerar Pix/assinatura Mercado Pago.
  * **Clientes** — cadastro com **Telegram ID** (obrigatório para bot: lembretes, Pix em atraso, confirmação).
  * **Cobranças** — listagem com multa/juros, copiar Pix em `pendente` ou `atrasado`.
  * **Dashboard** — inadimplência resumida com atalho para contratos e copiar Pix.
  * **Ajustes** — multa fixa, juros diários e **mensagens do Telegram** (notificações e comandos do bot), editáveis por operação em *Ajustes da Operação*; placeholders como `{placa}` e `{valor_total}`; worker e bot leem do banco na próxima mensagem (sem redeploy).
* **Admin:** mesmo painel + seletor de operação no topo; branding "MotoPay Admin".
* Sessão renovada automaticamente via refresh token (`POST /auth/refresh`).
* **PWA (instalável no celular e desktop):** o painel pode ser adicionado à tela inicial ou barra de apps como app standalone (ícone próprio, splash iOS, service worker com shell offline).
  * **Produção (HTTPS):** após deploy, Android Chrome exibe banner **Instalar app** (ou menu ⋮ → Instalar app); iOS Safari: **Compartilhar → Adicionar à Tela de Início**; desktop Chrome: ícone na barra de apps ou menu **Instalar MotoPay**.
  * **Rede local:** `./scripts/start.sh --lan` e abra `http://<IP-da-máquina>:5173` no celular (mesma Wi‑Fi). Em HTTP o navegador pode não mostrar prompt automático — siga as instruções do banner ou o menu do Chrome.
  * **Regenerar ícones e splash:** `python scripts/generate_pwa_icons.py` (gera `public/icons/`, `favicon.ico`, `public/splash/`, `public/screenshots/`). Manifest e service worker são gerados no `npm run build` ([`vite-plugin-pwa`](apps/motopay-frontend/vite.config.ts)).
  * **Dev desktop com SW:** `cd apps/motopay-frontend && VITE_PWA_DEV=true npm run dev` (opcional).
  * **Validar após build:** `cd apps/motopay-frontend && npm run build && npm test` — o teste `pwaManifest.build.test.ts` valida `dist/manifest.webmanifest` (ícones 192/512/maskable, screenshots).
  * **Lighthouse (Chrome DevTools):** abra o painel em HTTPS → **Application → Manifest** (sem erros) → aba **Lighthouse** → categoria **Progressive Web App** (instalável, ícones, service worker).
  * **Reinstalar no celular:** remova o ícone antigo da tela inicial → limpe dados do site (Chrome: Configurações → Privacidade → Dados do site) → abra a URL de produção → instale de novo. Isso evita ícone genérico ou manifest em cache.
  * **Play Store (futuro):** publicação como TWA (Bubblewrap) + `assetlinks.json` — fora do escopo atual; o manifest já inclui screenshots wide/narrow para preparação.

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
* **Após o vencimento:** o job diário (Celery Beat) recalcula multa e juros (% configurados por operação), gera um **novo Pix** com o total atualizado e envia o código pelo **Telegram** (copia e cola). Enquanto o contrato estiver em atraso, isso se repete **todo dia** (juros diários).

### 3. Financeiro

* Registro de custos
* Atualização de lucro

---

## 🛠️ Instalação e stack técnica

### Requisitos

* Python 3.11+
* **PostgreSQL** (qualquer instância compatível). O app usa `DATABASE_URL` padrão SQLAlchemy; [Supabase](https://supabase.com/) é só uma opção de **hospedagem** de Postgres, não um requisito do código.
* Redis (broker Celery)
* Conta [Mercado Pago Developers](https://www.mercadopago.com.br/developers) e bot [Telegram](https://core.telegram.org/bots)

Os exemplos usam `python` (Linux, macOS, containers). **No Windows**, substitua por `py` se preferir (ex.: `py -m pip install -e .`).

### Configuração

**Não commite o arquivo `.env`** (ele está no `.gitignore`). Use apenas `.env.example` como modelo.

```bash
cd FL-Enterprise
cp .env.example .env
# Edite .env: veja comentários em .env.example
# - DATABASE_URL: localhost vs Docker (host db); alinhar com POSTGRES_* se usar o mesmo banco
# - POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB: usados pelo docker-compose ao montar DATABASE_URL
# - JWT_SECRET: gere um segredo forte (nunca use o placeholder em produção)
# - REDIS_URL, MERCADOPAGO_*, TELEGRAM_BOT_TOKEN
python -m pip install -e .

# Se 'alembic' der erro de "module not found", use o executável do venv (Windows):
#   .\Scripts\alembic.exe upgrade head
# Ou: py -m alembic upgrade head (se não houver pasta local `alembic/` conflitando)
alembic upgrade head
# Migrações até 006_admin_dono_only (somente papéis admin e dono; remove usuarios operador/cliente).

# Postgres local na porta 5434 (se 5432 estiver ocupada):
# DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5434/motopay

PYTHONPATH=. python scripts/seed_admin.py
```

Opcional: gere/atualize o lock fechado com `pip-tools` — `pip-compile pyproject.toml -o requirements-lock.txt --strip-extras` (CI valida sincronia). Ver [`requirements.txt`](requirements.txt) e [`requirements-lock.txt`](requirements-lock.txt).

Ferramentas de desenvolvimento: `python -m pip install -e ".[dev]"` (tudo), ou só `".[lint]"` / `".[test]"` para CI separado.

Credenciais padrão do seed (altere em produção): admin `admin@motopay.local` / `adminadmin`, dono `dono@motopay.local` / `donodono`.

### Executar em desenvolvimento

Terminal 1 — API:

```bash
python -m uvicorn motopay.interfaces.api.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 — worker Celery:

```bash
python -m celery -A motopay.infrastructure.messaging.celery_app worker -l INFO
```

Terminal 3 — agendador (Beat):

```bash
python -m celery -A motopay.infrastructure.messaging.celery_app beat -l INFO
```

Terminal 4 — bot Telegram (polling):

```bash
python -m motopay.infrastructure.telegram.bot_main
```

Terminal 5 — admin React (Vite):

```bash
cd apps/motopay-frontend
npm install
npm run dev
```

Abra `http://localhost:5173`. Use `VITE_API_BASE_URL` apontando para a API como o navegador acessa (ex.: `http://localhost:8000`). Configure `CORS_ORIGINS` na API com a origem do front (ex.: `http://localhost:5173`). Administradores usam **Operação (escopo)** no topo para filtrar por `operacao_id` nas chamadas à API.

### Mercado Pago (Pix, cartão, webhook)

Guia completo: [`docs/MERCADOPAGO_SETUP.md`](docs/MERCADOPAGO_SETUP.md). Validar env: `python scripts/mp_config_check.py`.

- **Credenciais por operação:** dono/admin salva Access Token, Public Key e Webhook Secret em **Ajustes** (os três juntos).
- **Fallback global:** variáveis `MERCADOPAGO_*` / `MERCADOPAGO_*_TEST` no `.env` quando a operação não tem credenciais.
- **Webhook:** `POST {API_PUBLIC_BASE_URL}/webhooks/mercadopago` — evento **Order (Mercado Pago)** no painel MP; validação HMAC (`x-signature`). Em dev local use ngrok: `python scripts/mp_webhook_tunnel.py --url https://….ngrok-free.app`.
- Orders confirmadas atualizam `cobrancas`, lançam `financeiro`, recalculam score e enfileiram Telegram.

### Papéis de usuário

| Papel | Acesso |
|-------|--------|
| **admin** | Todas as operações; criar operações e usuários; escopo multi-operação |
| **dono** | Painel operacional completo da própria operação (frota, clientes, contratos, cobranças, financeiro, métricas, ajustes); sem menu Admin |

### Bot Telegram — comandos

* `/promessa <dias> <motivo>` — registrar promessa de pagamento
* `/pix` — última cobrança pendente com Pix
* `/status` — vencimento e inadimplência
* `/ajuda` — ajuda fixa ou resposta via OpenAI se `AI_BOT_ENABLED=true`

Beat diário configurável: `CELERY_BEAT_HOUR` / `CELERY_BEAT_MINUTE` (padrão 11:00).

### Health check da API

* **GET** `/health` — retorno JSON `{"status":"ok"}`. Usado pelo `docker compose` (serviço `api`) e por balanceadores. Base path raiz (não usa prefixo `/api/v1`).

### Deploy nuvem (Railway · Supabase · Upstash · Vercel)

Referência rápida (detalhes de variáveis: [`.env.example`](.env.example)):

#### Checklist rápido (pré-produção)

1. **`ENVIRONMENT=production`** e **`JWT_SECRET`** forte (sem prefixo `change-me`).
2. **`MERCADOPAGO_ACCESS_TOKEN`**, **`MERCADOPAGO_WEBHOOK_SECRET`**, webhook Mercado Pago HTTPS apontando para **`/webhooks/mercadopago`**.
3. **`TELEGRAM_BOT_TOKEN`**, **`REDIS_URL`** com autenticação (ex.: Upstash **`rediss://:TOKEN@…`**), Postgres com senha forte (`DATABASE_URL` / `POSTGRES_PASSWORD` — valores `postgres` recusados em produção).
4. **`TRUSTED_PROXY_IPS`** se a API ficar atrás de proxy/balanceador; **`CORS_ORIGINS`** com a(s) URL(s) do admin (ex.: Vercel).
5. Build do admin com **`VITE_API_BASE_URL`** = URL HTTPS pública da API.
6. **Release/deploy:** `alembic upgrade head` antes de aceitar tráfego; pelo menos um processo **Celery Beat** para agendamentos.
7. Seeds: só com **`ALLOW_PRODUCTION_SEED=true`** e senhas fortes via **`SEED_*`** — não use credenciais padrão (`adminadmin` / `donodono`).

**Supabase (Postgres)**

* Defina `DATABASE_URL` como string `postgresql+psycopg://…` gerada pela Supabase, com `sslmode=require` na query quando indicado pela documentação.
* Para alta concorrência, use URL do **Transaction pooler** (porta típica `6543`) na API/workers. Se o Alembic falhar com o pooler, defina `DATABASE_MIGRATION_URL` como conexão **direta** ao Postgres da Supabase (host tipo `db.*.supabase.co`, porta `5432`; veja `.env.example`). As migrações usam `DATABASE_MIGRATION_URL` quando estiver definida.
* Ajuste `DATABASE_POOL_SIZE` / `DATABASE_MAX_OVERFLOW` ao limite da instância.

**Upstash (Redis)**

* Cole `REDIS_URL` no formato **`rediss://…`** (TLS). Celery já ativa TLS automaticamente quando a URL começa com `rediss://`.
* Timeouts: `REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS`, `REDIS_SOCKET_TIMEOUT_SECONDS`, `REDIS_HEALTH_CHECK_INTERVAL_SECONDS`.

**Railway (API + Celery worker + Celery Beat + opcional Telegram bot)**

* Use o [`Dockerfile`](Dockerfile) da raiz. O **CMD** padrão sobe a API com **`PORT`** definido pela Railway (`${PORT:-8000}` local).
* Crie **vários serviços** no mesmo projeto (deploy a partir da mesma imagem) e **sobrescreva o comando** onde precisar, por exemplo:
  * Celery worker: `celery -A motopay.infrastructure.messaging.celery_app worker -l INFO`
  * Celery Beat: `celery -A motopay.infrastructure.messaging.celery_app beat -l INFO`
  * Bot Telegram: `python -m motopay.infrastructure.telegram.bot_main`
* **Release / comando de deploy**: `alembic upgrade head` (com as mesmas variáveis de ambiente da API).
* Coloque todas as secrets da aplicação no painel Railway (espelho de `.env.example`). `ENVIRONMENT=production`, `JWT_SECRET`, `MERCADOPAGO_ACCESS_TOKEN`, `MERCADOPAGO_WEBHOOK_SECRET`, `REDIS_URL`, `DATABASE_URL`, `CORS_ORIGINS` (URLs do admin no Vercel), etc.

**Vercel (admin React)**

* No projeto Vercel, defina **Root Directory** como `apps/motopay-frontend`.
* Variável de **build**: `VITE_API_BASE_URL` = URL **pública HTTPS** da API no Railway.

`vercel.json` no frontend inclui rewrites SPA (fallback `index.html`) e headers de segurança compatíveis com chamadas HTTPS à API.

### Docker

**Início rápido (recomendado):**

```bash
chmod +x scripts/start.sh   # uma vez (Linux/macOS/Git Bash)
./scripts/start.sh
```

O script [`scripts/start.sh`](scripts/start.sh) cria `.env` se ausente, sobe `db`, `redis`, `api`, `worker`, `beat`, `frontend` (e `bot` se `TELEGRAM_BOT_TOKEN` estiver definido), aguarda `/health`, executa migrations e seed. Opções: `--dev` (hot reload), `--no-seed`, `--down` (parar stack).

**Dados demo (opcional):** após o seed inicial (`seed_admin.py`), popule motos, clientes e cobranças de exemplo com:

```bash
docker compose run --rm api python scripts/seed_demo.py
# ou, fora do Docker:
PYTHONPATH=. python scripts/seed_demo.py
```

Requer que [`scripts/seed_admin.py`](scripts/seed_admin.py) já tenha sido executado (cria operação e usuários base).

**Manual (desenvolvimento):**

```bash
docker compose up --build
```

**Produção / staging hardened (Redis sem porta pública, senhas obrigatórias):**

```bash
# Defina POSTGRES_PASSWORD e REDIS_PASSWORD fortes no .env antes de subir
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build
```

O overlay [`docker-compose.prod.yml`](docker-compose.prod.yml) remove a exposição `6379:6379`, ativa `requirepass` no Redis, valida `ENVIRONMENT=production` nos serviços app e inclui serviço **`backup`** (pg_dump diário no volume `postgres_backups`).

O `Dockerfile` inclui a pasta `scripts/` (ex.: `docker compose run --rm api python scripts/seed_admin.py` após o stack subir). A imagem roda como usuário **`appuser`** (UID 1000), não root.

Serviços: `db`, `redis`, `api`, `worker`, `beat`, `bot`, `frontend`. Crie o `.env` a partir de `.env.example` antes do primeiro `up`.

Credenciais do Postgres no Compose dev vêm de `POSTGRES_USER`, `POSTGRES_PASSWORD` e `POSTGRES_DB` (padrão `postgres` / `postgres` / `motopay` — **apenas para dev**). Em produção use overlay prod + senhas fortes; a aplicação recusa `postgres/postgres` quando `ENVIRONMENT=production`.

**Celery Beat:** o agendamento é persistido no volume Docker `celery_beat_data` (arquivo `--schedule` em `/data/…`). Se esse volume for apagado, o Beat pode re-disparar tarefas conforme o estado novo do scheduler — trate como risco operacional em produção (backups ou alternativa de scheduler externo, se necessário).

Healthchecks: **`api`** (`GET /health`), **`worker`** (`GET :9808/metrics`), **`bot`** (chave Redis `bot:heartbeat`). O serviço **frontend** usa nginx; beat não expõe HTTP.

### Backup do banco

* **Manual:** `./scripts/backup_postgres.sh` (requer `pg_dump` e `POSTGRES_*` ou `DATABASE_URL`; grava em `./backups/`).
* **Compose prod:** serviço `backup` executa o script a cada 24h no volume `postgres_backups`.
* **Postgres gerenciado** (Supabase/Railway): use backups nativos do provedor; o script serve para dumps ad hoc ou self-hosted.

Serviços aguardam `db` e `redis` **saudáveis** antes de subir a API; o worker **não** depende da API estar pronta.

**Erro ao baixar `python:3.11-slim` / `registry-1.docker.io` / proxy:**

Mensagens como `lookup proxycamg...: no such host` indicam que o Docker está usando um **proxy** (`HTTP_PROXY`/`HTTPS_PROXY` ou configuração no Docker Desktop) cujo hostname **não resolve** na sua rede (ex.: fora da VPN corporativa).

1. **Proxy só no shell** — limpa `HTTP_PROXY`/`HTTPS_PROXY` **só nesta execução** e sobe a stack:
   - Bash / Git Bash: `./scripts/start.sh` (já faz `unset` de proxy antes do compose)
   - PowerShell (manual):
     ```powershell
     Remove-Item Env:HTTP_PROXY, Env:HTTPS_PROXY, Env:http_proxy, Env:https_proxy -ErrorAction SilentlyContinue
     docker compose up --build
     ```
   Se o pull **ainda** falhar, o daemon do Docker pode estar usando proxy nas configurações do Desktop (passo seguinte).

2. **Docker Desktop** → *Settings* → *Resources* → *Proxies*: desative proxy manual incorreto ou *Apply & Restart* após corrigir.

3. **VPN / TI** — se o proxy for só na intranet, conecte à VPN ou peça o endereço correto.

4. **Sem Docker** — use `python -m pip install -e .` e os comandos da seção “Executar em desenvolvimento”.

### Estrutura de código

* `motopay/domain` — enums e erros
* `motopay/services` — regras de negócio e casos de uso
* `motopay/infrastructure` — SQLAlchemy, Celery, Mercado Pago, Telegram
* `motopay/interfaces/api` — FastAPI, DTOs Pydantic
* `apps/motopay-frontend` — UI administrativa React (Vite; consome a API via HTTP)

---

## 🔐 Segurança e segredos

* **Repositório:** não versionar `.env`, `_env` nem arquivos `celerybeat-schedule*`. Quem já commitou `_env` ou `.env` no passado deve auditar o histórico, por exemplo: `git log --all --full-history --name-only -- _env` (e o mesmo para `.env`). Se aparecerem commits com segredos, rotacione credenciais e considere `git filter-repo`.
* **`JWT_SECRET`:** com `ENVIRONMENT=production`, a aplicação **recusa** valores ausentes ou que comecem com `change-me` (`RuntimeError` ao carregar config). Em desenvolvimento (`development`), o placeholder do `.env.example` ainda é aceito. Gere um segredo forte: `python -c "import secrets; print(secrets.token_hex(32))"`.
* **Produção (config):** além disso, com `ENVIRONMENT=production` a API **exige** `MERCADOPAGO_ACCESS_TOKEN`, `TELEGRAM_BOT_TOKEN`, salvo escape hatches em [`.env.example`](.env.example) (`ALLOW_PRODUCTION_WITHOUT_*`). Lista vazia de `CORS_ORIGINS`, Redis ou banco em `localhost` só gera **aviso de log**.
* **Seed em produção:** `scripts/seed_admin.py` **sai com erro** se `ENVIRONMENT=production` sem `ALLOW_PRODUCTION_SEED=true`; use sempre senhas customizadas neste cenário.
* **Telegram:** sem `TELEGRAM_BOT_TOKEN` (bot criado no @BotFather), o bot e parte das notificações não funcionam.
* **Mercado Pago:** sem `MERCADOPAGO_ACCESS_TOKEN` configurado, cobranças Pix usam código demo local; confirmação real exige webhook MP.
* **Vazamento no histórico Git:** se `.env` ou chaves reais já foram commitados, além de remover do índice atual, **rotacione** todos os segredos (JWT, Mercado Pago, Telegram, senha do banco) e, se o remoto já foi público, considere limpar o histórico com ferramentas como `git filter-repo` com apoio do time.

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
