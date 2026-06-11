# 🚀 Guia de Deploy — MotoPay Admin

Passo a passo para colocar o sistema **no ar em produção**, do servidor zerado ao primeiro pagamento real.

## Arquitetura em produção

```
Internet ──HTTPS(443)──▶ Caddy (TLS automático Let's Encrypt)
                           │
                           ▼
                        frontend (nginx) ── serve o painel React/PWA
                           │  proxy interno: /api, /socket.io, /health
                           ▼
                          api (FastAPI) ──▶ db (PostgreSQL 16)
                           │              ▶ redis (autenticado)
                           │              ▶ storage de fotos: volume local OU S3/R2
        worker (Celery) ◀──┤
        beat (agendador) ◀─┤
        bot (Telegram)  ◀──┘
        backup (pg_dump diário → volume postgres_backups)
```

Tudo sobe com **Docker Compose** usando o overlay de produção
([docker-compose.prod.yml](docker-compose.prod.yml)). A única porta pública é o
Caddy (80/443) — API, Redis e métricas ficam restritos ao servidor.

> **Rotas alternativas (nuvem gerenciada):** **Render** (blueprint pronto —
> ver [Apêndice A](#apêndice-a--deploy-no-render-blueprint)) ou Railway +
> Supabase + Upstash + Vercel (ver "Deploy nuvem" do [README.md](README.md)).
> O corpo deste guia cobre a rota **VPS**, que roda o sistema completo em um
> único servidor.

---

## 1. Pré-requisitos

| Item | Detalhe |
|---|---|
| **Servidor (VPS)** | Ubuntu 22.04+ — mínimo 2 vCPU / 4 GB RAM / 40 GB disco (Hetzner, DigitalOcean, Contabo, AWS Lightsail…) |
| **Domínio** | Ex.: `app.seudominio.com`, com acesso ao painel de DNS |
| **Conta Mercado Pago** | Com aplicação criada no [painel de desenvolvedor](https://www.mercadopago.com.br/developers/panel/app) |
| **Bot Telegram** | Token do [@BotFather](https://t.me/botfather) |
| **Sentry** (opcional, recomendado) | Projeto criado em sentry.io para captura de erros |

---

## 2. ⚠️ ANTES DE TUDO: rotacionar credenciais expostas

O arquivo `.env` esteve em commits antigos do repositório (histórico do git).
**Considere comprometidas e rotacione antes do deploy:**

1. **Token do bot Telegram** — no @BotFather: `/mybots` → seu bot → *API Token* → *Revoke current token*.
2. **Credenciais Mercado Pago de teste** — gere novas no painel MP (ou simplesmente não as use em produção).
3. **Nunca** copie o `.env` de desenvolvimento para o servidor — crie um novo seguindo o passo 4.

---

## 3. Preparar o servidor

```bash
# 3.1 Conecte por SSH e atualize o sistema
apt update && apt upgrade -y

# 3.2 Instale Docker + Compose plugin (script oficial)
curl -fsSL https://get.docker.com | sh

# 3.3 Firewall: só SSH e HTTP/HTTPS
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# 3.4 Clone o projeto
git clone <URL_DO_SEU_REPOSITORIO> /opt/motopay
cd /opt/motopay
```

**DNS:** no painel do seu domínio, crie um registro **A** apontando
`app.seudominio.com` → IP do servidor. Aguarde propagar
(`ping app.seudominio.com` deve responder com o IP do VPS) — o Caddy só
consegue emitir o certificado TLS depois disso.

---

## 4. Criar o `.env` de produção

```bash
cp .env.example .env
nano .env
```

Gere segredos fortes (rode no próprio servidor):

```bash
openssl rand -hex 32   # rode 3x: JWT_SECRET, POSTGRES_PASSWORD, REDIS_PASSWORD
```

### Variáveis obrigatórias

| Variável | Valor em produção |
|---|---|
| `ENVIRONMENT` | `production` |
| `JWT_SECRET` | hex de 64 chars gerado acima (valores `change-me*` são **recusados** no boot) |
| `POSTGRES_USER` / `POSTGRES_DB` | ex.: `motopay` / `motopay` |
| `POSTGRES_PASSWORD` | senha forte (`postgres` é **recusado** no boot) |
| `REDIS_PASSWORD` | senha forte (produção **exige** Redis autenticado) |
| `DOMAIN` | `app.seudominio.com` (usado pelo Caddy para o TLS) |
| `API_PUBLIC_BASE_URL` | `https://app.seudominio.com` (webhooks MP + OAuth) |
| `PAYER_PORTAL_BASE_URL` | `https://app.seudominio.com` (links de pagamento + retorno OAuth) |
| `CORS_ORIGINS` | `https://app.seudominio.com` |
| `TRUSTED_PROXY_IPS` | `172.16.0.0/12` (rede interna do Docker — necessário para o rate-limit ver o IP real do cliente atrás do Caddy/nginx) |
| `MERCADOPAGO_CREDENTIALS_MODE` | `production` (em `ENVIRONMENT=production` o modo teste é ignorado) |
| `MERCADOPAGO_ACCESS_TOKEN` | Access Token de **produção** da aplicação MP (`APP_USR-…`) |
| `MERCADOPAGO_PUBLIC_KEY` | Public Key de **produção** |
| `MERCADOPAGO_WEBHOOK_SECRET` | preencher no passo 8 (após cadastrar o webhook) |
| `MERCADOPAGO_VITE_PUBLIC_KEY` | igual à `MERCADOPAGO_PUBLIC_KEY` (vai para o build do frontend) |
| `MERCADOPAGO_OAUTH_CLIENT_ID` / `MERCADOPAGO_OAUTH_CLIENT_SECRET` | da aplicação MP (botão "Conectar Mercado Pago" do dono) |
| `TELEGRAM_BOT_TOKEN` | token **novo** do BotFather (passo 2) |
| `VITE_API_BASE_URL` | `SAME_ORIGIN` (frontend e API no mesmo domínio) |
| `VITE_DISABLE_PWA` | `false` (habilita instalação como app no celular) |
| `SENTRY_DSN` | DSN do projeto Sentry (recomendado; sem ele só há warning) |

> O sistema **valida tudo isso no boot**: com `ENVIRONMENT=production`, a API
> se recusa a subir com JWT fraco, Postgres/Redis sem senha ou Mercado
> Pago/Telegram ausentes (exceções documentadas via `ALLOW_PRODUCTION_WITHOUT_*`).
> Se a API não subir, `docker compose logs api` mostra exatamente qual variável corrigir.

---

## 5. Subir a stack

```bash
cd /opt/motopay
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

Aguarde todos os serviços ficarem `healthy` (1–2 min). O Caddy emite o
certificado TLS automaticamente na primeira requisição —
`https://app.seudominio.com` já deve responder.

> Todos os serviços têm `restart: unless-stopped` — voltam sozinhos após
> reboot do servidor ou crash.

---

## 6. Rodar as migrações do banco

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T api \
  alembic -c /app/alembic.ini upgrade head
```

Repita este comando **a cada atualização** do sistema (passo 12).

---

## 7. Criar os usuários iniciais

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T \
  -e ALLOW_PRODUCTION_SEED=true \
  -e SEED_ADMIN_EMAIL=admin@seudominio.com \
  -e SEED_ADMIN_PASSWORD='SenhaForteAdmin!2026' \
  -e SEED_DONO_EMAIL=dono@seudominio.com \
  -e SEED_DONO_PASSWORD='SenhaForteDono!2026' \
  -e SEED_OPERACAO_NOME='Minha Operação' \
  api python scripts/seed_admin.py
```

- Use senhas **fortes e únicas** — as senhas padrão (`adminadmin`/`donodono`) não devem existir em produção.
- O seed só roda uma vez (se o admin já existe, ele avisa e não altera nada).
- Faça login em `https://app.seudominio.com` com o admin e confirme o acesso.

---

## 8. Configurar o Mercado Pago (produção)

No [painel de desenvolvedor MP](https://www.mercadopago.com.br/developers/panel/app), na sua aplicação:

### 8.1 Credenciais de produção
*Credenciais de produção* → copie **Access Token** e **Public Key** para o
`.env` (`MERCADOPAGO_ACCESS_TOKEN`, `MERCADOPAGO_PUBLIC_KEY`,
`MERCADOPAGO_VITE_PUBLIC_KEY`). Para ativá-las o MP pode exigir dados do
negócio (processo de homologação da conta).

### 8.2 Webhook
*Webhooks* → *Configurar notificações*:
- **URL:** `https://app.seudominio.com/webhooks/mercadopago`
- **Eventos:** `Order`, `Pagamentos`, `Planos e assinaturas`, `Contestações (chargebacks)`
- Copie a **assinatura secreta** gerada → cole em `MERCADOPAGO_WEBHOOK_SECRET` no `.env`.

> Sem o secret configurado, a API **rejeita** webhooks em produção
> (fail-closed) — pagamentos não seriam confirmados automaticamente.

### 8.3 OAuth (login do dono na conta MP dele)
- Em *URLs de redirecionamento*, registre **exatamente**:
  `https://app.seudominio.com/api/v1/operacoes/mp-oauth/callback`
- Copie **Client ID** e **Client Secret** → `MERCADOPAGO_OAUTH_CLIENT_ID` / `MERCADOPAGO_OAUTH_CLIENT_SECRET`.

### 8.4 Aplicar e conferir

```bash
# Recriar serviços com o .env atualizado
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d

# Conferência automática da configuração MP
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T api \
  python scripts/mp_config_check.py
```

Depois, cada **dono de operação** entra em **Ajustes → Conectar Mercado Pago**
e autoriza a própria conta MP (OAuth) — os pagamentos da operação caem na conta dele.

---

## 9. Verificações pós-deploy (smoke test)

```bash
# API saudável (local e via HTTPS público)
curl -s http://localhost:8000/health          # → {"status":"ok"}
curl -s https://app.seudominio.com/health     # → {"status":"ok"}

# Worker/beat ativos e tarefas agendadas
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs beat --tail 20
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs worker --tail 20
```

No painel (`https://app.seudominio.com`):
1. Login como admin → criar operação/usuários reais.
2. Login como dono → **Ajustes → Conectar Mercado Pago** → badge verde "OAuth conectado".
3. Cadastrar moto + cliente (com CPF e e-mail) + contrato.
4. Gerar uma cobrança e **pagar um valor baixo real** (ex.: R$ 1 de teste com Pix).
5. Confirmar que o webhook chegou e a cobrança mudou para **Recebido** sozinha
   (`docker compose ... logs api | grep webhook`).
6. Conferir que o bot Telegram responde e envia a cobrança.
7. Instalar o PWA no celular (Compartilhar → Adicionar à Tela de Início no iOS).

---

## 10. Backups

O serviço `backup` roda `pg_dump` **diariamente** e mantém os últimos
`BACKUP_RETENTION_DAYS` (padrão 7) no volume `postgres_backups`.

```bash
# Listar backups
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backup ls -lh /backups

# Backup manual imediato
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backup /usr/local/bin/backup_postgres.sh

# Restaurar (CUIDADO: sobrescreve o banco)
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T backup \
  pg_restore -h db -U $POSTGRES_USER -d $POSTGRES_DB --clean --if-exists /backups/motopay_AAAAMMDD_HHMMSS.dump
```

**Recomendado:** copie os dumps para fora do servidor (S3, Backblaze, rclone)
via cron no host — backup no mesmo disco não protege contra perda do servidor.

---

## 11. Fotos de motos — armazenamento persistente

As fotos das motos são gravadas pelo backend e servidas pela API (com controle de
acesso por operação). O **onde** depende de `STORAGE_BACKEND`:

### Rota VPS (este guia) — já persistente, sem ação extra

Com `STORAGE_BACKEND=local` (padrão), as fotos vão para `UPLOAD_DIR`
(`/data/uploads`), montado no volume Docker nomeado **`uploads_data`**. Esse
volume **sobrevive** a `up --build`, restart e reboot — as fotos **não** somem no
redeploy. Nada a configurar; só inclua o volume no seu backup externo.

### Rota disco efêmero (Render, Railway, Heroku) — use S3

Nessas plataformas o filesystem é **efêmero**: a cada deploy o disco é zerado e as
fotos somem. Configure um storage de objetos S3-compatível (AWS S3, **Cloudflare
R2**, Backblaze B2, DigitalOcean Spaces, MinIO ou Supabase Storage):

1. Crie um **bucket** (ex.: `motopay-uploads`) e uma chave de acesso (Access Key + Secret).
2. Defina no ambiente do serviço (`.env` / painel da plataforma):

   ```
   STORAGE_BACKEND=s3
   S3_BUCKET=motopay-uploads
   S3_ACCESS_KEY_ID=...
   S3_SECRET_ACCESS_KEY=...
   # Cloudflare R2 (recomendado — sem egress):
   S3_ENDPOINT_URL=https://<ACCOUNT_ID>.r2.cloudflarestorage.com
   S3_REGION=auto
   # AWS S3: deixe S3_ENDPOINT_URL vazio e use S3_REGION=us-east-1 (ou a sua região)
   ```

3. Redeploy. A API valida no boot: com `STORAGE_BACKEND=s3` sem bucket/credenciais,
   ela **não sobe** e o log diz o que falta.

O bucket pode ser **privado** — as imagens continuam passando pela API
(`GET /api/v1/motos/{id}/imagem`), que exige login e respeita o escopo da operação.
Não é preciso deixar o bucket público.

> Trocar de backend não migra as fotos já existentes automaticamente. Em produção
> nova isso é irrelevante; se já houver fotos em disco, copie a pasta `motos/` para
> o bucket (ex.: `rclone copy /data/uploads/motos remote:motopay-uploads/motos`)
> antes de virar a chave.

---

## 12. Monitoramento

- **Sentry** (`SENTRY_DSN`): erros da API e do Celery capturados automaticamente.
- **Logs:** `docker compose ... logs -f api worker beat bot` (JSON estruturado com correlation_id).
- **Métricas Prometheus:** API `GET /health/metrics` (autenticado) e worker em `127.0.0.1:9808/metrics` no host.
- **Alertas internos:** sino no topo do painel (inadimplência, falhas).

---

## 13. Atualizar o sistema (novas versões)

```bash
cd /opt/motopay
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T api \
  alembic -c /app/alembic.ini upgrade head
curl -s https://app.seudominio.com/health
```

> `docker compose restart` **não aplica** mudanças de código (a imagem é
> imutável) — sempre use `up --build -d`.

---

## 14. Checklist final antes de liberar para clientes

- [ ] Token do Telegram e credenciais MP de teste **rotacionados** (passo 2)
- [ ] `.env` de produção criado no servidor, **fora do git**
- [ ] DNS propagado e `https://app.seudominio.com` com cadeado válido
- [ ] Todos os containers `healthy` e com `restart: unless-stopped`
- [ ] `alembic upgrade head` executado
- [ ] Admin/dono criados com senhas fortes (seed)
- [ ] Webhook MP cadastrado com secret no `.env` (HTTPS, eventos Order/Payment/Preapproval/Chargeback)
- [ ] OAuth MP: redirect URL registrada e dono conectado (badge verde em Ajustes)
- [ ] `scripts/mp_config_check.py` sem erros
- [ ] Pagamento real de valor baixo confirmado automaticamente via webhook
- [ ] Bot Telegram respondendo
- [ ] Backup diário gerando dump + cópia externa configurada
- [ ] Fotos de motos persistentes: volume `uploads_data` (VPS) **ou** `STORAGE_BACKEND=s3` (disco efêmero) — passo 11
- [ ] Sentry recebendo eventos (force um erro de teste se quiser validar)
- [ ] Firewall: somente 22/80/443 abertos (`ufw status`)

---

## Solução de problemas

| Sintoma | Causa provável / correção |
|---|---|
| API não sobe, log mostra `RuntimeError: JWT_SECRET…` ou similar | Validador de produção: alguma variável do passo 4 fraca/ausente. O log diz exatamente qual. |
| `https://` não funciona / certificado inválido | DNS ainda não propagou para o IP do VPS, ou portas 80/443 bloqueadas. `docker compose ... logs caddy` mostra o erro do Let's Encrypt. |
| Webhook MP retorna 403 | `MERCADOPAGO_WEBHOOK_SECRET` ausente ou diferente do painel MP (produção é fail-closed). |
| "Configuração Mercado Pago incompleta: Webhook Secret ausente" ao gerar Pix | Preencher `MERCADOPAGO_WEBHOOK_SECRET` no `.env` e recriar a API (passo 8.2). |
| Botão "Conectar Mercado Pago" desabilitado | `MERCADOPAGO_OAUTH_CLIENT_ID/SECRET` vazios no `.env` do servidor (passo 8.3). |
| OAuth volta com erro `invalid redirect_uri` | A URL registrada no painel MP não é **exatamente** `https://DOMAIN/api/v1/operacoes/mp-oauth/callback`. |
| Rate-limit bloqueando usuários legítimos / IPs iguais nos logs | `TRUSTED_PROXY_IPS` não inclui a rede Docker (`172.16.0.0/12`). |
| Cobranças não geram sozinhas no vencimento | Serviço `beat` parado — `docker compose ... ps` e `logs beat`. |
| Fotos de motos somem após redeploy | Disco efêmero com `STORAGE_BACKEND=local` — mude para `STORAGE_BACKEND=s3` (passo 11). No VPS, confirme que o volume `uploads_data` não foi removido (`docker volume ls`). |
| API não sobe com `RuntimeError: STORAGE_BACKEND=s3 exige…` | Faltam `S3_BUCKET`/`S3_ACCESS_KEY_ID`/`S3_SECRET_ACCESS_KEY` (passo 11). |
| `RuntimeError: MERCADOPAGO_ACCESS_TOKEN é obrigatório em produção` (deploy "Exited with status 1") | **O build funcionou** — a API se recusa a iniciar sem as credenciais de produção. Defina `MERCADOPAGO_ACCESS_TOKEN` (e os demais secrets) no ambiente. Se ainda não tem MP/Telegram prontos, use `ALLOW_PRODUCTION_WITHOUT_MERCADOPAGO=true` / `ALLOW_PRODUCTION_WITHOUT_TELEGRAM=true` temporariamente. Veja o Apêndice A. |
| `RuntimeError: REDIS_URL em produção exige autenticação` | Redis gerenciado de rede privada sem senha (Render Key Value interno): defina `ALLOW_PRODUCTION_REDIS_WITHOUT_AUTH=true`. Em Redis exposto, use senha (`rediss://:SENHA@…`). |

---

## Apêndice A — Deploy no Render (Blueprint)

O Render **não roda `docker-compose`**: cada serviço é construído isoladamente a
partir de um Dockerfile. O repositório já inclui um **blueprint** que cria tudo de
uma vez: API, worker, beat, bot, Postgres e Redis (Key Value).

> ⚠️ O erro `RuntimeError: MERCADOPAGO_ACCESS_TOKEN é obrigatório em produção` /
> `Exited with status 1` **não é falha de build** — é a API se recusando a subir
> sem os secrets de produção. A solução é preencher as variáveis abaixo.

### A.1 — Criar a stack com o blueprint

1. No Render: **New → Blueprint** e conecte este repositório (o
   [`render.yaml`](render.yaml) na raiz é detectado automaticamente).
2. O Render cria Postgres, Redis e os serviços API/worker/beat/bot a partir do
   [`Dockerfile`](Dockerfile). `DATABASE_URL` e `REDIS_URL` são preenchidos
   automaticamente; `ALLOW_PRODUCTION_REDIS_WITHOUT_AUTH=true` já vem no blueprint
   (o Redis interno do Render é rede privada sem senha).
3. O Render pede os valores dos secrets (`sync: false`). Preencha **todos** —
   senão a API não inicia (validação de produção).

### A.2 — Secrets a preencher (grupo `motopay-shared`)

| Variável | Valor |
|---|---|
| `JWT_SECRET` | hex de 64 chars — gere com `openssl rand -hex 32` |
| `MERCADOPAGO_ACCESS_TOKEN` | Access Token **de produção** (`APP_USR-…`) |
| `MERCADOPAGO_PUBLIC_KEY` | Public Key de produção |
| `MERCADOPAGO_WEBHOOK_SECRET` | assinatura secreta do webhook (passo 8.2) |
| `MERCADOPAGO_OAUTH_CLIENT_ID` / `..._SECRET` | da aplicação MP (botão "Conectar" do dono) |
| `TELEGRAM_BOT_TOKEN` | token do @BotFather |
| `API_PUBLIC_BASE_URL` | URL pública do serviço **motopay-api** (ex.: `https://motopay-api.onrender.com`) |
| `PAYER_PORTAL_BASE_URL` | URL pública do **frontend** |
| `CORS_ORIGINS` | URL pública do **frontend** |
| `S3_BUCKET`, `S3_ENDPOINT_URL`, `S3_REGION`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | storage de fotos — **obrigatório no Render** (disco efêmero), ver passo 11 |
| `SENTRY_DSN` | opcional |

> **Ainda não tem Mercado Pago/Telegram de produção?** Para subir a API primeiro,
> adicione ao grupo `ALLOW_PRODUCTION_WITHOUT_MERCADOPAGO=true` e
> `ALLOW_PRODUCTION_WITHOUT_TELEGRAM=true` (remova quando configurar de verdade).
> O storage S3 continua obrigatório se quiser fotos persistentes.

### A.3 — Migrações

O serviço `motopay-api` tem `preDeployCommand: alembic … upgrade head` — as
migrações rodam automaticamente a cada deploy, antes de entrar em tráfego.

### A.4 — Usuários iniciais

No **Shell** do serviço `motopay-api` (aba *Shell* no painel Render):

```bash
ALLOW_PRODUCTION_SEED=true SEED_ADMIN_EMAIL=admin@seudominio.com \
  SEED_ADMIN_PASSWORD='SenhaForte!2026' SEED_DONO_EMAIL=dono@seudominio.com \
  SEED_DONO_PASSWORD='SenhaForteDono!2026' python scripts/seed_admin.py
```

### A.5 — Frontend (admin React)

O frontend é um serviço **separado** (outro Dockerfile, precisa da URL da API no
build). Crie no Render um **Web Service** apontando para o repo com:

- **Root Directory:** `apps/motopay-frontend`
- **Runtime:** Docker (usa `apps/motopay-frontend/Dockerfile`)
- **Build-time env:** `VITE_API_BASE_URL` = URL pública da `motopay-api`
  (ex.: `https://motopay-api.onrender.com`), `VITE_DISABLE_PWA=false`

Depois de publicado, volte ao grupo `motopay-shared` e preencha
`PAYER_PORTAL_BASE_URL` e `CORS_ORIGINS` com a URL pública do frontend, e
`API_PUBLIC_BASE_URL` com a da API; registre o webhook e o redirect OAuth do
Mercado Pago apontando para a URL da API (passos 8.2 e 8.3).

> Atenção: o `nginx.conf` do frontend faz proxy de `/api` para o hostname `api`
> (válido só no docker-compose). No Render, frontend e API têm URLs distintas, por
> isso o `VITE_API_BASE_URL` aponta direto para a URL pública da API e o
> `CORS_ORIGINS` precisa conter a URL do frontend.
