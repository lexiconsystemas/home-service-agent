import axios, { AxiosInstance, AxiosError } from 'axios';

// Create axios instance with baseURL from environment
const apiClient: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add authentication
apiClient.interceptors.request.use(
  (config) => {
    // Add X-Client-API-Key header from localStorage
    const apiKey = localStorage.getItem('client_api_key');
    if (apiKey) {
      config.headers['X-Client-API-Key'] = apiKey;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle errors
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error: AxiosError) => {
    // Handle 401 errors - redirect to login
    if (error.response?.status === 401) {
      // Clear stored API key
      localStorage.removeItem('client_api_key');
      localStorage.removeItem('client_info');
      
      // Redirect to login page
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    
    // Handle network errors
    if (error.code === 'NETWORK_ERROR') {
      console.error('Network error - please check your connection');
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;
