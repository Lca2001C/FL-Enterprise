# Webhook Mercado Pago — túnel ativo (dev)

Atualizado automaticamente em `2026-06-08`.

## URL para cadastrar no painel MP

**Webhooks → URL de produção/teste → evento Order (Mercado Pago):**

```
https://rent-institutional-nebraska-competitors.trycloudflare.com/webhooks/mercadopago
```

## Passos no painel Mercado Pago

1. [Mercado Pago Developers](https://www.mercadopago.com.br/developers) → sua aplicação
2. **Webhooks** / **Notificações**
3. Cole a URL acima
4. Marque o evento **Order (Mercado Pago)**
5. **Salvar** → copie o **secret** gerado
6. Cole em:
   - `.env` → `MERCADOPAGO_WEBHOOK_SECRET_TEST=`
   - Painel MotoPay → **Ajustes** → Webhook Secret → **Salvar Alterações**
7. Rode: `python scripts/sync_mp_operacao_from_env.py` (ou reinicie após atualizar só o `.env`)

## Manter o túnel

O túnel **cloudflared** precisa ficar rodando. Se reiniciar o PC, gere um novo túnel:

```bash
npx cloudflared tunnel --url http://localhost:8000
python scripts/mp_webhook_tunnel.py --url https://NOVA-URL.trycloudflare.com
docker compose up -d --force-recreate api
```

Com **ngrok** (após `ngrok config add-authtoken <token>`):

```bash
ngrok http 8000
python scripts/mp_webhook_tunnel.py --url https://SEU-SUBDOMINIO.ngrok-free.app
docker compose up -d --force-recreate api
```
