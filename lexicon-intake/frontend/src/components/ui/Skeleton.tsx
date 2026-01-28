import React from 'react';

interface SkeletonProps {
  className?: string;
  variant?: 'default' | 'text' | 'circular' | 'rectangular';
  width?: string | number;
  height?: string | number;
  lines?: number;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className = '',
  variant = 'default',
  width,
  height,
  lines = 1,
}) => {
  const baseClasses = 'animate-pulse bg-gray-200 rounded';
  
  const variantClasses = {
    default: 'rounded',
    text: 'rounded h-4',
    circular: 'rounded-full',
    rectangular: 'rounded-md',
  };

  const style: React.CSSProperties = {};
  if (width) style.width = width;
  if (height) style.height = height;

  if (variant === 'text' && lines > 1) {
    return (
      <div className={`space-y-2 ${className}`}>
        {Array.from({ length: lines }, (_, i) => (
          <div
            key={i}
            className={`${baseClasses} ${variantClasses.text}`}
            style={{
              ...style,
              width: i === lines - 1 ? '70%' : '100%', // Last line shorter
            }}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      className={`${baseClasses} ${variantClasses[variant]} ${className}`}
      style={style}
    />
  );
};

// Card skeleton for dashboard components
export const CardSkeleton: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`bg-white rounded-lg p-6 shadow-sm ${className}`}>
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Skeleton variant="text" width="40%" />
        <Skeleton variant="circular" width={24} height={24} />
      </div>
      <Skeleton variant="text" width="60%" height={32} />
      <Skeleton variant="text" width="30%" />
    </div>
  </div>
);

// Table skeleton for call logs
export const TableSkeleton: React.FC<{ rows?: number; className?: string }> = ({ 
  rows = 5, 
  className = '' 
}) => (
  <div className={`bg-white rounded-lg shadow-sm overflow-hidden ${className}`}>
    <div className="px-6 py-4 border-b border-gray-200">
      <Skeleton variant="text" width="30%" />
    </div>
    <div className="divide-y divide-gray-200">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="px-6 py-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Skeleton variant="text" />
            <Skeleton variant="text" />
            <Skeleton variant="text" />
            <Skeleton variant="text" />
          </div>
        </div>
      ))}
    </div>
  </div>
);

// Chart skeleton
export const ChartSkeleton: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`bg-white rounded-lg p-6 shadow-sm ${className}`}>
    <div className="space-y-4">
      <Skeleton variant="text" width="30%" />
      <div className="h-64">
        <Skeleton variant="rectangular" height="100%" />
      </div>
    </div>
  </div>
);
