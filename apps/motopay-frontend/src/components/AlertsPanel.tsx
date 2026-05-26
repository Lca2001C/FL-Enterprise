import React from 'react';
import { useAlerts, type AlertSeverity } from '../stores/AlertContext';
import { AlertCircle, AlertTriangle, Info, X, Check } from 'lucide-react';

const severityIcons: Record<AlertSeverity, React.ReactNode> = {
  critical: <AlertCircle className="w-5 h-5 text-red-500" />,
  warning: <AlertTriangle className="w-5 h-5 text-yellow-500" />,
  info: <Info className="w-5 h-5 text-blue-500" />,
};

const severityColors: Record<AlertSeverity, string> = {
  critical: 'bg-red-50 border-red-200',
  warning: 'bg-yellow-50 border-yellow-200',
  info: 'bg-blue-50 border-blue-200',
};

export const AlertsPanel: React.FC = () => {
  const { alerts, unacknowledgedCount, removeAlert, acknowledgeAlert } = useAlerts();

  if (!alerts.length) {
    return null;
  }

  return (
    <div className="fixed bottom-4 right-4 w-96 max-h-96 overflow-y-auto z-50 space-y-2">
      {alerts.slice(0, 5).map(alert => (
        <div
          key={alert.id}
          className={`border rounded-lg p-3 ${severityColors[alert.severity]} flex items-start gap-3`}
        >
          <div className="flex-shrink-0 mt-1">
            {severityIcons[alert.severity]}
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="font-semibold text-sm text-gray-900">{alert.title}</h4>
            <p className="text-sm text-gray-700 mt-1">{alert.message}</p>
            <time className="text-xs text-gray-500 mt-2 block">
              {new Date(alert.timestamp).toLocaleTimeString()}
            </time>
          </div>
          <div className="flex-shrink-0 flex gap-2">
            {!alert.acknowledged && (
              <button
                onClick={() => acknowledgeAlert(alert.id)}
                className="p-1 hover:bg-black/5 rounded"
                title="Acknowledge"
              >
                <Check className="w-4 h-4 text-gray-500" />
              </button>
            )}
            <button
              onClick={() => removeAlert(alert.id)}
              className="p-1 hover:bg-black/5 rounded"
              title="Dismiss"
            >
              <X className="w-4 h-4 text-gray-500" />
            </button>
          </div>
        </div>
      ))}
      
      {unacknowledgedCount > 5 && (
        <div className="text-xs text-gray-600 px-3">
          +{unacknowledgedCount - 5} more alerts
        </div>
      )}
    </div>
  );
};

export default AlertsPanel;
