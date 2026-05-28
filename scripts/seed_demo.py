from datetime import date, timedelta
from decimal import Decimal

from motopay.domain.enums import (
    CicloCobranca,
    CobrancaStatus,
    ContratoStatus,
    FinanceiroTipo,
    MotoStatus,
)
from motopay.infrastructure.db.models import Cliente, Cobranca, Contrato, Financeiro, Moto, Operacao
from motopay.infrastructure.db.session import SessionLocal
from sqlalchemy import select, text


def main():
    db = SessionLocal()
    try:
        op = db.scalars(select(Operacao)).first()
        if not op:
            print("Execute o seed_admin.py primeiro!")
            return

        # O banco já cuida dos defaults (2% multa, 0.1% juros)
        # Mas vamos garantir que a operação demo existe com nome correto
        op.nome = "Operação Demo"
        db.add(op)
        db.commit()
        db.execute(text("DELETE FROM financeiro"))
        db.execute(text("DELETE FROM cobrancas"))
        db.execute(text("DELETE FROM contratos"))
        db.execute(text("DELETE FROM motos"))
        db.execute(text("DELETE FROM clientes"))
        db.commit()

        # 1. Criar 8 Motos
        motos_data = [
            ("BRA2E24", "Honda CG 160 Titan", MotoStatus.ALUGADA),
            ("KRY7711", "Yamaha Fazer 250", MotoStatus.ALUGADA),
            ("LUC1010", "Honda Biz 125", MotoStatus.ALUGADA),
            ("ADV9900", "Honda XRE 300 Sahara", MotoStatus.ALUGADA),
            ("ECO5522", "Yamaha Fluo 125", MotoStatus.ALUGADA),
            ("WORK888", "Honda CG 160 Cargo", MotoStatus.ALUGADA),
            ("MN77001", "Honda CB 300F Twister", MotoStatus.MANUTENCAO),
            ("DS11223", "Yamaha Factor 150", MotoStatus.DISPONIVEL),
        ]
        motos = []
        moto_kms = [1200, 18500, 5400, 36000, 10200, 14000, 8000, 500]
        for (placa, modelo, status), km in zip(motos_data, moto_kms, strict=True):
            m = Moto(
                operacao_id=op.id,
                placa=placa,
                modelo=modelo,
                status=status.value,
                km=km,
            )
            db.add(m)
            motos.append(m)
        db.commit()

        # 2. Criar 6 Clientes
        clientes_data = [
            ("Lucas Oliveira", "111.222.333-44", "(11) 98888-7777", 98),
            ("Mariana Silva", "555.666.777-88", "(11) 97777-6666", 92),
            ("Carlos Souza", "999.888.777-66", "(11) 96666-5555", 65),
            ("Beatriz Santos", "444.333.222-11", "(11) 95555-4444", 100),
            ("Fernanda Lima", "222.333.444-55", "(11) 93333-2222", 85),
            ("Ricardo Gomes", "333.444.555-66", "(11) 92222-1111", 70),
        ]
        clientes = []
        for nome, cpf, tel, score in clientes_data:
            c = Cliente(operacao_id=op.id, nome=nome, cpf=cpf, telefone=tel, score=score)
            db.add(c)
            clientes.append(c)
        db.commit()

        # 3. Criar Contratos 1:1 (Cada cliente com sua moto)
        contratos = []
        for i in range(6):
            # Os primeiros 6 clientes pegam as primeiras 6 motos
            is_atrasado = i == 2  # Carlos Souza está atrasado
            vencimento = (
                date.today() - timedelta(days=5)
                if is_atrasado
                else date.today() + timedelta(days=i + 1)
            )

            ct = Contrato(
                operacao_id=op.id,
                cliente_id=clientes[i].id,
                moto_id=motos[i].id,
                valor_recorrente=Decimal(str(250.0 + (i * 20))),
                ciclo=CicloCobranca.SEMANAL.value,
                status=ContratoStatus.ATIVO.value,
                data_inicio=date.today() - timedelta(days=90),
                proximo_vencimento=vencimento,
                inadimplente=is_atrasado,
            )
            db.add(ct)
            contratos.append(ct)
        db.commit()

        # 4. Gerar 50+ Lançamentos Financeiros (Histórico de 3 meses)
        print("Gerando 60 lançamentos financeiros...")
        for ct in contratos:
            # Receitas Semanais (12 semanas por contrato)
            for sem in range(12):
                # Simular alguns atrasos ou faltas de pagamento para o Carlos (contrato 2)
                if ct.cliente_id == clientes[2].id and sem > 9:
                    continue  # Carlos parou de pagar há 2 semanas

                db.add(
                    Financeiro(
                        operacao_id=op.id,
                        tipo=FinanceiroTipo.RECEITA.value,
                        valor=ct.valor_recorrente,
                        data=date.today() - timedelta(days=(sem * 7) + 3),
                        descricao=f"Aluguel Semanal - {ct.cliente.nome}",
                        moto_id=ct.moto_id,
                        contrato_id=ct.id,
                    )
                )

        # Despesas de Manutenção para as Motos
        manutencoes = [
            (250.0, "Troca de Pneu e Pastilhas", motos[0].id),
            (85.0, "Troca de Óleo Mobil 1L", motos[1].id),
            (120.0, "Ajuste de Relação e Limpeza", motos[2].id),
            (450.0, "Revisão Geral 10k km", motos[3].id),
            (1100.0, "Reparo de Carenagem e Farol", motos[6].id),
            (55.0, "Troca de Lâmpada e Cabo", motos[4].id),
        ]
        for val, desc, mid in manutencoes:
            # Várias manutenções em datas diferentes
            for m_idx in range(2):
                db.add(
                    Financeiro(
                        operacao_id=op.id,
                        tipo=FinanceiroTipo.DESPESA.value,
                        valor=Decimal(str(val * (m_idx + 1))),
                        data=date.today() - timedelta(days=(m_idx * 30) + 15),
                        descricao=desc,
                        moto_id=mid,
                    )
                )

        # 5. Gerar Cobranças detalhadas
        for ct in contratos:
            # Uma recebida
            db.add(
                Cobranca(
                    operacao_id=op.id,
                    contrato_id=ct.id,
                    valor=ct.valor_recorrente,
                    vencimento=date.today() - timedelta(days=7),
                    status=CobrancaStatus.RECEBIDO.value,
                )
            )
            # Uma pendente
            db.add(
                Cobranca(
                    operacao_id=op.id,
                    contrato_id=ct.id,
                    valor=ct.valor_recorrente,
                    vencimento=ct.proximo_vencimento,
                    status=CobrancaStatus.ATRASADO.value
                    if ct.inadimplente
                    else CobrancaStatus.PENDENTE.value,
                    pix_copia_cola=f"00020101021226870014br.gov.bcb.pix2565demo/p/v2/DEMO_PIX_{ct.id}_BR5913MOTOPAY",
                )
            )

        db.commit()
        print("MEGA DEMO carregado com sucesso! Sistema pronto para demonstração completa.")
    except Exception as e:
        db.rollback()
        print(f"Erro ao carregar demo: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
