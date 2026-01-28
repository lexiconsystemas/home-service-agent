import { Users, PhoneCall, Calendar, CheckCircle } from 'lucide-react';

const funnelSteps = [
  { 
    label: 'People Who Called', 
    value: 247, 
    percentage: 100,
    icon: PhoneCall,
    color: 'bg-blue-500',
    description: 'Total incoming calls'
  },
  { 
    label: 'Calls Answered', 
    value: 224, 
    percentage: 91,
    icon: Users,
    color: 'bg-indigo-500',
    description: 'Successfully connected'
  },
  { 
    label: 'Appointments Set', 
    value: 178, 
    percentage: 72,
    icon: Calendar,
    color: 'bg-purple-500',
    description: 'Scheduled for service'
  },
  { 
    label: 'Jobs Completed', 
    value: 156, 
    percentage: 63,
    icon: CheckCircle,
    color: 'bg-green-500',
    description: 'Confirmed jobs done'
  },
];

export function ConversionFunnel() {
  return (
    <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-gray-900">Lead Conversion Journey</h3>
        <p className="text-sm text-gray-500 mt-1">From first call to completed job</p>
      </div>
      
      <div className="space-y-4">
        {funnelSteps.map((step, index) => {
          const Icon = step.icon;
          return (
            <div key={step.label} className="relative">
              <div className="flex items-center gap-4">
                <div className={`${step.color} p-3 rounded-lg`}>
                  <Icon className="w-5 h-5 text-white" />
                </div>
                
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{step.label}</p>
                      <p className="text-xs text-gray-500">{step.description}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xl font-semibold text-gray-900">{step.value}</p>
                      <p className="text-xs text-gray-500">{step.percentage}%</p>
                    </div>
                  </div>
                  
                  <div className="relative w-full bg-gray-100 rounded-full h-2.5 overflow-hidden">
                    <div 
                      className={`absolute top-0 left-0 h-full ${step.color} rounded-full transition-all`}
                      style={{ width: `${step.percentage}%` }}
                    ></div>
                  </div>
                </div>
              </div>
              
              {index < funnelSteps.length - 1 && (
                <div className="ml-7 mt-2 mb-2 h-6 w-0.5 bg-gray-200"></div>
              )}
            </div>
          );
        })}
      </div>
      
      <div className="mt-6 p-4 bg-green-50 rounded-lg border border-green-100">
        <p className="text-sm text-gray-700">
          <span className="font-semibold text-green-700">Great work!</span> You're converting 63% of your calls into completed jobs.
        </p>
      </div>
    </div>
  );
}
