import { useState, useEffect } from 'react';
import { client } from '@/lib/api';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { LogOut, User } from 'lucide-react';

interface UserData {
  id: string;
  email: string;
}

export default function Header() {
  const [user, setUser] = useState<UserData | null>(null);
  const [userRole, setUserRole] = useState<string>('');

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const userData = await client.auth.me();
        if (userData.data) {
          setUser(userData.data);
          
          // Fetch user role from utilisateurs table
          const response = await client.entities.utilisateurs.query({
            query: { user_id: userData.data.id },
            limit: 1
          });
          
          if (response.data.items && response.data.items.length > 0) {
            setUserRole(response.data.items[0].role);
          }
        }
      } catch (error) {
        console.error('Error fetching user:', error);
      }
    };

    fetchUser();
  }, []);

  const handleLogout = async () => {
    try {
      await client.auth.logout();
      window.location.href = '/login';
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  const getInitials = (email: string) => {
    return email.substring(0, 2).toUpperCase();
  };

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-3">
            <img 
              src="https://mgx-backend-cdn.metadl.com/generate/images/934400/2026-01-27/44d01b7c-ac50-4b6d-9ccb-0a74219d8673.png" 
              alt="Logo" 
              className="h-8 w-8"
            />
            <h1 className="text-xl font-bold text-gray-900">Asset Management</h1>
          </div>

          <div className="flex items-center space-x-4">
            {userRole && (
              <span className="text-sm text-gray-600 bg-blue-50 px-3 py-1 rounded-full">
                {userRole}
              </span>
            )}
            
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="relative h-10 w-10 rounded-full">
                  <Avatar>
                    <AvatarFallback className="bg-blue-600 text-white">
                      {user?.email ? getInitials(user.email) : <User className="h-5 w-5" />}
                    </AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium">My Account</p>
                    {user?.email && (
                      <p className="text-xs text-gray-500">{user.email}</p>
                    )}
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout}>
                  <LogOut className="mr-2 h-4 w-4" />
                  <span>Log out</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </div>
    </header>
  );
}