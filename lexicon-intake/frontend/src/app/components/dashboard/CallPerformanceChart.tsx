import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

const data = [
  { date: 'Jan 20', calls: 12 },
  { date: 'Jan 21', calls: 15 },
  { date: 'Jan 22', calls: 9 },
  { date: 'Jan 23', calls: 18 },
  { date: 'Jan 24', calls: 14 },
  { date: 'Jan 25', calls: 11 },
  { date: 'Jan 26', calls: 16 },
];

export function CallPerformanceChart() {
  return (
    <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-gray-900">Daily Call Volume</h3>
        <p className="text-sm text-gray-500 mt-1">Track your call activity over the past week</p>
      </div>
      
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
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
          <p className="text-2xl font-semibold text-gray-900 mt-1">95</p>
        </div>
        <div>
          <p className="text-sm text-gray-600">Avg. Call Duration</p>
          <p className="text-2xl font-semibold text-gray-900 mt-1">4:32</p>
        </div>
        <div>
          <p className="text-sm text-gray-600">Peak Day</p>
          <p className="text-2xl font-semibold text-gray-900 mt-1">Jan 23</p>
        </div>
      </div>
    </div>
  );
}