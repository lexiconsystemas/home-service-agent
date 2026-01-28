import React from 'react';
import { Users, PhoneCall, Calendar, CheckCircle } from 'lucide-react';
import { useFunnel } from '../../../hooks/useDashboard';
import { ChartSkeleton } from '../../../components/ui/Skeleton';
import { ErrorDisplay } from '../../../components/ui/ErrorDisplay';

const ConversionFunnel: React.FC = () => {
  const { data: funnelData, isLoading, error, refetch } = useFunnel();

  if (isLoading) {
    return <ChartSkeleton />;
  }

  if (error || !funnelData?.success) {
    return (
      <ErrorDisplay
        message="Failed to load conversion funnel data"
        onRetry={() => refetch()}
      />
    );
  }

  const { funnel, rates } = funnelData.data;

  const funnelSteps = [
    { 
      label: 'People Who Called', 
      value: funnel.calls, 
      percentage: 100,
      icon: PhoneCall,
      color: 'bg-blue-500',
      description: 'Total incoming calls'
    },
    { 
      label: 'Calls Answered', 
      value: funnel.answered, 
      percentage: rates.answer_rate,
      icon: Users,
      color: 'bg-indigo-500',
      description: 'Successfully connected'
    },
    { 
      label: 'Appointments Set', 
      value: funnel.appointments, 
      percentage: rates.appointment_rate,
      icon: Calendar,
      color: 'bg-purple-500',
      description: 'Scheduled for service'
    },
    { 
      label: 'Jobs Completed', 
      value: funnel.completed, 
      percentage: rates.completion_rate,
      icon: CheckCircle,
      color: 'bg-green-500',
      description: 'Successfully completed'
    },
  ];

  return (
    <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-gray-900">Conversion Funnel</h3>
        <p className="text-sm text-gray-500 mt-1">Track your conversion rates through the customer journey ({funnelData.data.period})</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {funnelSteps.map((step, index) => {
          const Icon = step.icon;
          return (
            <div key={step.label} className="relative">
              {/* Connection line */}
              {index < funnelSteps.length - 1 && (
                <div className="absolute top-8 left-full w-full h-0.5 bg-gray-200 hidden lg:block" 
                     style={{ width: 'calc(100% - 2rem)' }} />
              )}
              
              <div className="text-center">
                <div className={`inline-flex items-center justify-center w-16 h-16 rounded-full ${step.color} mb-4 mx-auto`}>
                  <Icon className="w-8 h-8 text-white" />
                </div>
                
                <div className="mb-2">
                  <div className="text-2xl font-bold text-gray-900">{step.value.toLocaleString()}</div>
                  <div className="text-sm text-gray-500">{step.label}</div>
                </div>
                
                <div className="space-y-1">
                  <div className="text-lg font-semibold text-gray-700">{step.percentage.toFixed(1)}%</div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className={`${step.color} h-2 rounded-full transition-all duration-300`}
                      style={{ width: `${step.percentage}%` }}
                    />
                  </div>
                  <div className="text-xs text-gray-500">{step.description}</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
      
      <div className="mt-8 p-4 bg-gray-50 rounded-lg">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div>
            <p className="text-sm text-gray-600">Overall Conversion</p>
            <p className="text-xl font-semibold text-gray-900 mt-1">
              {((funnel.completed / funnel.calls) * 100).toFixed(1)}%
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Answer Rate</p>
            <p className="text-xl font-semibold text-gray-900 mt-1">{rates.answer_rate.toFixed(1)}%</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Appointment Rate</p>
            <p className="text-xl font-semibold text-gray-900 mt-1">{rates.appointment_rate.toFixed(1)}%</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Completion Rate</p>
            <p className="text-xl font-semibold text-gray-900 mt-1">{rates.completion_rate.toFixed(1)}%</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConversionFunnel;
