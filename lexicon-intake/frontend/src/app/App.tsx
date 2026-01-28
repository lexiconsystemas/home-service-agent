import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from '../context/AuthContext';
import { ProtectedRoute } from '../context/AuthContext';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';

// Create a client for React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

// Helper component for root route redirect
const RequireAuth: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  
  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-white text-lg">Loading...</div>
      </div>
    );
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
};

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Router>
          <Routes>
            {/* Root route - redirect based on auth status */}
            <Route 
              path="/" 
              element={
                <RequireAuth>
                  <Navigate to="/dashboard" replace />
                </RequireAuth>
              } 
            />
            
            {/* Login route */}
            <Route path="/login" element={<Login />} />
            
            {/* Protected dashboard route */}
            <Route 
              path="/dashboard" 
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              } 
            />
            
            {/* Catch all - redirect to dashboard */}
            <Route 
              path="*" 
              element={
                <RequireAuth>
                  <Navigate to="/dashboard" replace />
                </RequireAuth>
              } 
            />
          </Routes>
        </Router>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;