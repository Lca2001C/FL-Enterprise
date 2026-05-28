import { Printer, X } from 'lucide-react';
import type { FinanceiroOut, MotoOut } from '../apiTypes';
import { formatBrl, formatDate } from '../utils/format';

type Props = {
  entries: FinanceiroOut[];
  motos: MotoOut[];
  onClose: () => void;
};

function computeTotals(entries: FinanceiroOut[]) {
  let receitas = 0;
  let despesas = 0;
  for (const e of entries) {
    const v = Number(e.valor);
    if (e.tipo === 'receita') receitas += v;
    else despesas += v;
  }
  return { receitas, despesas, saldo: receitas - despesas };
}

const FinanceStatementModal = ({ entries, motos, onClose }: Props) => {
  const motoById = new Map(motos.map((m) => [m.id, m]));
  const { receitas, despesas, saldo } = computeTotals(entries);

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="statement-overlay">
      <div className="statement-shell glass animate-fade">
        <div className="statement-toolbar no-print">
          <h3>Extrato financeiro</h3>
          <div className="statement-toolbar-actions">
            <button type="button" className="btn-secondary" onClick={handlePrint}>
              <Printer size={18} /> Imprimir / Salvar PDF
            </button>
            <button type="button" className="icon-btn" onClick={onClose} aria-label="Fechar">
              <X size={20} />
            </button>
          </div>
        </div>

        <div className="statement-body" id="finance-statement-print">
          <div className="statement-print-header">
            <h2>MotoPay — Extrato financeiro</h2>
            <p>Gerado em {formatDate(new Date().toISOString().slice(0, 10))}</p>
          </div>

          <div className="summary-grid">
            <div className="summary-card receita">
              <span>Receitas</span>
              <strong>{formatBrl(receitas)}</strong>
            </div>
            <div className="summary-card despesa">
              <span>Despesas</span>
              <strong>{formatBrl(despesas)}</strong>
            </div>
            <div className="summary-card saldo">
              <span>Saldo</span>
              <strong>{formatBrl(saldo)}</strong>
            </div>
          </div>

          <table className="statement-table">
            <thead>
              <tr>
                <th>Data</th>
                <th>Descrição</th>
                <th>Tipo</th>
                <th>Valor</th>
                <th>Moto</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => {
                const moto = e.moto_id ? motoById.get(e.moto_id) : undefined;
                return (
                  <tr key={e.id}>
                    <td>{formatDate(e.data)}</td>
                    <td>{e.descricao}</td>
                    <td>
                      <span className={`tipo-badge ${e.tipo}`}>{e.tipo.toUpperCase()}</span>
                    </td>
                    <td className="valor">{formatBrl(e.valor)}</td>
                    <td>{moto ? `${moto.placa} — ${moto.modelo}` : '—'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <style jsx global>{`
        @media print {
          body * {
            visibility: hidden;
          }
          #finance-statement-print,
          #finance-statement-print * {
            visibility: visible;
          }
          #finance-statement-print {
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
            background: white !important;
            color: #0f172a !important;
            padding: 24px;
          }
          .no-print {
            display: none !important;
          }
          .statement-table th,
          .statement-table td {
            color: #0f172a !important;
            border-color: #cbd5e1 !important;
          }
          .summary-card {
            border: 1px solid #cbd5e1 !important;
            background: #f8fafc !important;
          }
        }
      `}</style>

      <style jsx>{`
        .statement-overlay {
          position: fixed;
          inset: 0;
          background: rgba(0, 0, 0, 0.65);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
          padding: 16px;
        }
        .statement-shell {
          width: min(920px, 100%);
          max-height: 90vh;
          overflow: auto;
          border-radius: 16px;
          padding: 20px;
        }
        .statement-toolbar {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 12px;
          margin-bottom: 16px;
          flex-wrap: wrap;
        }
        .statement-toolbar h3 {
          margin: 0;
        }
        .statement-toolbar-actions {
          display: flex;
          gap: 10px;
          align-items: center;
        }
        .statement-print-header {
          margin-bottom: 20px;
        }
        .statement-print-header h2 {
          margin: 0 0 4px;
          font-family: 'Outfit', sans-serif;
        }
        .statement-print-header p {
          margin: 0;
          color: var(--text-muted);
          font-size: 0.9rem;
        }
        .summary-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
          gap: 12px;
          margin-bottom: 20px;
        }
        .summary-card {
          padding: 14px 16px;
          border-radius: 12px;
          border: 1px solid var(--glass-border);
          background: rgba(0, 0, 0, 0.2);
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .summary-card span {
          font-size: 0.8rem;
          color: var(--text-muted);
          text-transform: uppercase;
          letter-spacing: 0.04em;
        }
        .summary-card strong {
          font-size: 1.25rem;
        }
        .summary-card.receita strong {
          color: var(--accent);
        }
        .summary-card.despesa strong {
          color: var(--danger);
        }
        .summary-card.saldo strong {
          color: var(--primary);
        }
        .statement-table {
          width: 100%;
          border-collapse: collapse;
        }
        .statement-table th,
        .statement-table td {
          padding: 10px 12px;
          border-bottom: 1px solid var(--glass-border);
          text-align: left;
          font-size: 0.9rem;
        }
        .statement-table th {
          color: var(--text-muted);
          font-size: 0.8rem;
        }
        .tipo-badge {
          display: inline-block;
          padding: 2px 8px;
          border-radius: 6px;
          font-size: 0.7rem;
          font-weight: 700;
        }
        .tipo-badge.receita {
          background: rgba(16, 185, 129, 0.15);
          color: var(--accent);
        }
        .tipo-badge.despesa {
          background: rgba(239, 68, 68, 0.15);
          color: var(--danger);
        }
        .valor {
          font-weight: 700;
        }
        .btn-secondary {
          background: var(--secondary);
          color: white;
          border: none;
          padding: 10px 16px;
          border-radius: 8px;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          gap: 8px;
        }
        .icon-btn {
          background: none;
          border: none;
          color: var(--text-muted);
          cursor: pointer;
          padding: 6px;
        }
      `}</style>
    </div>
  );
};

export default FinanceStatementModal;

export { computeTotals };
