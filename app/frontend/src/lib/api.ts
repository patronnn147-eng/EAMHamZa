import { createClient } from '@metagptx/web-sdk';

// Create and export the API client
export const client = createClient();

// Helper function to get user role
export const getUserRole = async () => {
  try {
    const user = await client.auth.me();
    if (user.data) {
      // Fetch user details from utilisateurs table to get role
      const response = await client.entities.utilisateurs.query({
        query: { user_id: user.data.id },
        limit: 1
      });
      
      if (response.data.items && response.data.items.length > 0) {
        return response.data.items[0].role;
      }
    }
    return null;
  } catch (error) {
    console.error('Error fetching user role:', error);
    return null;
  }
};

// Helper function to check if user has specific role
export const hasRole = async (allowedRoles: string[]) => {
  const role = await getUserRole();
  return role ? allowedRoles.includes(role) : false;
};