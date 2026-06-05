# Mercado Pago — configuração (sandbox + produção, por operação)

Modelo: **cada operação** (dono da frota) usa a própria conta Mercado Pago. Credenciais são salvas em **Ajustes** no painel (Access Token, Public Key, Webhook Secret). O `.env` global serve só como fallback.

## Fase 1 — Aplicação no Mercado Pago (por operação)

Para cada operação:

1. Acesse [Mercado Pago Developers](https://www.mercadopago.com.br/developers) com a conta do **recebedor**.
2. Crie uma aplicação (**Checkout Transparente** / Orders API).
3. **Credenciais de teste** (sandbox):
   - Access Token (`TEST-…` ou `APP_USR-…` na aba testes)
   - Public Key de teste
4. **Credenciais de produção** (quando for ao ar):
   - Access Token produção
   - Public Key produção
5. Crie **usuários de teste** (comprador/vendedor) no painel MP.

## Fase 2 — `.env` da plataforma

Copie de [`.env.example`](../.env.example):

| Variável (dev) | Uso |
|----------------|-----|
| `ENVIRONMENT=development` | Permite modo teste |
| `MERCADOPAGO_CREDENTIALS_MODE=test` | Usa `MERCADOPAGO_*_TEST` |
| `MERCADOPAGO_ACCESS_TOKEN_TEST` | Fallback global sandbox |
| `MERCADOPAGO_PUBLIC_KEY_TEST` | Payment Brick (fallback) |
| `MERCADOPAGO_WEBHOOK_SECRET_TEST` | HMAC do webhook sandbox |
| `API_PUBLIC_BASE_URL` | URL pública da API (ngrok em dev) |
| `CORS_ORIGINS` | `http://localhost:5173` |
| `VITE_API_BASE_URL` | `http://localhost:8000` |
| `MERCADOPAGO_VITE_PUBLIC_KEY` | Public Key injetada no build Docker do front |

Opcional em `apps/motopay-frontend/.env` (Vite dev): `VITE_MERCADOPAGO_PUBLIC_KEY=...`

**Produção:** `ENVIRONMENT=production`, credenciais `MERCADOPAGO_*` (sem `_TEST`), `JWT_SECRET` forte, `API_PUBLIC_BASE_URL` HTTPS. O boot exige `MERCADOPAGO_ACCESS_TOKEN` (use token da operação principal).

Valide: `python scripts/mp_config_check.py`

## Fase 3 — Webhooks

O MotoPay processa estes tópicos no painel MP (mesma URL para todas as operações):

| Tópico | Uso |
|--------|-----|
| **Order (Mercado Pago)** | Confirmação Pix/cartão via Orders API |
| **Payment** | Pagamentos legados, estornos, assinatura |
| **Preapproval / subscription** | Status da assinatura recorrente |
| **Chargeback** | Disputas e chargebacks |

URL: `{API_PUBLIC_BASE_URL}/webhooks/mercadopago`

### Local com ngrok

```bash
ngrok http 8000
```

1. Copie a URL HTTPS (ex. `https://abc123.ngrok-free.app`).
2. No `.env`: `API_PUBLIC_BASE_URL=https://abc123.ngrok-free.app`
3. Reinicie a API: `./scripts/start.sh` ou `docker compose up -d api`
4. Painel MP → Webhooks → URL: `{API_PUBLIC_BASE_URL}/webhooks/mercadopago`
5. Evento: **Order (Mercado Pago)**
6. Copie o **secret** → `MERCADOPAGO_WEBHOOK_SECRET_TEST` e/ou Ajustes da operação

Ou use: `python scripts/mp_webhook_tunnel.py --url https://abc123.ngrok-free.app`

### Produção

- URL fixa HTTPS: `https://sua-api.com/webhooks/mercadopago`
- Mesmo evento **Order**
- Secret em Ajustes (por operação) e/ou `MERCADOPAGO_WEBHOOK_SECRET` global

Cada conta MP de operação cadastra a **mesma URL** da plataforma; o backend resolve o secret pela cobrança (`mercadopago_order_id`).

## Fase 4 — Ajustes no painel MotoPay

1. `./scripts/start.sh` (migrations + seed)
2. Login **dono** ou **admin** com escopo da operação
3. **Ajustes** → Mercado Pago → preencha **os três** campos (token, public key, webhook secret)
4. Confirme: `mercadopago_credentials_complete: true` no texto de status em Ajustes

## Fase 5 — Docker

```bash
docker compose build api worker beat bot frontend
docker compose exec -T api env PYTHONPATH=/usr/local/lib/python3.11/site-packages:/app \
  alembic -c /app/alembic.ini upgrade head
```

## Fase 6 — Checklist sandbox

- [ ] `python scripts/mp_config_check.py` sem erros críticos
- [ ] Cobranças → Pagar → Pix gera código (polling automático no modal)
- [ ] Clientes → ícone cartão → Card Brick salva cartão
- [ ] Cobranças → Pagar → selecionar cartão salvo + CVV no Brick
- [ ] Cartão com 3DS: Status Screen / iframe no modal
- [ ] Contratos → assinatura MP → link `init_point` para o cliente autorizar
- [ ] Pagamento teste no MP → cobrança `recebido` via webhook (Order ou assinatura)
- [ ] `mercadopago_order_id` na cobrança

## Recursos adicionais (código)

- **Portal do pagador**: link público `/pay/{token}` (Cobranças → Link); TTL configurável (`PAYER_PORTAL_TOKEN_TTL_DAYS`)
- **OAuth**: Ajustes → Conectar Mercado Pago (`MERCADOPAGO_OAUTH_*`); refresh automático do token
- Cobrança com **multa/juros** (Pix, cartão e assinatura em atraso)
- **Estorno** total/parcial + webhook de confirmação; notificação ao dono (Telegram)
- **Chargebacks**: webhook + badge na cobrança; despesa automática se disputa perdida
- **Reconciliação**: Celery Beat a cada 15 min (pagamentos, estornos, chargebacks, Pix expirado)
- **Telegram**: `/pix` e inadimplência enviam link do portal + Pix
- **Assinatura**: ciclo semanal/mensal editável; sync com MP ao mudar valor/ciclo
- **Cartão padrão** e cartões salvos no portal público
- **E-mail obrigatório** em produção (`clientes.email`)

Variáveis extras: `PAYER_PORTAL_BASE_URL`, `MERCADOPAGO_OAUTH_CLIENT_ID`, `MERCADOPAGO_OAUTH_CLIENT_SECRET`, `PAYER_PORTAL_TOKEN_TTL_DAYS`

## Fase 7 — Produção

Checklist detalhado: [MERCADOPAGO_PRODUCTION_CHECKLIST.md](MERCADOPAGO_PRODUCTION_CHECKLIST.md)

- [ ] Credenciais **produção** em Ajustes (não TEST)
- [ ] Webhook HTTPS em cada conta MP
- [ ] `CORS_ORIGINS` com URL do admin (Vercel)
- [ ] `VITE_API_BASE_URL` na build do front
- [ ] Teste com valor baixo antes de liberar clientes
