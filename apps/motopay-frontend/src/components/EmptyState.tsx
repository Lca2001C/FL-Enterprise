import type { ReactNode } from 'react';

type EmptyStateProps = {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
};

const EmptyState = ({ icon, title, description, action }: EmptyStateProps) => (
  <div className="empty-state">
    {icon && <div className="empty-icon">{icon}</div>}
    <h3>{title}</h3>
    {description && <p className="text-muted">{description}</p>}
    {action && <div className="empty-action">{action}</div>}
    <style jsx>{`
      .empty-state {
        text-align: center;
        padding: 48px 24px;
      }
      .empty-icon {
        margin-bottom: 16px;
        color: var(--text-muted);
        display: flex;
        justify-content: center;
      }
      .empty-state h3 {
        font-size: 1.1rem;
        margin-bottom: 8px;
      }
      .empty-action {
        margin-top: 20px;
      }
    `}</style>
  </div>
);

export default EmptyState;
