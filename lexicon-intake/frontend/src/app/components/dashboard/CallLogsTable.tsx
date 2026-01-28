import React, { useState } from 'react';
import { Phone, Clock, Eye, ChevronLeft, ChevronRight } from 'lucide-react';
import { Badge } from '@/app/components/ui/badge';
import { useCalls } from '../../../hooks/useDashboard';
import { TableSkeleton } from '../../../components/ui/Skeleton';
import { ErrorDisplay } from '../../../components/ui/ErrorDisplay';

const CallLogsTable: React.FC = () => {
  const [currentPage, setCurrentPage] = useState(1);
  const { data: callsData, isLoading, error, refetch } = useCalls(currentPage);

  if (isLoading) {
    return <TableSkeleton />;
  }

  if (error || !callsData?.success) {
    return (
      <ErrorDisplay
        message="Failed to load call logs"
        onRetry={() => refetch()}
      />
    );
  }

  const { calls, pagination } = callsData.data;
  const totalPages = Math.ceil(pagination.total / pagination.limit);

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));
    
    if (diffInHours < 1) return 'Just now';
    if (diffInHours < 24) return `${diffInHours} hour${diffInHours > 1 ? 's' : ''} ago`;
    const diffInDays = Math.floor(diffInHours / 24);
    return `${diffInDays} day${diffInDays > 1 ? 's' : ''} ago`;
  };

  const getOutcomeBadge = (classification: string) => {
    switch (classification) {
      case 'QUALIFIED_LEAD':
        return <Badge variant="default">Booked</Badge>;
      case 'UNQUALIFIED_LEAD':
        return <Badge variant="secondary">Follow-up</Badge>;
      case 'SPAM_INVALID':
        return <Badge variant="destructive">Spam</Badge>;
      default:
        return <Badge variant="outline">Unknown</Badge>;
    }
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  return (
    <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Recent Call Logs</h3>
          <p className="text-sm text-gray-500 mt-1">Latest incoming calls and their outcomes</p>
        </div>
        <div className="text-sm text-gray-500">
          Showing {pagination.offset + 1}-{Math.min(pagination.offset + pagination.limit, pagination.total)} of {pagination.total}
        </div>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Caller</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Phone</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Service</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Outcome</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Time</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {calls.map((call) => (
              <tr key={call.id} className="hover:bg-gray-50 transition-colors">
                <td className="py-4 px-4">
                  <div>
                    <div className="font-medium text-gray-900">{call.caller_name}</div>
                    {call.location && (
                      <div className="text-sm text-gray-500">{call.location}</div>
                    )}
                  </div>
                </td>
                <td className="py-4 px-4">
                  <div className="flex items-center text-gray-600">
                    <Phone className="w-4 h-4 mr-2" />
                    {call.caller_phone}
                  </div>
                </td>
                <td className="py-4 px-4">
                  <div className="text-sm text-gray-900">{call.service_requested}</div>
                  {call.urgency && (
                    <div className="text-xs text-gray-500 capitalize">{call.urgency}</div>
                  )}
                </td>
                <td className="py-4 px-4">
                  {getOutcomeBadge(call.classification)}
                </td>
                <td className="py-4 px-4">
                  <div className="flex items-center text-sm text-gray-500">
                    <Clock className="w-4 h-4 mr-1" />
                    {formatTimeAgo(call.created_at)}
                  </div>
                </td>
                <td className="py-4 px-4">
                  <button className="text-blue-600 hover:text-blue-800 transition-colors">
                    <Eye className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-6 flex items-center justify-between">
          <div className="text-sm text-gray-500">
            Page {currentPage} of {totalPages}
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1}
              className="p-2 border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              let pageNum;
              if (totalPages <= 5) {
                pageNum = i + 1;
              } else if (currentPage <= 3) {
                pageNum = i + 1;
              } else if (currentPage >= totalPages - 2) {
                pageNum = totalPages - 4 + i;
              } else {
                pageNum = currentPage - 2 + i;
              }
              
              return (
                <button
                  key={pageNum}
                  onClick={() => handlePageChange(pageNum)}
                  className={`px-3 py-1 border rounded-md transition-colors ${
                    currentPage === pageNum
                      ? 'bg-blue-500 text-white border-blue-500'
                      : 'border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  {pageNum}
                </button>
              );
            })}
            
            <button
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
              className="p-2 border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default CallLogsTable;
