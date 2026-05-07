'use client';

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { SentimentTrendPoint } from '@/lib/types';

interface SentimentChartProps {
  data: SentimentTrendPoint[];
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div style={{
        background: 'rgba(13, 20, 36, 0.95)',
        border: '1px solid rgba(255,255,255,0.1)',
        borderRadius: '10px',
        padding: '10px 14px',
        fontSize: '12px',
        backdropFilter: 'blur(10px)',
      }}>
        <p style={{ color: '#8892a4', marginBottom: '6px', fontWeight: 600 }}>{label}</p>
        {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */
        payload.map((entry: any) => (
          <div key={entry.name} style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '2px' }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: entry.color, display: 'inline-block' }} />
            <span style={{ color: '#f0f2f8', textTransform: 'capitalize' }}>{entry.name}:</span>
            <span style={{ color: entry.color, fontWeight: 700 }}>{entry.value}</span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export default function SentimentChart({ data }: SentimentChartProps) {
  if (!data.length) {
    return (
      <div className="chart-container">
        <div className="empty-state">
          <div className="empty-icon"></div>
          <p>No trend data yet. Trigger a scrape to see charts!</p>
        </div>
      </div>
    );
  }

  const formatted = data.map((d) => ({
    ...d,
    date: d.date.slice(5), // Show MM-DD
  }));

  return (
    <div className="chart-container">
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={formatted} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="colorPositive" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="colorNegative" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#f43f5e" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="colorNeutral" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.25} />
              <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis dataKey="date" tick={{ fill: '#8892a4', fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: '#8892a4', fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ fontSize: '12px', paddingTop: '12px' }}
            formatter={(v) => <span style={{ color: '#8892a4', textTransform: 'capitalize' }}>{v}</span>}
          />
          <Area type="monotone" dataKey="positive" stroke="#22c55e" strokeWidth={2} fill="url(#colorPositive)" />
          <Area type="monotone" dataKey="negative" stroke="#f43f5e" strokeWidth={2} fill="url(#colorNegative)" />
          <Area type="monotone" dataKey="neutral" stroke="#f59e0b" strokeWidth={2} fill="url(#colorNeutral)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
