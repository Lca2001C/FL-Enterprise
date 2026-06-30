import { useEffect, useRef, useState } from 'react';
import { Paperclip, Trash2, Download, FileText, Image as ImageIcon } from 'lucide-react';
import { useAuth } from '../AuthContext';
import type { AnexoOut } from '../apiTypes';
import { parseApiError } from '../utils/apiError';

const ACCEPTED = 'application/pdf,image/jpeg,image/png,image/webp';

type Props = {
  /** Base da entidade, ex.: `/api/v1/multas/123`. */
  entityBase: string;
  /** Base do recurso para download/delete de anexos, ex.: `/api/v1/multas`. */
  anexoBase: string;
  onChange?: () => void;
};

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const AnexoUploader = ({ entityBase, anexoBase, onChange }: Props) => {
  const { api } = useAuth();
  const [anexos, setAnexos] = useState<AnexoOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const load = async () => {
    setLoading(true);
    try {
      const res = await api.get<AnexoOut[]>(`${entityBase}/anexos`);
      setAnexos(res.data);
    } catch (e) {
      setError(parseApiError(e, 'Erro ao carregar anexos'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entityBase]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    setError('');
    try {
      const data = new FormData();
      data.append('file', file);
      await api.post(`${entityBase}/anexos`, data, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      await load();
      onChange?.();
    } catch (e) {
      setError(parseApiError(e, 'Erro ao enviar anexo'));
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  const handleDownload = async (anexo: AnexoOut) => {
    try {
      const res = await api.get(`${anexoBase}/anexos/${anexo.id}`, { responseType: 'blob' });
      const url = URL.createObjectURL(res.data as Blob);
      window.open(url, '_blank', 'noopener');
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (e) {
      setError(parseApiError(e, 'Erro ao abrir anexo'));
    }
  };

  const handleDelete = async (anexo: AnexoOut) => {
    if (!confirm(`Excluir o anexo "${anexo.filename}"?`)) return;
    try {
      await api.delete(`${anexoBase}/anexos/${anexo.id}`);
      await load();
      onChange?.();
    } catch (e) {
      setError(parseApiError(e, 'Erro ao excluir anexo'));
    }
  };

  return (
    <div className="anexo-uploader">
      <div className="anexo-head">
        <span className="anexo-title">
          <Paperclip size={16} /> Anexos (PDF e fotos)
        </span>
        <button
          type="button"
          className="btn-secondary btn-sm"
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
        >
          <Paperclip size={16} /> {uploading ? 'Enviando...' : 'Anexar'}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED}
          style={{ display: 'none' }}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void handleUpload(file);
          }}
        />
      </div>

      {error && <p className="anexo-error">{error}</p>}

      {loading ? (
        <p className="text-muted anexo-empty">Carregando anexos...</p>
      ) : anexos.length === 0 ? (
        <p className="text-muted anexo-empty">Nenhum anexo. Anexe a foto da multa ou o PDF do boleto.</p>
      ) : (
        <ul className="anexo-list">
          {anexos.map((a) => (
            <li key={a.id} className="anexo-item">
              <span className="anexo-icon">
                {a.content_type === 'application/pdf' ? (
                  <FileText size={16} />
                ) : (
                  <ImageIcon size={16} />
                )}
              </span>
              <span className="anexo-name" title={a.filename}>
                {a.filename}
              </span>
              <span className="anexo-size text-muted">{formatSize(a.tamanho)}</span>
              <button
                type="button"
                className="icon-btn"
                title="Abrir / baixar"
                aria-label="Abrir anexo"
                onClick={() => void handleDownload(a)}
              >
                <Download size={16} />
              </button>
              <button
                type="button"
                className="icon-btn danger"
                title="Excluir anexo"
                aria-label="Excluir anexo"
                onClick={() => void handleDelete(a)}
              >
                <Trash2 size={16} />
              </button>
            </li>
          ))}
        </ul>
      )}

      <style jsx>{`
        .anexo-uploader {
          border: 1px dashed var(--glass-border);
          border-radius: 10px;
          padding: 12px;
          margin-top: 8px;
        }
        .anexo-head {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
          flex-wrap: wrap;
        }
        .anexo-title {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          font-size: 0.85rem;
          color: var(--text-muted);
        }
        .btn-sm {
          padding: 6px 12px;
          font-size: 0.85rem;
        }
        .anexo-empty {
          margin: 10px 0 2px;
          font-size: 0.85rem;
        }
        .anexo-error {
          color: var(--danger);
          font-size: 0.85rem;
          margin: 8px 0 0;
        }
        .anexo-list {
          list-style: none;
          padding: 0;
          margin: 10px 0 0;
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .anexo-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 6px 8px;
          border-radius: 8px;
          background: var(--glass-bg, rgba(255, 255, 255, 0.03));
        }
        .anexo-icon {
          display: inline-flex;
          color: var(--primary);
        }
        .anexo-name {
          flex: 1;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          font-size: 0.85rem;
        }
        .anexo-size {
          font-size: 0.75rem;
        }
        .icon-btn {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 32px;
          height: 32px;
          border: none;
          border-radius: 8px;
          background: transparent;
          color: var(--text-muted);
          cursor: pointer;
        }
        .icon-btn:hover {
          background: var(--glass-border);
          color: var(--text);
        }
        .icon-btn.danger:hover {
          color: var(--danger);
        }
      `}</style>
    </div>
  );
};

export default AnexoUploader;
