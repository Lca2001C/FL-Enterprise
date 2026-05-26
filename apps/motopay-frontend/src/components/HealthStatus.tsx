import React, { useState } from 'react';
import { useHealth, getHealthColor } from '../hooks/useHealth';
import { Loader, ChevronDown } from 'lucide-react';

export const HealthStatus: React.FC = () => {
  const { health, error } = useHealth(30000);
  const [expanded, setExpanded] = useState(false);

  if (error) {
    return (
      <div className="px-4 py-2 bg-red-50 text-red-700 text-sm rounded border border-red-200">
        Health check failed: {error}
      </div>
    );
  }

  if (!health) {
    return (
      <div className="px-4 py-2 flex items-center gap-2 text-sm text-gray-600">
        <Loader className="w-4 h-4 animate-spin" />
        Loading health...
      </div>
    );
  }

  const statusColor = getHealthColor(health.status);

  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 rounded border border-gray-200 hover:bg-gray-50"
      >
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: statusColor }} />
          <span className="font-medium text-sm">Status: {health.status}</span>
        </div>
        <ChevronDown className={`w-4 h-4 transition-transform ${expanded ? 'rotate-180' : ''}`} />
      </button>

      {expanded && (
        <div className="border border-gray-200 rounded p-4 space-y-3">
          <p className="text-sm text-gray-700">{health.overall_message}</p>
          <div className="space-y-2">
            {health.checks.map((check) => (
              <div
                key={check.name}
                className="flex items-center justify-between text-sm p-2 rounded bg-gray-50"
              >
                <span className="font-medium capitalize">{check.name}</span>
                <span className="text-gray-600">{check.duration_ms.toFixed(0)}ms</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default HealthStatus;
