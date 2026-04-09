import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export default function AuthCallback() {
  const navigate = useNavigate();

  useEffect(() => {
    // This page is no longer needed with JWT authentication
    // Redirect to login if accessed directly
    const token = localStorage.getItem('access_token');
    if (token) {
      const user = JSON.parse(localStorage.getItem('user') || '{}');
      if (user.role === 'TECHNICIEN') {
        navigate('/technician/dashboard');
      } else {
        navigate('/admin/dashboard');
      }
    } else {
      navigate('/login');
    }
  }, [navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
    </div>
  );
}