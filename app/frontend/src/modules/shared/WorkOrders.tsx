import { useAuth } from '@/contexts/AuthContext';
import {
  DeleteWorkOrderDialog,
  WorkOrderFormDialog,
  WorkOrdersFilters,
  WorkOrdersHeader,
  WorkOrdersList,
} from './work-orders/components';
import { useWorkOrders } from './work-orders/hooks';

export default function WorkOrders() {
  const { user } = useAuth();
  const {
    machines,
    filteredWorkOrders,
    loading,
    searchTerm,
    setSearchTerm,
    statusFilter,
    setStatusFilter,
    priorityFilter,
    setPriorityFilter,
    dialogOpen,
    setDialogOpen,
    deleteDialogOpen,
    setDeleteDialogOpen,
    editingWorkOrder,
    deletingWorkOrder,
    setDeletingWorkOrder,
    formData,
    setFormData,
    handleOpenDialog,
    handleSubmit,
    handleDelete,
  } = useWorkOrders();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <WorkOrdersHeader onCreate={() => handleOpenDialog()} />

      <WorkOrdersFilters
        searchTerm={searchTerm}
        setSearchTerm={setSearchTerm}
        statusFilter={statusFilter}
        setStatusFilter={setStatusFilter}
        priorityFilter={priorityFilter}
        setPriorityFilter={setPriorityFilter}
      />

      <WorkOrdersList
        workOrders={filteredWorkOrders}
        machines={machines}
        isAdmin={user?.role === 'ADMIN'}
        onEdit={handleOpenDialog}
        onRequestDelete={(wo) => {
          setDeletingWorkOrder(wo);
          setDeleteDialogOpen(true);
        }}
      />

      <WorkOrderFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        editingWorkOrder={editingWorkOrder}
        machines={machines}
        formData={formData}
        setFormData={setFormData}
        onSubmit={handleSubmit}
      />

      <DeleteWorkOrderDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        deletingWorkOrder={deletingWorkOrder}
        onDelete={handleDelete}
      />
    </div>
  );
}