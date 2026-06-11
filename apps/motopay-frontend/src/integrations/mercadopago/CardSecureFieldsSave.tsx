import { memo, useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import {
  CardNumber,
  createCardToken,
  ExpirationDate,
  SecurityCode,
} from '@mercadopago/sdk-react';
import { getMercadoPagoSdkPublicKey, subscribeMercadoPagoSdkReady } from './init';

type Payer = {
  email: string;
  identification: { type: string; number: string };
};

type Props = {
  payer: Payer;
  onToken: (token: string) => void | Promise<void>;
  onFieldError?: (message: string) => void;
};

function isEdgeBrowser(): boolean {
  if (typeof navigator === 'undefined') return false;
  return /Edg\//.test(navigator.userAgent);
}

function CardSecureFieldsSaveInner({ payer, onToken, onFieldError }: Props) {
  const [sdkReady, setSdkReady] = useState(() => getMercadoPagoSdkPublicKey());
  const [fieldsMount, setFieldsMount] = useState(false);
  const [cardholderName, setCardholderName] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [fieldsReady, setFieldsReady] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);
  const onTokenRef = useRef(onToken);
  const onFieldErrorRef = useRef(onFieldError);
  onTokenRef.current = onToken;
  onFieldErrorRef.current = onFieldError;

  useEffect(() => subscribeMercadoPagoSdkReady(() => setSdkReady(true)), []);

  useEffect(() => {
    if (!sdkReady) return;
    const frame = requestAnimationFrame(() => setFieldsMount(true));
    return () => cancelAnimationFrame(frame);
  }, [sdkReady]);

  useEffect(() => {
    if (!fieldsMount) return;
    const timer = window.setTimeout(() => {
      const iframeCount = formRef.current?.querySelectorAll('iframe').length ?? 0;
      if (iframeCount >= 3) {
        setFieldsReady(true);
        onFieldErrorRef.current?.('');
      } else if (iframeCount === 0) {
        const edgeHint = isEdgeBrowser()
          ? ' No Edge: adicione este site às exceções de rastreamento ou use Chrome.'
          : '';
        onFieldErrorRef.current?.(`Os campos do cartão não carregaram.${edgeHint}`);
      }
    }, 5000);
    return () => window.clearTimeout(timer);
  }, [fieldsMount, payer.email]);

  const handleSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      if (!cardholderName.trim()) {
        onFieldErrorRef.current?.('Informe o nome impresso no cartão.');
        return;
      }
      setSubmitting(true);
      onFieldErrorRef.current?.('');
      try {
        const result = await createCardToken({
          cardholderName: cardholderName.trim(),
          identificationType: payer.identification.type,
          identificationNumber: payer.identification.number.replace(/\D/g, ''),
        });
        const token = String(
          (result as { id?: string; token?: string }).id ??
            (result as { token?: string }).token ??
            ''
        );
        if (!token) {
          throw new Error('Token do cartão não foi gerado');
        }
        await onTokenRef.current(token);
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Erro ao tokenizar cartão';
        onFieldErrorRef.current?.(msg);
      } finally {
        setSubmitting(false);
      }
    },
    [cardholderName, payer.identification.number, payer.identification.type]
  );

  if (!sdkReady || !fieldsMount) {
    return <p className="text-muted mp-brick-status">Carregando Mercado Pago…</p>;
  }

  return (
    <form
      ref={formRef}
      className="mp-secure-fields-form"
      onSubmit={(e) => void handleSubmit(e)}
    >
      {isEdgeBrowser() && !fieldsReady && (
        <p className="text-muted mp-secure-fields-hint">
          Se os campos do cartão não aparecerem, permita rastreamento para este site no Edge ou
          use Chrome.
        </p>
      )}
      {fieldsReady && (
        <p className="mp-secure-fields-hint mp-secure-fields-hint--success">
          Campos do cartão prontos. Preencha e clique em Salvar cartão.
        </p>
      )}
      <div className="input-group">
        <label className="input-label" htmlFor="mp-cardholder">
          Nome no cartão
        </label>
        <input
          id="mp-cardholder"
          className="input-field"
          value={cardholderName}
          onChange={(e) => setCardholderName(e.target.value)}
          autoComplete="cc-name"
          required
        />
      </div>
      <div className="input-group">
        <label className="input-label">Número do cartão</label>
        <div className="mp-secure-field">
          <CardNumber placeholder="0000 0000 0000 0000" />
        </div>
      </div>
      <div className="mp-secure-fields-row">
        <div className="input-group">
          <label className="input-label">Validade</label>
          <div className="mp-secure-field">
            <ExpirationDate placeholder="MM/AA" />
          </div>
        </div>
        <div className="input-group">
          <label className="input-label">CVV</label>
          <div className="mp-secure-field">
            <SecurityCode placeholder="123" />
          </div>
        </div>
      </div>
      <button type="submit" className="btn-primary" disabled={submitting}>
        {submitting ? 'Salvando…' : 'Salvar cartão'}
      </button>
    </form>
  );
}

const CardSecureFieldsSave = memo(CardSecureFieldsSaveInner);
export default CardSecureFieldsSave;
