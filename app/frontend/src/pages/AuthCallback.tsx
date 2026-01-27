import { useEffect } from 'react';
import { client } from '@/lib/api';

export default function AuthCallback() {
  useEffect(() => {
    const handleCallback = async () => {
      try {
        await client.auth.login();
        
        // Check if there's a pending role from registration
        const pendingRole = sessionStorage.getItem('pendingRole');
        if (pendingRole) {
          // Get current user
          const userData = await client.auth.me();
          if (userData.data) {
            // Create user entry in utilisateurs table with the selected role
            try {
              await client.entities.utilisateurs.create({
                data: {
                  user_id: userData.data.id,
                  nom: userData.data.email.split('@')[0],
                  email: userData.data.email,
                  role: pendingRole,
                },
              });
            } catch (error) {
              // User might already exist, that's okay
              console.log('User entry already exists or error creating:', error);
            }
          }
          sessionStorage.removeItem('pendingRole');
        }
        
        window.location.href = '/';
      } catch (error) {
        console.error('Auth callback error:', error);
        window.location.href = '/login';
      }
    };

    handleCallback();
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
        <p className="mt-4 text-gray-600">Completing authentication...</p>
      </div>
    </div>
  );
}