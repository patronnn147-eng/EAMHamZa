import React, { useEffect } from 'react';

const LogoutCallbackPage: React.FC = () => {
  useEffect(() => {
    // The OIDC provider has logged out the user and redirected here
    // We can redirect to the home page or show a logout success message
    setTimeout(() => {
      globalThis.location.href = '/';
    }, 2000);
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-800/50">
      <div className="text-center">
        <div className="mx-auto h-12 w-12 flex items-center justify-center rounded-full bg-green-100 mb-4">
          <svg
            className="h-6 w-6 text-green-600"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">
          Logout Successful
        </h2>
        <p className="text-blue-200 mb-4">
          You have been successfully logged out.
        </p>
        <p className="text-sm text-blue-300">Redirecting to home page...</p>
      </div>
    </div>
  );
};

export default LogoutCallbackPage;
