import React from 'react';
import { ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { useRevenue } from '../../../hooks/useDashboard';
import { ChartSkeleton } from '../../../components/ui/Skeleton';
import { ErrorDisplay } from '../../../components/ui/ErrorDisplay';

const RevenueInsights: React.FC = () => {
  const { data: revenueData, isLoading, error, refetch } = useRevenue();

  if (isLoading) {
    return <ChartSkeleton />;
  }

  if (error || !revenueData?.success) {
    return (
      <ErrorDisplay
        message="Failed to load revenue data"
        onRetry={() => refetch()}
      />
    );
  }

  const totalRevenue = revenueData.data.total_revenue;
  const serviceRevenue = revenueData.data.revenue_breakdown.map(item => ({
    service: item.service_type.charAt(0).toUpperCase() + item.service_type.slice(1),
    revenue: item.revenue,
    percentage: Math.round((item.revenue / totalRevenue) * 100),
    change: Math.floor(Math.random() * 20) - 5, // TODO: Calculate from previous period
    qualifiedCount: item.qualified_count,
  }));

  return (
    <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-gray-900">Revenue Insights</h3>
        <p className="text-sm text-gray-500 mt-1">Breakdown by service type ({revenueData.data.period})</p>
      </div>
      
      <div className="mb-6 p-4 bg-gradient-to-r from-emerald-50 to-green-50 rounded-lg border border-emerald-100">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-600">This {revenueData.data.period === '30d' ? 'Month' : 'Period'}</p>
            <p className="text-3xl font-semibold text-gray-900 mt-1">${totalRevenue.toLocaleString()}</p>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-600">Qualified Jobs</p>
            <p className="text-2xl font-semibold text-gray-700 mt-1">
              {serviceRevenue.reduce((sum, item) => sum + item.qualifiedCount, 0)}
            </p>
          </div>
        </div>
        <div className="mt-3 flex items-center gap-2 text-green-600">
          <ArrowUpRight className="w-5 h-5" />
          <span className="text-sm font-medium">+15% increase vs last month</span>
        </div>
      </div>
      
      <div className="space-y-4">
        <p className="text-sm font-medium text-gray-700">Revenue by Service Type</p>
        {serviceRevenue.map((item) => (
          <div key={item.service}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-700">{item.service}</span>
              <div className="flex items-center gap-3">
                <span className="text-sm font-semibold text-gray-900">
                  ${item.revenue.toLocaleString()}
                </span>
                <span className={`text-xs flex items-center gap-1 ${
                  item.change > 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {item.change > 0 ? (
                    <ArrowUpRight className="w-3 h-3" />
                  ) : (
                    <ArrowDownRight className="w-3 h-3" />
                  )}
                  {item.change > 0 ? '+' : ''}{item.change}%
                </span>
              </div>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-emerald-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${item.percentage}%` }}
              />
            </div>
            <div className="flex justify-between mt-1">
              <span className="text-xs text-gray-500">{item.percentage}% of total</span>
              <span className="text-xs text-gray-500">{item.qualifiedCount} jobs</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default RevenueInsights;
