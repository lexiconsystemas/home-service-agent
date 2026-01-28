import React, { useState } from 'react';
import { Zap, AlertCircle, ChevronLeft, ChevronRight } from 'lucide-react';
import { Badge } from '@/app/components/ui/badge';
import { useAISummaries } from '../../../hooks/useDashboard';
import { CardSkeleton } from '../../../components/ui/Skeleton';
import { ErrorDisplay } from '../../../components/ui/ErrorDisplay';

const AISummaryPanel: React.FC = () => {
  const [currentPage, setCurrentPage] = useState(1);
  const { data: summariesData, isLoading, error, refetch } = useAISummaries(currentPage);

  if (isLoading) {
    return <CardSkeleton />;
  }

  if (error || !summariesData?.success) {
    return (
      <ErrorDisplay
        message="Failed to load AI summaries"
        onRetry={() => refetch()}
      />
    );
  }

  const { summaries, pagination } = summariesData.data;
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

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'positive':
        return 'bg-green-100 text-green-700';
      case 'negative':
        return 'bg-red-100 text-red-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600';
    if (confidence >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  return (
    <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap className="w-5 h-5 text-blue-500" />
          <h3 className="text-lg font-semibold text-gray-900">AI Call Summaries</h3>
        </div>
        <div className="text-sm text-gray-500">
          Showing {pagination.offset + 1}-{Math.min(pagination.offset + pagination.limit, pagination.total)} of {pagination.total}
        </div>
      </div>
      
      <div className="space-y-4">
        {summaries.map((summary) => (
          <div key={summary.id} className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors">
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className={`px-2 py-1 rounded-full text-xs font-medium ${getSentimentColor(summary.sentiment)}`}>
                  {summary.sentiment}
                </div>
                <div className="flex items-center gap-1 text-sm text-gray-500">
                  <AlertCircle className="w-3 h-3" />
                  <span className={getConfidenceColor(summary.confidence)}>
                    {Math.round(summary.confidence * 100)}% confidence
                  </span>
                </div>
              </div>
              <div className="text-xs text-gray-500">
                {formatTimeAgo(summary.created_at)}
              </div>
            </div>
            
            <p className="text-gray-700 mb-3 text-sm leading-relaxed">
              {summary.summary}
            </p>
            
            <div className="flex items-center justify-between">
              <div className="text-xs text-gray-500">
                Lead ID: {summary.lead_id}
              </div>
              <Badge variant="outline" className="text-xs">
                AI Generated
              </Badge>
            </div>
          </div>
        ))}
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
      
      {summaries.length === 0 && (
        <div className="text-center py-8">
          <Zap className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No AI summaries available yet</p>
          <p className="text-sm text-gray-400 mt-1">AI summaries will appear here as calls are processed</p>
        </div>
      )}
    </div>
  );
};

export default AISummaryPanel;
