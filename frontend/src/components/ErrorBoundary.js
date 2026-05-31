import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{
          minHeight: '100vh',
          padding: '24px',
          background: '#f7f7f8',
          color: '#2d333a',
          fontFamily: 'Inter, sans-serif',
        }}>
          <div style={{
            maxWidth: '860px',
            margin: '0 auto',
            background: '#fff',
            border: '1px solid rgba(0,0,0,0.1)',
            borderRadius: '12px',
            padding: '20px',
          }}>
            <h1 style={{ margin: '0 0 12px', fontSize: '20px' }}>页面运行出错</h1>
            <pre style={{
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              fontSize: '13px',
              lineHeight: 1.6,
              color: '#b91c1c',
            }}>
              {String(this.state.error?.stack || this.state.error?.message || this.state.error)}
            </pre>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
