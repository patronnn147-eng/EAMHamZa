import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { client } from '@/lib/api';

export function SectionRedirect({ section }: { section: 'machines' | 'work-orders' | 'interventions' }) {
  const [loading, setLoading] = useState(true);
  const [redirectPath, setRedirectPath] = useState<string>('/');

  useEffect(() => {
    const resolve = async () => {
      try {
        const me = await client.auth.me();
        const role = me.data?.role;

        if (role === 'TECHNICIEN') {
          setRedirectPath(`/technician/${section}`);
        } else if (role === 'CHETOP') {
          setRedirectPath(`/chetop/${section}`);
        } else if (role === 'CHEFTECH') {
          setRedirectPath(`/cheftech/${section}`);
        } else {
          setRedirectPath(`/admin/${section}`);
        }
      } catch (error) {
        setRedirectPath('/login');
      } finally {
        setLoading(false);
      }
    };

    resolve();
  }, [section]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return <Navigate to={redirectPath} replace />;
}
