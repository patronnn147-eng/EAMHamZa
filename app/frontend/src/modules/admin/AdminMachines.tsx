import {
  AdminMachinesGrid,
  AdminMachinesHeader,
  AdminMachinesSearch,
  DeleteMachineDialog,
  MachineFormDialog,
  MachineImportDialog,
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
    importDialogOpen,
    setImportDialogOpen,
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
    fleetPredictions,
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
      <AdminMachinesHeader 
        onCreate={() => handleOpenDialog()} 
        onImport={() => setImportDialogOpen(true)}
      />

      <AdminMachinesSearch searchTerm={searchTerm} setSearchTerm={setSearchTerm} />

      <AdminMachinesGrid
        machines={filteredMachines}
        fleetPredictions={fleetPredictions}
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

      <MachineImportDialog
        open={importDialogOpen}
        onOpenChange={setImportDialogOpen}
        onSuccess={() => {}}
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
