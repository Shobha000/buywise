'use client';

import { useState } from 'react';

interface SearchBarProps {
  onSearch: (product: string, sources: string[]) => void;
  isSearching: boolean;
  searchStatus: Record<string, string>;
}

export default function SearchBar({ onSearch, isSearching }: SearchBarProps) {
  const [product, setProduct] = useState('');
  const [focused, setFocused] = useState(false);
  const allSources = ['amazon', 'flipkart', 'trustpilot', 'g2'];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!product.trim() || isSearching) return;
    onSearch(product.trim(), allSources);
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        background: focused ? 'var(--bg-raised)' : 'var(--bg-surface)',
        border: `1px solid ${focused ? 'var(--border-warm)' : 'var(--border)'}`,
        borderRadius: '12px',
        padding: '0 14px',
        transition: 'all 0.2s',
        boxShadow: focused ? '0 0 0 3px var(--amber-soft)' : 'none',
      }}>
        <span style={{ fontSize: '15px', flexShrink: 0, opacity: 0.5 }}>🔍</span>
        <input
          id="search-input"
          type="text"
          value={product}
          onChange={(e) => setProduct(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder="Search any product…"
          disabled={isSearching}
          style={{
            flex: 1,
            padding: '11px 0',
            background: 'transparent',
            border: 'none',
            color: 'var(--cream)',
            fontSize: '14px',
            outline: 'none',
            fontFamily: 'Inter, sans-serif',
          }}
        />
        {isSearching && (
          <div className="spinner" style={{ width: '16px', height: '16px', borderWidth: '2px', borderTopColor: 'var(--amber)', borderColor: 'rgba(255,255,255,0.1)', flexShrink: 0 }} />
        )}
      </div>

      <button
        type="submit"
        className="btn-primary"
        disabled={isSearching || !product.trim()}
        style={{ width: '100%', justifyContent: 'center' }}
      >
        {isSearching ? (
          <>Searching across Amazon & Flipkart…</>
        ) : (
          <>🚀 Analyse Reviews</>
        )}
      </button>
    </form>
  );
}
