import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '../api/dashboard';

// Hook for overview metrics
export const useMetrics = (period: string = '30d') => {
  return useQuery({
    queryKey: ['metrics', period],
    queryFn: () => dashboardApi.getMetrics(period),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 2,
  });
};

// Hook for call performance data
export const useCallPerformance = (days: number = 7) => {
  return useQuery({
    queryKey: ['callPerformance', days],
    queryFn: () => dashboardApi.getCallPerformance(days),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 2,
  });
};

// Hook for revenue breakdown
export const useRevenue = (period: string = '30d') => {
  return useQuery({
    queryKey: ['revenue', period],
    queryFn: () => dashboardApi.getRevenue(period),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 2,
  });
};

// Hook for conversion funnel data
export const useFunnel = (period: string = '30d') => {
  return useQuery({
    queryKey: ['funnel', period],
    queryFn: () => dashboardApi.getFunnel(period),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 2,
  });
};

// Hook for call logs with pagination
export const useCalls = (page: number = 1, limit: number = 50) => {
  const offset = (page - 1) * limit;
  
  return useQuery({
    queryKey: ['calls', page, limit],
    queryFn: () => dashboardApi.getCalls(limit, offset),
    staleTime: 2 * 60 * 1000, // 2 minutes
    retry: 2,
    placeholderData: (previousData) => previousData, // Keep previous data while loading new page
  });
};

// Hook for AI summaries with pagination
export const useAISummaries = (page: number = 1, limit: number = 20) => {
  const offset = (page - 1) * limit;
  
  return useQuery({
    queryKey: ['aiSummaries', page, limit],
    queryFn: () => dashboardApi.getAISummaries(limit, offset),
    staleTime: 10 * 60 * 1000, // 10 minutes
    retry: 2,
    placeholderData: (previousData) => previousData, // Keep previous data while loading new page
  });
};

// Hook for business profile
export const useProfile = () => {
  return useQuery({
    queryKey: ['profile'],
    queryFn: () => dashboardApi.getProfile(),
    staleTime: 15 * 60 * 1000, // 15 minutes
    retry: 2,
  });
};

// Hook for metrics with auto-refresh (for real-time updates)
export const useMetricsRealTime = (period: string = '30d') => {
  return useQuery({
    queryKey: ['metrics', period],
    queryFn: () => dashboardApi.getMetrics(period),
    staleTime: 30 * 1000, // 30 seconds for real-time
    retry: 2,
    refetchInterval: 30 * 1000, // Auto-refresh every 30 seconds
  });
};
