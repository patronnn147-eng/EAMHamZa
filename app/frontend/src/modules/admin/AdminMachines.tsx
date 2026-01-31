import {
  AdminMachinesGrid,
  AdminMachinesHeader,
  AdminMachinesSearch,
  DeleteMachineDialog,
  MachineFormDialog,
} from './machines/components';
import { useAdminMachines } from './machines/hooks';

export default function AdminMachines() {
  const {
    filteredMachines,
    searchTerm,
    setSearchTerm,
    loading,
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
  } = useAdminMachines();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <AdminMachinesHeader onCreate={() => handleOpenDialog()} />

      <AdminMachinesSearch searchTerm={searchTerm} setSearchTerm={setSearchTerm} />

      <AdminMachinesGrid
        machines={filteredMachines}
        onEdit={handleOpenDialog}
        onRequestDelete={(machine) => {
          setDeletingMachine(machine);
          setDeleteDialogOpen(true);
        }}
      />

      <MachineFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        editingMachine={editingMachine}
        formData={formData}
        setFormData={setFormData}
        onSubmit={handleSubmit}
      />

      <DeleteMachineDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        deletingMachine={deletingMachine}
        onDelete={handleDelete}
      />
    </div>
  );
}
