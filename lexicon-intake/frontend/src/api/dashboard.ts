import apiClient from './client';

// Types for API responses
export interface MetricsResponse {
  success: boolean;
  data: {
    total_calls: number;
    booked_jobs: number;
    revenue: number;
    conversion_rate: number;
    period: {
      start_date: string;
      end_date: string;
    };
  };
}

export interface CallPerformanceResponse {
  success: boolean;
  data: {
    call_volume: Array<{
      date: string;
      call_count: number;
    }>;
    period_days: number;
  };
}

export interface RevenueResponse {
  success: boolean;
  data: {
    revenue_breakdown: Array<{
      service_type: string;
      qualified_count: number;
      revenue: number;
      avg_job_value: number;
    }>;
    total_revenue: number;
    period: string;
  };
}

export interface FunnelResponse {
  success: boolean;
  data: {
    funnel: {
      calls: number;
      answered: number;
      appointments: number;
      completed: number;
    };
    rates: {
      answer_rate: number;
      appointment_rate: number;
      completion_rate: number;
    };
    period: string;
  };
}

export interface CallsResponse {
  success: boolean;
  data: {
    calls: Array<{
      id: string;
      lead_id: string;
      caller_phone: string;
      caller_name: string;
      service_requested: string;
      urgency: string;
      classification: string;
      created_at: string;
      budget?: number;
      location?: string;
    }>;
    pagination: {
      total: number;
      limit: number;
      offset: number;
      has_more: boolean;
    };
  };
}

export interface AISummariesResponse {
  success: boolean;
  data: {
    summaries: Array<{
      id: string;
      lead_id: string;
      summary: string;
      sentiment: string;
      confidence: number;
      created_at: string;
    }>;
    pagination: {
      total: number;
      limit: number;
      offset: number;
      has_more: boolean;
    };
  };
}

export interface ProfileResponse {
  success: boolean;
  data: {
    client_id: string;
    business_name: string;
    phone: string;
    email: string;
    address?: string;
    service_areas: string[];
    delivery_channels: string[];
    followup_flags: Record<string, boolean>;
    created_at: string;
    updated_at: string;
  };
}

// API functions for dashboard endpoints
export const dashboardApi = {
  // Get overview metrics
  getMetrics: async (period: string = '30d'): Promise<MetricsResponse> => {
    const response = await apiClient.get('/v1/dashboard/metrics', {
      params: { period }
    });
    return response.data;
  },

  // Get call performance data
  getCallPerformance: async (days: number = 7): Promise<CallPerformanceResponse> => {
    const response = await apiClient.get('/v1/dashboard/call-performance', {
      params: { days }
    });
    return response.data;
  },

  // Get revenue breakdown
  getRevenue: async (period: string = '30d'): Promise<RevenueResponse> => {
    const response = await apiClient.get('/v1/dashboard/revenue', {
      params: { period }
    });
    return response.data;
  },

  // Get conversion funnel data
  getFunnel: async (period: string = '30d'): Promise<FunnelResponse> => {
    const response = await apiClient.get('/v1/dashboard/funnel', {
      params: { period }
    });
    return response.data;
  },

  // Get recent calls
  getCalls: async (limit: number = 50, offset: number = 0): Promise<CallsResponse> => {
    const response = await apiClient.get('/v1/dashboard/calls', {
      params: { limit, offset }
    });
    return response.data;
  },

  // Get AI summaries
  getAISummaries: async (limit: number = 20, offset: number = 0): Promise<AISummariesResponse> => {
    const response = await apiClient.get('/v1/dashboard/ai-summaries', {
      params: { limit, offset }
    });
    return response.data;
  },

  // Get business profile
  getProfile: async (): Promise<ProfileResponse> => {
    const response = await apiClient.get('/v1/dashboard/profile');
    return response.data;
  },
};

// Export individual functions for convenience
export const {
  getMetrics,
  getCallPerformance,
  getRevenue,
  getFunnel,
  getCalls,
  getAISummaries,
  getProfile,
} = dashboardApi;
