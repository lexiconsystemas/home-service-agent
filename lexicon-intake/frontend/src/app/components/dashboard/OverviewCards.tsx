import React from 'react';
import { Phone, Calendar, DollarSign, TrendingUp, HelpCircle } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/app/components/ui/tooltip';
import { useMetrics } from '../../../hooks/useDashboard';
import { CardSkeleton } from '../../../components/ui/Skeleton';
import { ErrorDisplay } from '../../../components/ui/ErrorDisplay';

const OverviewCards: React.FC = () => {
  const { data: metricsData, isLoading, error, refetch } = useMetrics();

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <CardSkeleton />
        <CardSkeleton />
        <CardSkeleton />
        <CardSkeleton />
      </div>
    );
  }

  if (error || !metricsData?.success) {
    return (
      <ErrorDisplay
        message="Failed to load overview metrics"
        onRetry={() => refetch()}
        className="col-span-full"
      />
    );
  }

  const metrics = [
    {
      label: 'Total Calls This Month',
      value: metricsData.data.total_calls.toLocaleString(),
      change: '+12%', // TODO: Calculate from previous period
      changeType: 'positive' as const,
      icon: Phone,
      color: 'bg-blue-50',
      iconColor: 'text-blue-600',
      tooltip: 'Total number of incoming calls received this month'
    },
    {
      label: 'Booked Jobs',
      value: metricsData.data.booked_jobs.toLocaleString(),
      change: '+8%', // TODO: Calculate from previous period
      changeType: 'positive' as const,
      icon: Calendar,
      color: 'bg-green-50',
      iconColor: 'text-green-600',
      tooltip: 'Jobs scheduled from customer calls'
    },
    {
      label: 'Estimated Revenue',
      value: `$${metricsData.data.revenue.toLocaleString()}`,
      change: '+15%', // TODO: Calculate from previous period
      changeType: 'positive' as const,
      icon: DollarSign,
      color: 'bg-emerald-50',
      iconColor: 'text-emerald-600',
      tooltip: 'Total estimated revenue from booked jobs'
    },
    {
      label: 'Conversion Rate',
      value: `${metricsData.data.conversion_rate.toFixed(1)}%`,
      change: '+3%', // TODO: Calculate from previous period
      changeType: 'positive' as const,
      icon: TrendingUp,
      color: 'bg-purple-50',
      iconColor: 'text-purple-600',
      tooltip: 'Percentage of calls that turned into booked jobs'
    },
  ];

  return (
    <TooltipProvider>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <div key={metric.label} className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
              <div className="flex items-start justify-between mb-4">
                <div className={`${metric.color} p-3 rounded-lg`}>
                  <Icon className={`w-6 h-6 ${metric.iconColor}`} />
                </div>
                <Tooltip>
                  <TooltipTrigger>
                    <HelpCircle className="w-4 h-4 text-gray-400 hover:text-gray-600 transition-colors" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="text-sm">{metric.tooltip}</p>
                  </TooltipContent>
                </Tooltip>
              </div>
              <div className="space-y-1">
                <div className="text-2xl font-bold text-gray-900">{metric.value}</div>
                <div className="flex items-center space-x-2">
                  <span className={`text-sm font-medium ${
                    metric.changeType === 'positive' ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {metric.change}
                  </span>
                  <span className="text-xs text-gray-500">vs last month</span>
                </div>
              </div>
              <div className="mt-4">
                <div className="text-sm font-medium text-gray-700">{metric.label}</div>
              </div>
            </div>
          );
        })}
      </div>
    </TooltipProvider>
  );
};

export default OverviewCards;
