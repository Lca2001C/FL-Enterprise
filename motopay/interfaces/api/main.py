import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from motopay.config import get_settings
from motopay.domain.enums import UserRole
from motopay.domain.exceptions import (
    ConflictError,
    ForbiddenError,
    MotoPayError,
    NotFoundError,
    UnauthorizedError,
)
from motopay.infrastructure.security.client_ip import get_client_ip
from motopay.interfaces.api.middleware import ObservabilityMiddleware
from motopay.interfaces.api.routers import (
    analytics,
    auth,
    clientes,
    cobrancas,
    config,
    contratos,
    financeiro,
    motos,
    operacoes,
    ops,
    public_pay,
    usuarios,
    webhooks,
)
from motopay.interfaces.api.routers import health as health_router
from motopay.observability import get_logger, setup_logging
from motopay.observability.metrics import setup_metrics
from motopay.services.auth_service import decode_token

logger = get_logger(__name__)
audit_logger = logging.getLogger("motopay.audit")

_settings = get_settings()

# Setup observability
setup_logging(level=_settings.log_level)
setup_metrics()

if _settings.sentry_dsn.strip():
    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=_settings.sentry_dsn,
            environment=_settings.environment,
            integrations=[FastApiIntegration(), CeleryIntegration()],
            traces_sample_rate=0.1,
        )
    except ImportError:
        logger.warning("sentry-sdk não instalado; SENTRY_DSN ignorado")

app = FastAPI(title="MotoPay Admin API", version="0.1.0")

# Add observability middleware (must be added before other middlewares)
app.add_middleware(ObservabilityMiddleware)

def _cors_allow_origins() -> list[str]:
    """Origens permitidas no CORS. Em produção, lista vazia = nenhuma origem (sem fallback para '*')."""
    s = get_settings()
    parsed = [x.strip() for x in s.cors_origins.split(",") if x.strip()]
    if s.environment == "production":
        if not parsed:
            logger.warning(
                "CORS_ORIGINS vazio em produção: navegadores só acessam a API em mesmo host/porta; "
                "configure CORS_ORIGINS com URLs explícitas se precisar de front em outro domínio."
            )
        return parsed
    if parsed:
        return parsed
    return ["*"]


def _cors_allow_origin_regex() -> str | None:
    s = get_settings()
    if s.environment == "production":
        return None
    # Celular/tablet na mesma Wi‑Fi (ex.: http://192.168.0.209:5173)
    return r"https?://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d+)?"


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins(),
    allow_origin_regex=_cors_allow_origin_regex(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://sdk.mercadopago.com https://http2.mlstatic.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data: blob: https://http2.mlstatic.com https://mla-s1-p.mlstatic.com; "
    "connect-src 'self' https://api.mercadopago.com https://events.mercadopago.com; "
    "frame-src https://www.mercadopago.com.br https://www.mercadopago.com; "
    "worker-src 'self' blob:; "
    "object-src 'none'; "
    "base-uri 'self';"
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = _CSP
    if get_settings().environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.middleware("http")
async def audit_admin_global_scope(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if not path.startswith("/api/v1/") or path.startswith("/api/v1/auth/"):
        return response
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return response
    if request.query_params.get("operacao_id") or request.headers.get("x-operacao-id"):
        return response
    try:
        data = decode_token(auth_header.split(" ", 1)[1])
        role = UserRole(data["role"])
    except (UnauthorizedError, KeyError, ValueError, TypeError):
        return response
    if role != UserRole.ADMIN:
        return response
    audit_logger.info(
        "admin_global_scope sub=%s email=%s method=%s path=%s ip=%s",
        data.get("sub"),
        data.get("email"),
        request.method,
        path,
        get_client_ip(request),
    )
    return response


def _translate_pydantic_error(err: dict) -> str:
    """Converte mensagens de erro do Pydantic (inglês) para português."""
    etype = err.get("type", "")
    ctx = err.get("ctx") or {}
    loc = err.get("loc", ())
    field = str(loc[-1]) if loc else "campo"

    _TRANSLATIONS: dict[str, str] = {
        "missing": f"O campo '{field}' é obrigatório.",
        "string_too_short": f"O campo '{field}' deve ter pelo menos {ctx.get('min_length', '?')} caractere(s).",
        "string_too_long": f"O campo '{field}' deve ter no máximo {ctx.get('max_length', '?')} caractere(s).",
        "string_type": f"O campo '{field}' deve ser um texto.",
        "int_type": f"O campo '{field}' deve ser um número inteiro.",
        "int_parsing": f"O campo '{field}' deve ser um número inteiro válido.",
        "float_type": f"O campo '{field}' deve ser um número.",
        "float_parsing": f"O campo '{field}' deve ser um número válido.",
        "bool_type": f"O campo '{field}' deve ser verdadeiro ou falso.",
        "bool_parsing": f"O campo '{field}' deve ser verdadeiro ou falso.",
        "value_error": err.get("msg", f"Valor inválido no campo '{field}'."),
        "enum": f"O campo '{field}' tem um valor inválido. Opções: {ctx.get('expected', '?')}.",
        "literal_error": f"O campo '{field}' tem um valor inválido.",
        "greater_than": f"O campo '{field}' deve ser maior que {ctx.get('gt', '?')}.",
        "greater_than_equal": f"O campo '{field}' deve ser no mínimo {ctx.get('ge', '?')}.",
        "less_than": f"O campo '{field}' deve ser menor que {ctx.get('lt', '?')}.",
        "less_than_equal": f"O campo '{field}' deve ser no máximo {ctx.get('le', '?')}.",
        "date_from_datetime_parsing": f"O campo '{field}' deve ser uma data válida (AAAA-MM-DD).",
        "datetime_parsing": f"O campo '{field}' deve ser uma data/hora válida.",
        "decimal_parsing": f"O campo '{field}' deve ser um valor decimal válido.",
        "url_parsing": f"O campo '{field}' deve ser uma URL válida.",
        "json_invalid": "O corpo da requisição contém JSON inválido.",
        "json_type": "O corpo da requisição deve ser um objeto JSON.",
        "extra_forbidden": f"O campo '{field}' não é permitido.",
        "model_type": f"Estrutura de dados inválida no campo '{field}'.",
    }

    # email_validator retorna type="value_error" com msg em inglês — traduzimos pela mensagem
    msg = err.get("msg", "")
    if "email" in msg.lower() or "e-mail" in msg.lower():
        return f"O campo '{field}' deve conter um e-mail válido."
    if "special-use" in msg or "reserved" in msg:
        return f"O campo '{field}' deve conter um e-mail válido."

    return _TRANSLATIONS.get(etype, err.get("msg", f"Valor inválido no campo '{field}'."))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [_translate_pydantic_error(e) for e in exc.errors()]
    detail = errors[0] if len(errors) == 1 else errors
    return JSONResponse(status_code=422, content={"detail": detail})


@app.exception_handler(UnauthorizedError)
async def unauthorized_handler(_: Request, exc: UnauthorizedError) -> JSONResponse:
    return JSONResponse(status_code=401, content={"detail": str(exc)})


@app.exception_handler(ForbiddenError)
async def forbidden_handler(_: Request, exc: ForbiddenError) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": str(exc)})


@app.exception_handler(NotFoundError)
async def not_found_handler(_: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
async def conflict_handler(_: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(MotoPayError)
async def generic_motopay_handler(_: Request, exc: MotoPayError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


api_prefix = "/api/v1"
app.include_router(webhooks.router)
app.include_router(auth.router, prefix=api_prefix)
app.include_router(operacoes.router, prefix=api_prefix)
app.include_router(usuarios.router, prefix=api_prefix)
app.include_router(motos.router, prefix=api_prefix)
app.include_router(clientes.router, prefix=api_prefix)
app.include_router(contratos.router, prefix=api_prefix)
app.include_router(financeiro.router, prefix=api_prefix)
app.include_router(cobrancas.router, prefix=api_prefix)
app.include_router(public_pay.router, prefix=api_prefix)
app.include_router(config.router, prefix=api_prefix)
app.include_router(analytics.router, prefix=api_prefix)
app.include_router(ops.router, prefix=api_prefix)

# Health check and observability routers
app.include_router(health_router.router)
app.include_router(health_router.alert_router)
