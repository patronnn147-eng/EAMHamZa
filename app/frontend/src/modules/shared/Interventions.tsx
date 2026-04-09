import { useAuth } from '@/contexts/AuthContext';
import {
  DeleteInterventionDialog,
  InterventionFormDialog,
  InterventionsHeader,
  InterventionsList,
  InterventionsSearch,
} from './interventions/components';
import { useInterventions } from './interventions/hooks';

export default function Interventions() {
  const { user } = useAuth();
  const {
    workOrders,
    filteredInterventions,
    searchTerm,
    setSearchTerm,
    loading,
    dialogOpen,
    setDialogOpen,
    deleteDialogOpen,
    setDeleteDialogOpen,
    editingIntervention,
    deletingIntervention,
    setDeletingIntervention,
    formData,
    setFormData,
    handleOpenDialog,
    handleSubmit,
    handleDelete,
  } = useInterventions();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <InterventionsHeader onCreate={() => handleOpenDialog()} />

      <InterventionsSearch searchTerm={searchTerm} setSearchTerm={setSearchTerm} />

      <InterventionsList
        interventions={filteredInterventions}
        workOrders={workOrders}
        isAdmin={user?.role === 'ADMIN'}
        onEdit={handleOpenDialog}
        onRequestDelete={(intervention) => {
          setDeletingIntervention(intervention);
          setDeleteDialogOpen(true);
        }}
      />

      <InterventionFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        editingIntervention={editingIntervention}
        workOrders={workOrders}
        formData={formData}
        setFormData={setFormData}
        onSubmit={handleSubmit}
      />

      <DeleteInterventionDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        deletingIntervention={deletingIntervention}
        onDelete={handleDelete}
      />
    </div>
  );
}