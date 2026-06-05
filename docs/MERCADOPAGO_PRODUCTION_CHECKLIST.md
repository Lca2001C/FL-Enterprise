# Mercado Pago — checklist de producao

Use apos concluir o sandbox ([MERCADOPAGO_SETUP.md](MERCADOPAGO_SETUP.md)).

## Variaveis de ambiente

- [ ] `ENVIRONMENT=production`
- [ ] `JWT_SECRET` forte (sem `change-me`)
- [ ] `MERCADOPAGO_ACCESS_TOKEN` (boot da API)
- [ ] `MERCADOPAGO_PUBLIC_KEY` (fallback Brick)
- [ ] `MERCADOPAGO_WEBHOOK_SECRET`
- [ ] `MERCADOPAGO_CREDENTIALS_MODE` **nao** use `test` em producao
- [ ] `API_PUBLIC_BASE_URL` HTTPS (ex. `https://api.seudominio.com`)
- [ ] `CORS_ORIGINS` com URL do admin (ex. Vercel)
- [ ] `VITE_API_BASE_URL` na build do frontend = mesma API HTTPS
- [ ] `REDIS_URL` com autenticacao; Postgres com senha forte
- [ ] `PAYER_PORTAL_BASE_URL` = URL publica do painel (links de pagamento e redirect OAuth)
- [ ] `MERCADOPAGO_OAUTH_CLIENT_ID` / `MERCADOPAGO_OAUTH_CLIENT_SECRET` (se usar OAuth)
- [ ] `PAYER_PORTAL_TOKEN_TTL_DAYS` (padrao 30)

## Por operacao (Ajustes)

- [ ] Access Token **producao** (nao `TEST-`)
- [ ] Public Key producao
- [ ] Webhook Secret do painel MP producao
- [ ] `mercadopago_credentials_complete: true` em Ajustes

## Webhook Mercado Pago

- [ ] URL: `{API_PUBLIC_BASE_URL}/webhooks/mercadopago`
- [ ] Eventos: **Order**, **Payment**, **Preapproval/subscription**, **Chargeback**
- [ ] HTTPS valido
- [ ] Webhook Secret em Ajustes (obrigatorio mesmo com OAuth)
- [ ] Cada conta MP da operacao cadastra a mesma URL da plataforma

## Portal e OAuth

- [ ] `PAYER_PORTAL_BASE_URL` aponta para o frontend em producao
- [ ] OAuth redirect: `{API_PUBLIC_BASE_URL}/api/v1/operacoes/mp-oauth/callback`
- [ ] Testar link do portal (Cobranças → Link) e pagamento Pix/cartao sem login

## Deploy

- [ ] `alembic upgrade head` antes do trafego
- [ ] Celery worker + beat ativos
- [ ] `python scripts/mp_config_check.py` em ambiente de staging com vars de prod
- [ ] Pagamento real de valor baixo antes de liberar clientes
