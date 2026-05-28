import { useEffect, useState } from 'react';
import { Bike } from 'lucide-react';
import type { AxiosInstance } from 'axios';

type Props = {
  api: AxiosInstance;
  motoId: number;
  temImagem: boolean;
  size?: number;
  refreshKey?: number;
};

const MotoThumbnail = ({ api, motoId, temImagem, size = 48, refreshKey = 0 }: Props) => {
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!temImagem) {
      setSrc(null);
      setFailed(false);
      return;
    }

    let objectUrl: string | null = null;
    let cancelled = false;

    const load = async () => {
      try {
        const response = await api.get(`/api/v1/motos/${motoId}/imagem`, {
          responseType: 'blob',
        });
        if (cancelled) return;
        objectUrl = URL.createObjectURL(response.data);
        setSrc(objectUrl);
        setFailed(false);
      } catch {
        if (!cancelled) {
          setSrc(null);
          setFailed(true);
        }
      }
    };

    void load();

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [api, motoId, temImagem, refreshKey]);

  const dimension = `${size}px`;

  if (src && !failed) {
    return (
      <img
        src={src}
        alt=""
        className="moto-thumbnail"
        style={{ width: dimension, height: dimension }}
      />
    );
  }

  return (
    <span
      className="moto-thumbnail moto-thumbnail-placeholder"
      style={{ width: dimension, height: dimension }}
      aria-hidden
    >
      <Bike size={Math.max(16, size * 0.45)} />
    </span>
  );
};

export default MotoThumbnail;
