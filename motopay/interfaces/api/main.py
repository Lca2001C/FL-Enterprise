from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from motopay.domain.exceptions import (
    ConflictError,
    ForbiddenError,
    MotoPayError,
    NotFoundError,
    UnauthorizedError,
)
from motopay.interfaces.api.routers import (
    analytics,
    auth,
    clientes,
    cobrancas,
    contratos,
    financeiro,
    motos,
    operacoes,
    usuarios,
    webhooks,
)

app = FastAPI(title="MotoPay Admin API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
