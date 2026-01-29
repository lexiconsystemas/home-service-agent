import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Sidebar } from '../components/dashboard/Sidebar';
import Header from '../components/dashboard/Header';
import OverviewCards from '../components/dashboard/OverviewCards';
import CallPerformanceChart from '../components/dashboard/CallPerformanceChart';
import RevenueInsights from '../components/dashboard/RevenueInsights';
import ConversionFunnel from '../components/dashboard/ConversionFunnel';
import CallLogsTable from '../components/dashboard/CallLogsTable';
import AISummaryPanel from '../components/dashboard/AISummaryPanel';

const Dashboard: React.FC = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const { logout } = useAuth();

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      <Sidebar 
        isOpen={isSidebarOpen} 
        isCollapsed={isSidebarCollapsed}
        onClose={() => setIsSidebarOpen(false)}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
      />
      
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header 
          onMenuClick={() => setIsSidebarOpen(true)} 
          onLogout={logout}
        />
        
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-[1600px] mx-auto p-4 lg:p-8 space-y-6 lg:space-y-8">
            {/* Overview Metrics */}
            <OverviewCards />
            
            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <CallPerformanceChart />
              <RevenueInsights />
            </div>
            
            {/* Conversion Funnel */}
            <ConversionFunnel />
            
            {/* Call Logs Table */}
            <CallLogsTable />
            
            {/* AI Summary Panel */}
            <AISummaryPanel />
          </div>
        </main>
      </div>
    </div>
  );
};

export default Dashboard;
