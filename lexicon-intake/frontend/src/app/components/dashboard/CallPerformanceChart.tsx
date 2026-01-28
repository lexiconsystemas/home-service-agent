import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { useCallPerformance } from '../../../hooks/useDashboard';
import { ChartSkeleton } from '../../../components/ui/Skeleton';
import { ErrorDisplay } from '../../../components/ui/ErrorDisplay';

const CallPerformanceChart: React.FC = () => {
  const { data: performanceData, isLoading, error, refetch } = useCallPerformance();

  if (isLoading) {
    return <ChartSkeleton />;
  }

  if (error || !performanceData?.success) {
    return (
      <ErrorDisplay
        message="Failed to load call performance data"
        onRetry={() => refetch()}
      />
    );
  }

  // Transform API data to chart format
  const chartData = performanceData.data.call_volume.map(item => ({
    date: new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    calls: item.call_count,
  }));

  const totalCalls = chartData.reduce((sum, item) => sum + item.calls, 0);
  const avgDailyCalls = Math.round(totalCalls / chartData.length);
  const peakDayCalls = Math.max(...chartData.map(item => item.calls));

  return (
    <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-gray-900">Daily Call Volume</h3>
        <p className="text-sm text-gray-500 mt-1">Track your call activity over the past {performanceData.data.period_days} days</p>
      </div>
      
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 12 }} />
          <YAxis tick={{ fill: '#6b7280', fontSize: 12 }} />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: '#fff', 
              border: '1px solid #e5e7eb', 
              borderRadius: '8px',
              fontSize: '14px'
            }} 
          />
          <Legend 
            wrapperStyle={{ fontSize: '14px', paddingTop: '20px' }}
            iconType="circle"
          />
          <Bar dataKey="calls" fill="#10b981" name="Calls" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
      
      <div className="mt-6 grid grid-cols-3 gap-4 pt-4 border-t border-gray-100">
        <div>
          <p className="text-sm text-gray-600">Total Calls</p>
          <p className="text-2xl font-semibold text-gray-900 mt-1">{totalCalls}</p>
        </div>
        <div>
          <p className="text-sm text-gray-600">Avg. Daily Calls</p>
          <p className="text-2xl font-semibold text-gray-900 mt-1">{avgDailyCalls}</p>
        </div>
        <div>
          <p className="text-sm text-gray-600">Peak Day</p>
          <p className="text-2xl font-semibold text-gray-900 mt-1">{peakDayCalls}</p>
        </div>
      </div>
    </div>
  );
};

export default CallPerformanceChart;
