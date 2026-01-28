import { Home, Phone, DollarSign, Users, FileText, Settings, BarChart3, ChevronLeft, ChevronRight } from 'lucide-react';

const navItems = [
  { icon: Home, label: 'Overview', active: true },
  { icon: Phone, label: 'Calls', active: false },
  { icon: BarChart3, label: 'Performance', active: false },
  { icon: DollarSign, label: 'Revenue', active: false },
  { icon: Users, label: 'Customers', active: false },
  { icon: FileText, label: 'Reports', active: false },
  { icon: Settings, label: 'Settings', active: false },
];

interface SidebarProps {
  isOpen: boolean;
  isCollapsed: boolean;
  onClose: () => void;
  onToggleCollapse: () => void;
}

export function Sidebar({ isOpen, isCollapsed, onClose, onToggleCollapse }: SidebarProps) {
  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}
      
      {/* Sidebar */}
      <aside 
        className={`
          fixed lg:sticky top-0 h-screen bg-[#1e3a5f] text-white flex flex-col z-50 transition-all duration-300 ease-in-out
          ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
          ${isCollapsed ? 'lg:w-20' : 'lg:w-64'}
          w-64
        `}
      >
        <div className={`p-6 border-b border-white/10 flex items-center ${isCollapsed ? 'lg:justify-center' : 'justify-between'}`}>
          <div className={`${isCollapsed ? 'lg:hidden' : ''}`}>
            <h1 className="text-xl font-semibold">ServicePro</h1>
            <p className="text-sm text-white/60 mt-1">Business Dashboard</p>
          </div>
          {isCollapsed && (
            <div className="hidden lg:block">
              <h1 className="text-xl font-semibold">SP</h1>
            </div>
          )}
          
          {/* Desktop collapse toggle */}
          <button
            onClick={onToggleCollapse}
            className="hidden lg:flex items-center justify-center w-8 h-8 rounded-lg hover:bg-white/10 transition-colors"
          >
            {isCollapsed ? (
              <ChevronRight className="w-5 h-5" />
            ) : (
              <ChevronLeft className="w-5 h-5" />
            )}
          </button>
        </div>
        
        <nav className="flex-1 p-4 overflow-y-auto">
          <ul className="space-y-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <li key={item.label}>
                  <a
                    href="#"
                    className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                      item.active
                        ? 'bg-white/10 text-white'
                        : 'text-white/70 hover:bg-white/5 hover:text-white'
                    } ${isCollapsed ? 'lg:justify-center lg:px-2' : ''}`}
                    title={isCollapsed ? item.label : ''}
                  >
                    <Icon className="w-5 h-5 flex-shrink-0" />
                    <span className={`${isCollapsed ? 'lg:hidden' : ''}`}>{item.label}</span>
                  </a>
                </li>
              );
            })}
          </ul>
        </nav>
        
        <div className={`p-4 border-t border-white/10 ${isCollapsed ? 'lg:hidden' : ''}`}>
          <div className="bg-white/5 rounded-lg p-4">
            <p className="text-sm font-medium">Need Help?</p>
            <p className="text-xs text-white/60 mt-1">Contact support for assistance</p>
            <button className="mt-3 w-full bg-white/10 hover:bg-white/20 text-white px-4 py-2 rounded-md text-sm transition-colors">
              Get Support
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}