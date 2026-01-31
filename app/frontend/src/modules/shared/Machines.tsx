import { useAuth } from '@/contexts/AuthContext';
import {
  DeleteMachineDialog,
  MachineFormDialog,
  MachinesGrid,
  MachinesHeader,
  MachinesSearch,
} from './machines/components';
import { useMachines } from './machines/hooks';

export default function Machines() {
  const { user } = useAuth();
  const canCreate = user?.role !== 'CHETOP';
  const canEdit = user?.role !== 'CHETOP';
  const canDelete = user?.role === 'ADMIN';
  const {
    filteredMachines,
    loading,
    searchTerm,
    setSearchTerm,
    dialogOpen,
    setDialogOpen,
    deleteDialogOpen,
    setDeleteDialogOpen,
    editingMachine,
    deletingMachine,
    setDeletingMachine,
    formData,
    setFormData,
    handleOpenDialog,
    handleSubmit,
    handleDelete,
  } = useMachines();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <MachinesHeader onCreate={() => handleOpenDialog()} canCreate={canCreate} />

      <MachinesSearch searchTerm={searchTerm} setSearchTerm={setSearchTerm} />

      <MachinesGrid
        machines={filteredMachines}
        canEdit={canEdit}
        canDelete={canDelete}
        onEdit={handleOpenDialog}
        onRequestDelete={(machine) => {
          setDeletingMachine(machine);
          setDeleteDialogOpen(true);
        }}
      />

      {canCreate && (
        <MachineFormDialog
          open={dialogOpen}
          onOpenChange={setDialogOpen}
          editingMachine={editingMachine}
          formData={formData}
          setFormData={setFormData}
          onSubmit={handleSubmit}
        />
      )}

      {canDelete && (
        <DeleteMachineDialog
          open={deleteDialogOpen}
          onOpenChange={setDeleteDialogOpen}
          deletingMachine={deletingMachine}
          onDelete={handleDelete}
        />
      )}
    </div>
  );
}