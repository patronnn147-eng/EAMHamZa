import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { PermissionButton } from '@/components/ui/PermissionButton';
import { PermissionGuard } from '@/components/ui/PermissionGuard';
import { usePermissions } from '@/hooks/usePermissions';
import { 
  Users, 
  Plus, 
  Edit, 
  Trash2, 
  Eye, 
  Settings,
  FileText,
  Calendar,
  Archive
} from 'lucide-react';

export function RoleBasedActions() {
  const { userRole, canCreate, canUpdate, canDelete } = usePermissions();

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Actions disponibles pour votre rôle: {userRole}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            
            {/* Users Section */}
            <div className="border rounded-lg p-4">
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <Users className="h-4 w-4" />
                Utilisateurs
              </h3>
              <div className="space-y-2">
                <PermissionButton permission="create" resource="users" size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  Créer utilisateur
                </PermissionButton>
                <PermissionButton permission="read" resource="users" size="sm" variant="outline">
                  <Eye className="h-4 w-4 mr-2" />
                  Voir utilisateurs
                </PermissionButton>
                <PermissionButton permission="update" resource="users" size="sm" variant="outline">
                  <Edit className="h-4 w-4 mr-2" />
                  Modifier utilisateur
                </PermissionButton>
                <PermissionButton permission="delete" resource="users" size="sm" variant="destructive">
                  <Trash2 className="h-4 w-4 mr-2" />
                  Supprimer utilisateur
                </PermissionButton>
              </div>
            </div>

            {/* Machines Section */}
            <div className="border rounded-lg p-4">
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <Settings className="h-4 w-4" />
                Machines
              </h3>
              <div className="space-y-2">
                <PermissionButton permission="create" resource="machines" size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  Ajouter machine
                </PermissionButton>
                <PermissionButton permission="read" resource="machines" size="sm" variant="outline">
                  <Eye className="h-4 w-4 mr-2" />
                  Voir machines
                </PermissionButton>
                <PermissionButton permission="update" resource="machines" size="sm" variant="outline">
                  <Edit className="h-4 w-4 mr-2" />
                  Modifier statut
                </PermissionButton>
                <PermissionButton permission="delete" resource="machines" size="sm" variant="destructive">
                  <Trash2 className="h-4 w-4 mr-2" />
                  Supprimer machine
                </PermissionButton>
              </div>
            </div>

            {/* Work Orders Section */}
            <div className="border rounded-lg p-4">
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <FileText className="h-4 w-4" />
                Ordres de travail
              </h3>
              <div className="space-y-2">
                <PermissionButton permission="create" resource="work_orders" size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  Créer ordre
                </PermissionButton>
                <PermissionButton permission="read" resource="work_orders" size="sm" variant="outline">
                  <Eye className="h-4 w-4 mr-2" />
                  Voir ordres
                </PermissionButton>
                <PermissionButton permission="update" resource="work_orders" size="sm" variant="outline">
                  <Edit className="h-4 w-4 mr-2" />
                  Modifier ordre
                </PermissionButton>
                <PermissionButton permission="delete" resource="work_orders" size="sm" variant="destructive">
                  <Trash2 className="h-4 w-4 mr-2" />
                  Supprimer ordre
                </PermissionButton>
              </div>
            </div>

            {/* Interventions Section */}
            <div className="border rounded-lg p-4">
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <FileText className="h-4 w-4" />
                Interventions
              </h3>
              <div className="space-y-2">
                <PermissionButton permission="create" resource="interventions" size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  Créer rapport
                </PermissionButton>
                <PermissionButton permission="read" resource="interventions" size="sm" variant="outline">
                  <Eye className="h-4 w-4 mr-2" />
                  Voir rapports
                </PermissionButton>
                <PermissionButton permission="update" resource="interventions" size="sm" variant="outline">
                  <Edit className="h-4 w-4 mr-2" />
                  Modifier rapport
                </PermissionButton>
                <PermissionButton permission="delete" resource="interventions" size="sm" variant="destructive">
                  <Trash2 className="h-4 w-4 mr-2" />
                  Supprimer rapport
                </PermissionButton>
              </div>
            </div>

            {/* Planning Section */}
            <div className="border rounded-lg p-4">
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                Planning
              </h3>
              <div className="space-y-2">
                <PermissionButton permission="create" resource="planning" size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  Créer planning
                </PermissionButton>
                <PermissionButton permission="read" resource="planning" size="sm" variant="outline">
                  <Eye className="h-4 w-4 mr-2" />
                  Voir planning
                </PermissionButton>
                <PermissionButton permission="update" resource="planning" size="sm" variant="outline">
                  <Edit className="h-4 w-4 mr-2" />
                  Modifier planning
                </PermissionButton>
                <PermissionButton permission="delete" resource="planning" size="sm" variant="destructive">
                  <Trash2 className="h-4 w-4 mr-2" />
                  Supprimer planning
                </PermissionButton>
              </div>
            </div>

            {/* Archives Section */}
            <div className="border rounded-lg p-4">
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <Archive className="h-4 w-4" />
                Archives
              </h3>
              <div className="space-y-2">
                <PermissionButton permission="create" resource="archives" size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  Archiver
                </PermissionButton>
                <PermissionButton permission="read" resource="archives" size="sm" variant="outline">
                  <Eye className="h-4 w-4 mr-2" />
                  Voir archives
                </PermissionButton>
                <PermissionButton permission="update" resource="archives" size="sm" variant="outline">
                  <Edit className="h-4 w-4 mr-2" />
                  Modifier archive
                </PermissionButton>
                <PermissionButton permission="delete" resource="archives" size="sm" variant="destructive">
                  <Trash2 className="h-4 w-4 mr-2" />
                  Supprimer archive
                </PermissionButton>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Example of PermissionGuard with fallback */}
      <Card>
        <CardHeader>
          <CardTitle>Exemples de sections protégées</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <PermissionGuard permission="create" resource="users" fallback={
              <div className="bg-gray-100 border border-gray-300 rounded-lg p-4 text-center">
                <p className="text-gray-600">❌ Vous ne pouvez pas créer d'utilisateurs avec votre rôle actuel</p>
              </div>
            }>
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <p className="text-green-800">✅ Vous pouvez créer des utilisateurs</p>
                <Button className="mt-2">Créer un nouvel utilisateur</Button>
              </div>
            </PermissionGuard>

            <PermissionGuard permission="update" resource="machines" fallback={
              <div className="bg-gray-100 border border-gray-300 rounded-lg p-4 text-center">
                <p className="text-gray-600">❌ Vous ne pouvez pas modifier les machines avec votre rôle actuel</p>
              </div>
            }>
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <p className="text-green-800">✅ Vous pouvez modifier les machines</p>
                <Button className="mt-2">Mettre à jour une machine</Button>
              </div>
            </PermissionGuard>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
