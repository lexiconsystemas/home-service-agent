import { Phone, Calendar, DollarSign, TrendingUp } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/app/components/ui/tooltip';
import { HelpCircle } from 'lucide-react';

const metrics = [
  {
    label: 'Total Calls This Month',
    value: '247',
    change: '+12%',
    changeType: 'positive' as const,
    icon: Phone,
    color: 'bg-blue-50',
    iconColor: 'text-blue-600',
    tooltip: 'Total number of incoming calls received this month'
  },
  {
    label: 'Booked Jobs',
    value: '156',
    change: '+8%',
    changeType: 'positive' as const,
    icon: Calendar,
    color: 'bg-green-50',
    iconColor: 'text-green-600',
    tooltip: 'Jobs scheduled from customer calls'
  },
  {
    label: 'Estimated Revenue',
    value: '$42,850',
    change: '+15%',
    changeType: 'positive' as const,
    icon: DollarSign,
    color: 'bg-emerald-50',
    iconColor: 'text-emerald-600',
    tooltip: 'Total estimated revenue from booked jobs'
  },
  {
    label: 'Conversion Rate',
    value: '63%',
    change: '+3%',
    changeType: 'positive' as const,
    icon: TrendingUp,
    color: 'bg-purple-50',
    iconColor: 'text-purple-600',
    tooltip: 'Percentage of calls that turned into booked jobs'
  },
];

export function OverviewCards() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {metrics.map((metric) => {
        const Icon = metric.icon;
        return (
          <div key={metric.label} className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
            <div className="flex items-start justify-between mb-4">
              <div className={`${metric.color} p-3 rounded-lg`}>
                <Icon className={`w-6 h-6 ${metric.iconColor}`} />
              </div>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger>
                    <HelpCircle className="w-4 h-4 text-gray-400" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="max-w-xs">{metric.tooltip}</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            
            <div>
              <p className="text-sm text-gray-600 mb-1">{metric.label}</p>
              <p className="text-3xl font-semibold text-gray-900">{metric.value}</p>
              <p className={`text-sm mt-2 ${
                metric.changeType === 'positive' ? 'text-green-600' : 'text-red-600'
              }`}>
                {metric.change} vs last month
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}