import { useEffect, useMemo, useState } from 'react';
import { client } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Trash2, Users as UsersIcon } from 'lucide-react';
import { AppPagination } from '@/components/shared/AppPagination';

interface AdminUser {
  id: number;
  nom: string;
  email: string;
  role: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  shift_type?: 'MORNING' | 'NIGHT' | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export default function UserManagement() {
  const { toast } = useToast();

  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [pageSize] = useState(100);

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletingUser, setDeletingUser] = useState<AdminUser | null>(null);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const response = await client.apiCall.invoke({
        url: `/api/v1/admin/users?page=${page}&size=${pageSize}`,
        method: 'GET',
      });
      const data = response.data;
      setUsers(data?.items || []);
      setTotalPages(data?.total_pages || 1);
    } catch (error) {
      console.error('Error fetching users:', error);
      toast({
        title: 'Error',
        description: 'Failed to load users',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [page]);

  const roleBadge = (role: string) => {
    const map: Record<string, string> = {
      ADMIN: 'bg-red-500',
      CHEFTECH: 'bg-blue-500',
      CHETOP: 'bg-purple-500',
      TECHNICIEN: 'bg-green-500',
    };
    return <Badge className={map[role] || 'bg-gray-500'}>{role}</Badge>;
  };

  const statusBadge = (status: string) => {
    const map: Record<string, string> = {
      PENDING: 'bg-yellow-500',
      APPROVED: 'bg-green-600',
      REJECTED: 'bg-red-600',
    };
    return <Badge className={map[status] || 'bg-gray-500'}>{status}</Badge>;
  };

  const shiftBadge = (shiftType?: string | null) => {
    if (!shiftType) return <Badge variant="outline">—</Badge>;
    if (shiftType === 'MORNING') return <Badge className="bg-yellow-100 text-yellow-800">Morning</Badge>;
    if (shiftType === 'NIGHT') return <Badge className="bg-indigo-100 text-indigo-800">Night</Badge>;
    return <Badge variant="outline">{shiftType}</Badge>;
  };

  const sortedUsers = useMemo(() => {
    // Note: Backend now handles sorting/pagination, but we keep this as a safety
    return [...users];
  }, [users]);

  const updateStatus = async (userId: number, status: string) => {
    try {
      const response = await client.apiCall.invoke({
        url: `/api/v1/admin/users/${userId}/status`,
        method: 'PATCH',
        data: { status },
      });

      const updated = response.data;
      setUsers(prev => prev.map(u => (u.id === userId ? { ...u, ...updated } : u)));

      toast({
        title: 'Success',
        description: 'User status updated',
      });
    } catch (error) {
      console.error('Error updating status:', error);
      toast({
        title: 'Error',
        description: 'Failed to update user status',
        variant: 'destructive',
      });
    }
  };

  const updateShiftType = async (userId: number, shift_type: string) => {
    try {
      const response = await client.apiCall.invoke({
        url: `/api/v1/admin/users/${userId}/shift-type`,
        method: 'PATCH',
        data: { shift_type },
      });

      const updated = response.data;
      setUsers(prev => prev.map(u => (u.id === userId ? { ...u, ...updated } : u)));

      toast({
        title: 'Success',
        description: 'User shift updated',
      });
    } catch (error) {
      console.error('Error updating shift:', error);
      toast({
        title: 'Error',
        description: 'Failed to update user shift',
        variant: 'destructive',
      });
    }
  };

  const confirmDelete = (user: AdminUser) => {
    setDeletingUser(user);
    setDeleteDialogOpen(true);
  };

  const handleDelete = async () => {
    if (!deletingUser) return;

    try {
      await client.apiCall.invoke({
        url: `/api/v1/admin/users/${deletingUser.id}`,
        method: 'DELETE',
      });

      setUsers(prev => prev.filter(u => u.id !== deletingUser.id));
      toast({
        title: 'Success',
        description: 'User deleted',
      });
    } catch (error) {
      console.error('Error deleting user:', error);
      toast({
        title: 'Error',
        description: 'Failed to delete user',
        variant: 'destructive',
      });
    } finally {
      setDeleteDialogOpen(false);
      setDeletingUser(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
          <p className="text-muted-foreground">Loading users...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <UsersIcon className="w-6 h-6" />
            User Management
          </CardTitle>
          <CardDescription>
            View users, update status, assign default shift, and delete users.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Shift</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedUsers.map((u) => (
                  <TableRow key={u.id}>
                    <TableCell className="font-mono text-xs">{u.id}</TableCell>
                    <TableCell className="font-medium">{u.nom}</TableCell>
                    <TableCell>{u.email}</TableCell>
                    <TableCell>{roleBadge(u.role)}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {statusBadge(u.status)}
                        <Select
                          value={u.status}
                          onValueChange={(value) => updateStatus(u.id, value)}
                        >
                          <SelectTrigger className="w-[140px]">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="PENDING">PENDING</SelectItem>
                            <SelectItem value="APPROVED">APPROVED</SelectItem>
                            <SelectItem value="REJECTED">REJECTED</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {shiftBadge(u.shift_type)}
                        <Select
                          value={(u.shift_type || 'MORNING') as string}
                          onValueChange={(value) => updateShiftType(u.id, value)}
                        >
                          <SelectTrigger className="w-[140px]">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="MORNING">Morning (09:00-17:00)</SelectItem>
                            <SelectItem value="NIGHT">Night (17:00-24:00)</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        variant="outline"
                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                        onClick={() => confirmDelete(u)}
                      >
                        <Trash2 className="w-4 h-4 mr-1" />
                        Delete
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}

                {sortedUsers.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground">
                      No users found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
          <AppPagination
            currentPage={page}
            totalPages={totalPages}
            onPageChange={setPage}
          />
        </CardContent>
      </Card>

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirm deletion</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete user <strong>{deletingUser?.nom}</strong> ({deletingUser?.email})?
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDeletingUser(null)}>Cancel</AlertDialogCancel>
            <AlertDialogAction className="bg-red-600 hover:bg-red-700" onClick={handleDelete}>
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
