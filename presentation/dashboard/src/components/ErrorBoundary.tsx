import { Component, ReactNode } from 'react';

/* ------------------------------------------------------------------ */
/*  Fallback UI for page-level errors                                  */
/* ------------------------------------------------------------------ */

export function PageErrorFallback({
  error,
  onReset,
}: {
  error: Error;
  onReset: () => void;
}) {
  return (
    <div className="flex flex-1 items-center justify-center p-8">
      <div className="max-w-md rounded-lg border border-red-200 bg-white p-6 shadow-sm">
        <h2 className="mb-2 text-lg font-semibold text-red-700">
          Something went wrong
        </h2>
        <p className="mb-4 text-sm text-gray-600">
          An unexpected error occurred while rendering this page. You can try
          again or navigate to a different section.
        </p>
        <pre className="mb-4 max-h-32 overflow-auto rounded bg-red-50 p-3 text-xs text-red-800">
          {error.message}
        </pre>
        <div className="flex gap-3">
          <button
            onClick={onReset}
            className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
          >
            Try Again
          </button>
          <button
            onClick={() => window.location.reload()}
            className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Reload Page
          </button>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Full-screen fallback for catastrophic (root-level) errors          */
/* ------------------------------------------------------------------ */

function RootErrorFallback({
  error,
  onReset,
}: {
  error: Error;
  onReset: () => void;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-8">
      <div className="max-w-lg rounded-lg border border-red-200 bg-white p-8 shadow-md">
        <h1 className="mb-2 text-xl font-bold text-red-700">
          Application Error
        </h1>
        <p className="mb-4 text-sm text-gray-600">
          A critical error prevented the application from rendering. Please
          reload the page or contact support if the problem persists.
        </p>
        <pre className="mb-4 max-h-40 overflow-auto rounded bg-red-50 p-3 text-xs text-red-800">
          {error.message}
        </pre>
        <div className="flex gap-3">
          <button
            onClick={onReset}
            className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
          >
            Try Again
          </button>
          <button
            onClick={() => window.location.reload()}
            className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Reload Page
          </button>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  ErrorBoundary — class component (required by React)                */
/* ------------------------------------------------------------------ */

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Custom fallback renderer. Receives the error and a reset callback. */
  fallback?: (error: Error, reset: () => void) => ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[ErrorBoundary] Caught error:', error, info.componentStack);
  }

  resetError = () => {
    this.setState({ error: null });
  };

  render() {
    const { error } = this.state;
    if (error) {
      if (this.props.fallback) {
        return this.props.fallback(error, this.resetError);
      }
      return <RootErrorFallback error={error} onReset={this.resetError} />;
    }
    return this.props.children;
  }
}
