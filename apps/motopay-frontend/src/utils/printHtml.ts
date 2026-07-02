/**
 * Imprime um documento HTML auto-contido em um iframe isolado.
 *
 * O iframe tem seu próprio contexto de layout: o navegador pagina a tabela
 * normalmente (thead repetido por página, sem sobreposição), sem depender de
 * hacks de visibility/position sobre o DOM do app — a causa do PDF corrompido
 * nas páginas 2+.
 */
export function printHtmlDocument(html: string): void {
  const iframe = document.createElement('iframe');
  iframe.setAttribute('aria-hidden', 'true');
  iframe.style.position = 'fixed';
  iframe.style.right = '0';
  iframe.style.bottom = '0';
  iframe.style.width = '0';
  iframe.style.height = '0';
  iframe.style.border = '0';
  document.body.appendChild(iframe);

  const cleanup = () => {
    // Adia a remoção: alguns navegadores cancelam a impressão se o iframe
    // sair do DOM antes do diálogo fechar.
    window.setTimeout(() => {
      if (iframe.parentNode) iframe.parentNode.removeChild(iframe);
    }, 1000);
  };

  const doc = iframe.contentWindow?.document;
  if (!doc) {
    cleanup();
    return;
  }
  doc.open();
  doc.write(html);
  doc.close();

  const win = iframe.contentWindow;
  if (!win) {
    cleanup();
    return;
  }
  win.onafterprint = cleanup;

  // Espera o layout do iframe estabilizar antes de abrir o diálogo.
  window.setTimeout(() => {
    try {
      win.focus();
      win.print();
    } finally {
      // onafterprint não dispara em todos os navegadores — garante a limpeza.
      window.setTimeout(cleanup, 60_000);
    }
  }, 150);
}
