import { useAuth } from '../AuthContext';

const AdminScopeBanner = () => {
  const { user, operacaoScopeId } = useAuth();
  if (user?.tipo !== 'admin' || operacaoScopeId != null) return null;

  return (
    <div className="admin-scope-banner glass">
      Selecione uma operação no topo da página para ver os dados desta tela.
      <style jsx>{`
        .admin-scope-banner {
          padding: 12px 16px;
          margin-bottom: 16px;
          border-radius: 10px;
          font-size: 0.85rem;
          color: var(--warning);
          border: 1px solid rgba(245, 158, 11, 0.35);
          background: rgba(245, 158, 11, 0.08);
        }
      `}</style>
    </div>
  );
};

export default AdminScopeBanner;
