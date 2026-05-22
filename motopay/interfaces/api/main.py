import logging

from fastapi import FastAPI, Request
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
from motopay.interfaces.api.routers import (
    analytics,
    auth,
    clientes,
    cobrancas,
    contratos,
    financeiro,
    motos,
    operacoes,
    portal,
    usuarios,
    webhooks,
)
from motopay.services.auth_service import decode_token

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("motopay.audit")

_settings = get_settings()
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


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
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
app.include_router(analytics.router, prefix=api_prefix)
app.include_router(portal.router, prefix=api_prefix)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
