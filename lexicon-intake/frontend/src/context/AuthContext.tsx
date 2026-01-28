import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { dashboardApi } from '../api/dashboard';

// Types
interface AuthContextType {
  apiKey: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (apiKey: string) => Promise<boolean>;
  logout: () => void;
  error: string | null;
}

interface AuthProviderProps {
  children: ReactNode;
}

// Create context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// AuthProvider component
export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  // Check for existing auth on mount
  useEffect(() => {
    const storedApiKey = localStorage.getItem('client_api_key');
    const storedClientInfo = localStorage.getItem('client_info');
    
    if (storedApiKey && storedClientInfo) {
      setApiKey(storedApiKey);
      setIsAuthenticated(true);
    }
    setIsLoading(false);
  }, []);

  // Login function
  const login = async (inputApiKey: string): Promise<boolean> => {
    setIsLoading(true);
    setError(null);
    
    try {
      // Store API key temporarily for validation
      localStorage.setItem('client_api_key', inputApiKey);
      
      // Validate API key by calling the profile endpoint
      const response = await dashboardApi.getProfile();
      
      if (response.success) {
        // API key is valid
        setApiKey(inputApiKey);
        setIsAuthenticated(true);
        
        // Store client info
        localStorage.setItem('client_info', JSON.stringify(response.data));
        
        return true;
      } else {
        // Invalid response
        throw new Error('Invalid API key');
      }
    } catch (err) {
      // API key is invalid
      localStorage.removeItem('client_api_key');
      localStorage.removeItem('client_info');
      setApiKey(null);
      setIsAuthenticated(false);
      
      const errorMessage = err instanceof Error ? err.message : 'Authentication failed';
      setError(errorMessage);
      
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  // Logout function
  const logout = () => {
    localStorage.removeItem('client_api_key');
    localStorage.removeItem('client_info');
    setApiKey(null);
    setIsAuthenticated(false);
    setError(null);
    navigate('/login');
  };

  // Context value
  const value: AuthContextType = {
    apiKey,
    isAuthenticated,
    isLoading,
    login,
    logout,
    error,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// Custom hook to use auth context
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Protected route component
export const ProtectedRoute: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, isLoading, navigate]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-white text-lg">Loading...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null; // Will redirect
  }

  return <>{children}</>;
};
