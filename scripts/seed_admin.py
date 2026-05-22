from __future__ import annotations

import os

from motopay.domain.enums import UserRole
from motopay.infrastructure.db.models import Operacao, Usuario
from motopay.infrastructure.db.session import SessionLocal
from motopay.services.auth_service import hash_password
from sqlalchemy import select


def main() -> None:
    db = SessionLocal()
    try:
        existing = db.scalars(select(Usuario).where(Usuario.email == os.getenv("SEED_ADMIN_EMAIL", "admin@motopay.local"))).first()
        if existing:
            print("Seed já aplicado (admin existe).")
            return
        op = Operacao(nome=os.getenv("SEED_OPERACAO_NOME", "Operação Demo"))
        db.add(op)
        db.commit()
        db.refresh(op)
        admin = Usuario(
            email=os.getenv("SEED_ADMIN_EMAIL", "admin@motopay.local"),
            senha_hash=hash_password(os.getenv("SEED_ADMIN_PASSWORD", "adminadmin")),
            tipo=UserRole.ADMIN.value,
            operacao_id=None,
        )
        dono = Usuario(
            email=os.getenv("SEED_DONO_EMAIL", "dono@motopay.local"),
            senha_hash=hash_password(os.getenv("SEED_DONO_PASSWORD", "donodono")),
            tipo=UserRole.DONO.value,
            operacao_id=op.id,
        )
        db.add_all([admin, dono])
        db.commit()
        print(f"Seed concluído. operacao_id={op.id} admin={admin.email} dono={dono.email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
