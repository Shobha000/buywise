'use client';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { TopicCount } from '@/lib/types';

interface TopicsChartProps {
  data: TopicCount[];
}

const COLORS = [
  '#6c63ff', '#00d4ff', '#22c55e', '#f59e0b', '#f43f5e',
  '#8b5cf6', '#06b6d4', '#10b981', '#eab308', '#ef4444',
];

const CustomTooltip = ({ active, payload }: any) => {
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
        <p style={{ color: '#f0f2f8', fontWeight: 700, marginBottom: '2px', textTransform: 'capitalize' }}>
          {payload[0]?.payload?.topic}
        </p>
        <p style={{ color: '#6c63ff', fontWeight: 700 }}>{payload[0]?.value} reviews</p>
      </div>
    );
  }
  return null;
};

export default function TopicsChart({ data }: TopicsChartProps) {
  if (!data.length) {
    return (
      <div className="chart-container">
        <div className="empty-state">
          <div className="empty-icon">️</div>
          <p>No topics extracted yet.</p>
        </div>
      </div>
    );
  }

  const top10 = data.slice(0, 10);

  return (
    <div className="chart-container">
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={top10} layout="vertical" margin={{ top: 0, right: 20, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
          <XAxis type="number" tick={{ fill: '#8892a4', fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis
            type="category"
            dataKey="topic"
            tick={{ fill: '#8892a4', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={70}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="count" radius={[0, 6, 6, 0]}>
            {top10.map((_, idx) => (
              <Cell key={idx} fill={COLORS[idx % COLORS.length]} fillOpacity={0.85} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
