import { Component, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  height?: number;
}

interface State {
  hasError: boolean;
}

export class ErrorBoundary3D extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            height: this.props.height ?? 280,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: '#0a1628',
            borderRadius: '0.75rem',
            color: '#475569',
            gap: '0.5rem',
            fontSize: '0.8rem',
            fontFamily: 'Manrope, sans-serif',
          }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <rect x="2" y="7" width="20" height="14" rx="2" />
            <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
            <line x1="12" y1="12" x2="12" y2="16" />
            <line x1="12" y1="18.5" x2="12.01" y2="18.5" strokeLinecap="round" strokeWidth="2" />
          </svg>
          3D view unavailable
        </div>
      );
    }
    return this.props.children;
  }
}
