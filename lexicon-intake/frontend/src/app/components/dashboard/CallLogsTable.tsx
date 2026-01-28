import { Phone, Clock, Eye } from 'lucide-react';
import { Badge } from '@/app/components/ui/badge';

const callLogs = [
  {
    id: 1,
    caller: 'Sarah Mitchell',
    phone: '(555) 234-5678',
    outcome: 'Booked',
    duration: '5:23',
    preview: 'Needs urgent HVAC repair, system not cooling properly...',
    time: '2 hours ago',
  },
  {
    id: 2,
    caller: 'Mike Johnson',
    phone: '(555) 987-6543',
    outcome: 'Follow-up',
    duration: '3:45',
    preview: 'Asked about pricing for water heater installation...',
    time: '3 hours ago',
  },
  {
    id: 3,
    caller: 'Jennifer Lee',
    phone: '(555) 456-7890',
    outcome: 'Booked',
    duration: '6:12',
    preview: 'Electrical outlet not working in kitchen, safety concern...',
    time: '5 hours ago',
  },
  {
    id: 4,
    caller: 'David Brown',
    phone: '(555) 654-3210',
    outcome: 'Booked',
    duration: '4:56',
    preview: 'Roof leak after recent storm, needs inspection...',
    time: '6 hours ago',
  },
  {
    id: 5,
    caller: 'Amanda White',
    phone: '(555) 789-0123',
    outcome: 'Booked',
    duration: '7:34',
    preview: 'Installing new thermostat, discussed smart home options...',
    time: '7 hours ago',
  },
  {
    id: 6,
    caller: 'Robert Garcia',
    phone: '(555) 111-2222',
    outcome: 'Follow-up',
    duration: '2:18',
    preview: 'General inquiry about maintenance packages...',
    time: '1 day ago',
  },
];

const outcomeStyles = {
  Booked: 'bg-green-100 text-green-700 border-green-200',
  'Follow-up': 'bg-yellow-100 text-yellow-700 border-yellow-200',
};

export function CallLogsTable() {
  return (
    <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Recent Call Activity</h3>
          <p className="text-sm text-gray-500 mt-1">Latest customer interactions and outcomes</p>
        </div>
        <button className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
          View All Calls
        </button>
      </div>
      
      <div className="overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Caller</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Outcome</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Duration</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Call Preview</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Time</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Action</th>
            </tr>
          </thead>
          <tbody>
            {callLogs.map((log) => (
              <tr key={log.id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                <td className="py-4 px-4">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{log.caller}</p>
                    <p className="text-xs text-gray-500 flex items-center gap-1 mt-1">
                      <Phone className="w-3 h-3" />
                      {log.phone}
                    </p>
                  </div>
                </td>
                <td className="py-4 px-4">
                  <Badge 
                    variant="outline" 
                    className={outcomeStyles[log.outcome as keyof typeof outcomeStyles]}
                  >
                    {log.outcome}
                  </Badge>
                </td>
                <td className="py-4 px-4">
                  <div className="flex items-center gap-1 text-sm text-gray-600">
                    <Clock className="w-4 h-4" />
                    {log.duration}
                  </div>
                </td>
                <td className="py-4 px-4">
                  <p className="text-sm text-gray-600 max-w-xs truncate">{log.preview}</p>
                </td>
                <td className="py-4 px-4">
                  <p className="text-sm text-gray-500">{log.time}</p>
                </td>
                <td className="py-4 px-4">
                  <button className="flex items-center gap-1 text-sm text-[#1e3a5f] hover:underline">
                    <Eye className="w-4 h-4" />
                    View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}