import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface ErrorDisplayProps {
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorDisplay: React.FC<ErrorDisplayProps> = ({
  message = 'Failed to load data. Please try again.',
  onRetry,
  className = '',
}) => {
  return (
    <div className={`bg-red-50 border border-red-200 rounded-lg p-6 ${className}`}>
      <div className="flex items-center space-x-3">
        <div className="flex-shrink-0">
          <AlertCircle className="h-5 w-5 text-red-400" />
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-medium text-red-800">
            Error
          </h3>
          <div className="mt-2 text-sm text-red-700">
            {message}
          </div>
        </div>
        {onRetry && (
          <div className="flex-shrink-0">
            <button
              onClick={onRetry}
              className="inline-flex items-center px-3 py-2 border border-red-300 shadow-sm text-sm leading-4 font-medium rounded-md text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

// Inline error for smaller components
export const InlineError: React.FC<{ message?: string; onRetry?: () => void }> = ({
  message = 'Failed to load data',
  onRetry,
}) => (
  <div className="flex items-center space-x-2 text-red-600 text-sm">
    <AlertCircle className="h-4 w-4" />
    <span>{message}</span>
    {onRetry && (
      <button
        onClick={onRetry}
        className="text-red-600 hover:text-red-700 underline text-xs"
      >
        Retry
      </button>
    )}
  </div>
);
