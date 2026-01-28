import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

const Login: React.FC = () => {
  const [apiKey, setApiKey] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { login, error, isLoading } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!apiKey.trim()) {
      return;
    }

    setIsSubmitting(true);
    
    try {
      const success = await login(apiKey.trim());
      if (success) {
        navigate('/dashboard');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setApiKey(e.target.value);
  };

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4">
      <div className="max-w-md w-full">
        {/* Logo/Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-lg mb-4">
            <svg
              className="w-8 h-8 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"
              />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">
            Lexicon Dashboard
          </h1>
          <p className="text-slate-400">
            Enter your API key to access your dashboard
          </p>
        </div>

        {/* Login Form */}
        <div className="bg-slate-800 rounded-lg p-6 shadow-xl">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* API Key Input */}
            <div>
              <label htmlFor="apiKey" className="block text-sm font-medium text-slate-300 mb-2">
                Client API Key
              </label>
              <input
                id="apiKey"
                type="password"
                value={apiKey}
                onChange={handleInputChange}
                placeholder="lexicon_client_your-client-id_abc123..."
                className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
                disabled={isLoading || isSubmitting}
                autoComplete="off"
              />
              <p className="mt-2 text-xs text-slate-500">
                Your client API key should start with "lexicon_client_"
              </p>
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-red-900/50 border border-red-700 rounded-lg p-3">
                <div className="flex items-center">
                  <svg
                    className="w-5 h-5 text-red-400 mr-2 flex-shrink-0"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <p className="text-red-300 text-sm">{error}</p>
                </div>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading || isSubmitting || !apiKey.trim()}
              className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isSubmitting ? (
                <div className="flex items-center justify-center">
                  <svg
                    className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  Authenticating...
                </div>
              ) : (
                'Access Dashboard'
              )}
            </button>
          </form>

          {/* Help Section */}
          <div className="mt-6 pt-6 border-t border-slate-700">
            <div className="text-center">
              <p className="text-slate-400 text-sm mb-2">
                Need help finding your API key?
              </p>
              <a
                href="#"
                className="text-blue-400 hover:text-blue-300 text-sm font-medium transition-colors"
                onClick={(e) => {
                  e.preventDefault();
                  // TODO: Open help modal or navigate to help page
                }}
              >
                Contact Support
              </a>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 text-center">
          <p className="text-slate-500 text-xs">
            © 2026 Lexicon Systemas. All rights reserved.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;
