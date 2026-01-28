import { ArrowUpRight, ArrowDownRight } from 'lucide-react';

const serviceRevenue = [
  { service: 'HVAC Repair', revenue: 15420, percentage: 36, change: 12 },
  { service: 'Plumbing', revenue: 12350, percentage: 29, change: 8 },
  { service: 'Electrical', revenue: 9680, percentage: 23, change: -3 },
  { service: 'Roofing', revenue: 5400, percentage: 12, change: 18 },
];

export function RevenueInsights() {
  return (
    <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-gray-900">Revenue Insights</h3>
        <p className="text-sm text-gray-500 mt-1">Breakdown by service type</p>
      </div>
      
      <div className="mb-6 p-4 bg-gradient-to-r from-emerald-50 to-green-50 rounded-lg border border-emerald-100">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-600">This Month</p>
            <p className="text-3xl font-semibold text-gray-900 mt-1">$42,850</p>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-600">Last Month</p>
            <p className="text-2xl font-semibold text-gray-700 mt-1">$37,200</p>
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
                  {Math.abs(item.change)}%
                </span>
              </div>
            </div>
            <div className="relative w-full bg-gray-100 rounded-full h-2 overflow-hidden">
              <div 
                className="absolute top-0 left-0 h-full bg-emerald-500 rounded-full transition-all"
                style={{ width: `${item.percentage}%` }}
              ></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
