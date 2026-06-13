// Shared types across the frontend
export interface Review {
  id: number;
  source: string;
  product: string;
  author: string;
  text: string;
  rating: number | null;
  scraped_at: string;
  sentiment: 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL' | null;
  sentiment_score: number | null;
  topics: string | null;
  is_fake: boolean | null;
  fake_confidence: number | null;
  summary: string | null;
  images: string | null;   // JSON list of image URLs
}

export interface Stats {
  total: number;
  positive: number;
  negative: number;
  neutral: number;
  fake_count: number;
  fake_percent: number;
  avg_sentiment_score: number;
  avg_rating: number;
}

export interface SentimentTrendPoint {
  date: string;
  positive: number;
  negative: number;
  neutral: number;
}

export interface TopicCount {
  topic: string;
  count: number;
}

export interface Alert {
  id: number;
  text: string;
  sentiment: string;
  is_fake: boolean;
  source: string;
  product: string;
  scraped_at: string;
}

// Dynamic API base — works on Mac (localhost) and Android (network IP) automatically
function getApiBase(): string {
  // During SSR (no window), fall back to env or localhost
  if (typeof window === 'undefined') {
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  }
  // On the browser: use same hostname as the page, but port 8000
  const host = window.location.hostname;
  return `http://${host}:8000`;
}

export const API_BASE = getApiBase();
export const WS_BASE = API_BASE.replace('http', 'ws');
