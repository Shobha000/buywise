'use client';

import { Alert } from '@/lib/types';

interface AlertPanelProps {
  alerts: Alert[];
}

export default function AlertPanel({ alerts }: AlertPanelProps) {
  if (!alerts.length) {
    return (
      <div className="empty-state">
        <div className="empty-icon"></div>
        <p>No alerts. All reviews look healthy!</p>
      </div>
    );
  }

  return (
    <div className="alert-list">
      {alerts.map((a) => (
        <div key={a.id} className={`alert-item ${a.is_fake ? 'fake-alert' : ''}`}>
          <div className="alert-icon">
            {a.is_fake ? '️' : ''}
          </div>
          <div className="alert-body">
            <div className="alert-title">
              {a.is_fake ? 'Suspicious Review Detected' : 'Negative Review Alert'}
              <span style={{
                marginLeft: 8,
                fontSize: '10px',
                color: '#4a5568',
                fontWeight: 400,
              }}>
                {a.source} · {a.product}
              </span>
            </div>
            <div className="alert-text">{a.text}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
