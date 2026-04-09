import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { client } from '@/lib/api';

export function RoleBasedRedirect() {
  const [loading, setLoading] = useState(true);
  const [redirectPath, setRedirectPath] = useState<string>('/');

  useEffect(() => {
    checkRole();
  }, []);

  const checkRole = async () => {
    try {
      const user = await client.auth.me();
      if (user.data) {
        if (user.data.role === 'TECHNICIEN') {
          setRedirectPath('/technician/dashboard');
        } else if (user.data.role === 'CHETOP') {
          setRedirectPath('/chetop/dashboard');
        } else if (user.data.role === 'CHEFTECH') {
          setRedirectPath('/cheftech/dashboard');
        } else {
          setRedirectPath('/admin/dashboard');
        }
      }
    } catch (error) {
      console.error('Error checking role:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return <Navigate to={redirectPath} replace />;
}
