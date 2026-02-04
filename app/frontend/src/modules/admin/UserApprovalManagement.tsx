import { useState, useEffect } from 'react';
import { client } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { CheckCircle, XCircle, Clock, Mail, User, Calendar } from 'lucide-react';
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

interface PendingUser {
  id: string;
  email: string;
  nom: string;
  role: string;
  status: string;
  created_at: string;
}

export default function UserApprovalManagement() {
  const [pendingUsers, setPendingUsers] = useState<PendingUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [selectedUser, setSelectedUser] = useState<PendingUser | null>(null);
  const [actionType, setActionType] = useState<'approve' | 'reject' | null>(null);
  const { toast } = useToast();

  const fetchPendingUsers = async () => {
    try {
      setLoading(true);
      const response = await client.apiCall.invoke({
        url: '/api/v1/user-approvals/pending',
        method: 'GET',
      });
      setPendingUsers(response.data || []);
    } catch (error) {
      const errorDetail = error instanceof Error 
        ? error.message 
        : 'Impossible de charger les utilisateurs en attente';
      toast({
        title: 'Erreur',
        description: errorDetail,
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPendingUsers();
  }, []);

  const handleAction = async () => {
    if (!selectedUser || !actionType) return;

    try {
      setActionLoading(selectedUser.id);
      const endpoint = actionType === 'approve' 
        ? `/api/v1/user-approvals/approve/${selectedUser.id}`
        : `/api/v1/user-approvals/reject/${selectedUser.id}`;

      const response = await client.apiCall.invoke({
        url: endpoint,
        method: 'POST',
      });

      toast({
        title: 'Succès',
        description: response.data.message,
      });

      // Refresh the list
      await fetchPendingUsers();
      setSelectedUser(null);
      setActionType(null);
    } catch (error) {
      const errorDetail = error instanceof Error 
        ? error.message 
        : 'Une erreur est survenue';
      toast({
        title: 'Erreur',
        description: errorDetail,
        variant: 'destructive',
      });
    } finally {
      setActionLoading(null);
    }
  };

  const openConfirmDialog = (user: PendingUser, action: 'approve' | 'reject') => {
    setSelectedUser(user);
    setActionType(action);
  };

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'ADMIN':
        return 'bg-red-500';
      case 'CHEFTECH':
        return 'bg-blue-500';
      case 'CHETOP':
        return 'bg-purple-500';
      case 'TECHNICIEN':
        return 'bg-green-500';
      default:
        return 'bg-gray-500';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Clock className="w-12 h-12 animate-spin mx-auto mb-4 text-primary" />
          <p className="text-muted-foreground">Chargement des demandes...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="w-6 h-6" />
            Gestion des Demandes d'Inscription
          </CardTitle>
          <CardDescription>
            Approuvez ou rejetez les nouvelles demandes d'inscription
          </CardDescription>
        </CardHeader>
        <CardContent>
          {pendingUsers.length === 0 ? (
            <div className="text-center py-12">
              <CheckCircle className="w-16 h-16 mx-auto mb-4 text-green-500" />
              <h3 className="text-lg font-semibold mb-2">Aucune demande en attente</h3>
              <p className="text-muted-foreground">
                Toutes les demandes d'inscription ont été traitées
              </p>
            </div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Utilisateur</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Rôle</TableHead>
                    <TableHead>Date de demande</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {pendingUsers.map((user) => (
                    <TableRow key={user.id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <User className="w-4 h-4 text-muted-foreground" />
                          <span className="font-medium">{user.nom}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Mail className="w-4 h-4 text-muted-foreground" />
                          <span className="text-sm">{user.email}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge className={getRoleBadgeColor(user.role)}>
                          {user.role}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Calendar className="w-4 h-4" />
                          {new Date(user.created_at).toLocaleDateString('fr-FR', {
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex gap-2 justify-end">
                          <Button
                            size="sm"
                            variant="default"
                            onClick={() => openConfirmDialog(user, 'approve')}
                            disabled={actionLoading === user.id}
                            className="bg-green-600 hover:bg-green-700"
                          >
                            <CheckCircle className="w-4 h-4 mr-1" />
                            Approuver
                          </Button>
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() => openConfirmDialog(user, 'reject')}
                            disabled={actionLoading === user.id}
                          >
                            <XCircle className="w-4 h-4 mr-1" />
                            Rejeter
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <AlertDialog open={!!selectedUser && !!actionType} onOpenChange={() => {
        setSelectedUser(null);
        setActionType(null);
      }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {actionType === 'approve' ? 'Approuver' : 'Rejeter'} la demande
            </AlertDialogTitle>
            <AlertDialogDescription>
              {actionType === 'approve' ? (
                <>
                  Êtes-vous sûr de vouloir approuver la demande de <strong>{selectedUser?.nom}</strong> ?
                  <br />
                  Un email de confirmation sera envoyé à <strong>{selectedUser?.email}</strong>.
                </>
              ) : (
                <>
                  Êtes-vous sûr de vouloir rejeter la demande de <strong>{selectedUser?.nom}</strong> ?
                  <br />
                  Un email de notification sera envoyé à <strong>{selectedUser?.email}</strong>.
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleAction}
              className={actionType === 'approve' ? 'bg-green-600 hover:bg-green-700' : ''}
            >
              Confirmer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}