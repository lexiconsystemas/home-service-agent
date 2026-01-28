import { Bell, Calendar, ChevronDown, Menu } from 'lucide-react';
import { format } from 'date-fns';

interface HeaderProps {
  onMenuClick: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  const today = new Date();
  
  return (
    <header className="bg-white border-b border-gray-200 px-4 lg:px-8 py-4 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center gap-4">
        {/* Mobile menu button */}
        <button
          onClick={onMenuClick}
          className="lg:hidden p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <Menu className="w-6 h-6 text-gray-600" />
        </button>
        
        <div>
          <h2 className="text-xl lg:text-2xl font-semibold text-gray-900">Dashboard Overview</h2>
          <p className="text-xs lg:text-sm text-gray-500 mt-1 hidden sm:block">Welcome back! Here's what's happening today.</p>
        </div>
      </div>
      
      <div className="flex items-center gap-2 lg:gap-4">
        <button className="hidden md:flex items-center gap-2 px-3 lg:px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
          <Calendar className="w-4 h-4 text-gray-600" />
          <span className="text-sm text-gray-700 hidden lg:inline">Last 30 Days</span>
          <span className="text-sm text-gray-700 lg:hidden">30d</span>
          <ChevronDown className="w-4 h-4 text-gray-600" />
        </button>
        
        <button className="relative p-2 hover:bg-gray-100 rounded-lg transition-colors">
          <Bell className="w-5 h-5 text-gray-600" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
        </button>
        
        <div className="hidden sm:flex items-center gap-3 pl-4 border-l border-gray-200">
          <div className="text-right hidden lg:block">
            <p className="text-sm font-medium text-gray-900">John's HVAC</p>
            <p className="text-xs text-gray-500">{format(today, 'MMMM dd, yyyy')}</p>
          </div>
          <div className="w-10 h-10 bg-[#1e3a5f] rounded-full flex items-center justify-center text-white font-medium">
            JH
          </div>
        </div>
      </div>
    </header>
  );
}