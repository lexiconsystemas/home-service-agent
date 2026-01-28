import { Zap, AlertCircle, DollarSign, Clock } from 'lucide-react';
import { Badge } from '@/app/components/ui/badge';

const aiSummaries = [
  {
    id: 1,
    caller: 'Sarah Mitchell',
    summary: 'Customer reported AC unit not cooling. Needs immediate repair. Lives in a 2-story home, system is 8 years old. Willing to pay for emergency service.',
    tags: ['Emergency', 'HVAC', 'High Priority'],
    tagColors: ['bg-red-100 text-red-700', 'bg-blue-100 text-blue-700', 'bg-orange-100 text-orange-700'],
    time: '2 hours ago',
  },
  {
    id: 2,
    caller: 'Mike Johnson',
    summary: 'Inquired about water heater replacement costs. Current unit is 12 years old and making noise. Asked for quote and available dates next week.',
    tags: ['Price Check', 'Plumbing', 'Follow-up Needed'],
    tagColors: ['bg-purple-100 text-purple-700', 'bg-blue-100 text-blue-700', 'bg-yellow-100 text-yellow-700'],
    time: '3 hours ago',
  },
  {
    id: 3,
    caller: 'Jennifer Lee',
    summary: 'Kitchen outlet stopped working suddenly. Concerned about electrical safety. Has small children in the home. Wants same-day or next-day service.',
    tags: ['Emergency', 'Electrical', 'Safety Issue'],
    tagColors: ['bg-red-100 text-red-700', 'bg-blue-100 text-blue-700', 'bg-red-100 text-red-700'],
    time: '5 hours ago',
  },
  {
    id: 4,
    caller: 'David Brown',
    summary: 'Roof leak discovered after recent storm. Water damage visible in ceiling. Needs inspection and repair estimate. Insurance claim likely.',
    tags: ['Weather Related', 'Roofing', 'Insurance Work'],
    tagColors: ['bg-gray-100 text-gray-700', 'bg-blue-100 text-blue-700', 'bg-green-100 text-green-700'],
    time: '7 hours ago',
  },
];

export function AISummaryPanel() {
  return (
    <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
      <div className="flex items-center gap-2 mb-6">
        <Zap className="w-5 h-5 text-purple-600" />
        <h3 className="text-lg font-semibold text-gray-900">AI Call Summaries</h3>
      </div>
      
      <p className="text-sm text-gray-500 mb-6">
        Automatically generated summaries of recent customer calls to help you quickly understand what callers need.
      </p>
      
      <div className="space-y-4">
        {aiSummaries.map((item) => (
          <div key={item.id} className="p-4 border border-gray-200 rounded-lg hover:border-gray-300 transition-colors">
            <div className="flex items-start justify-between mb-3">
              <div>
                <p className="text-sm font-medium text-gray-900">{item.caller}</p>
                <p className="text-xs text-gray-500 mt-1">{item.time}</p>
              </div>
            </div>
            
            <p className="text-sm text-gray-700 mb-3 leading-relaxed">{item.summary}</p>
            
            <div className="flex flex-wrap gap-2">
              {item.tags.map((tag, index) => (
                <Badge 
                  key={tag} 
                  variant="outline" 
                  className={item.tagColors[index]}
                >
                  {tag}
                </Badge>
              ))}
            </div>
          </div>
        ))}
      </div>
      
      <div className="mt-6 p-4 bg-purple-50 rounded-lg border border-purple-100">
        <div className="flex gap-3">
          <AlertCircle className="w-5 h-5 text-purple-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-purple-900">AI Insights Tip</p>
            <p className="text-sm text-purple-700 mt-1">
              3 calls today mentioned "emergency" - consider adjusting your availability for urgent requests.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
