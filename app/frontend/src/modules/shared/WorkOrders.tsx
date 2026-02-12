import { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { client } from '@/lib/api';
import {
  DeleteWorkOrderDialog,
  WorkOrderFormDialog,
  WorkOrdersFilters,
  WorkOrdersHeader,
  WorkOrdersList,
} from './work-orders/components';
import { useWorkOrders } from './work-orders/hooks';
import type { Planning, OrdreTravail } from '@/lib/types';
import { WorkOrderDetailsDialog } from './work-orders/components/WorkOrderDetailsDialog';

export default function WorkOrders() {
  const { user } = useAuth();
  const [plannings, setPlannings] = useState<Planning[]>([]);
  const [attachments, setAttachments] = useState<File[]>([]);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [detailsWorkOrder, setDetailsWorkOrder] = useState<OrdreTravail | null>(null);

  const canManage = user?.role === 'ADMIN' || user?.role === 'CHETOP' || user?.role === 'CHEFOP';

  const clearAttachments = () => setAttachments([]);
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
  } = useWorkOrders({ attachments, clearAttachments, userRole: user?.role });

  useEffect(() => {
    const fetchPlannings = async () => {
      try {
        const resp = await client.apiCall.invoke({
          url: '/api/v1/plannings?skip=0&limit=100',
          method: 'GET',
        });

        const unwrap = (value: unknown): unknown => {
          let current = value;
          for (let i = 0; i < 5; i += 1) {
            if (!current || typeof current !== 'object') return current;
            const obj = current as Record<string, unknown>;

            if ('items' in obj && Array.isArray(obj.items)) return current;
            if ('data' in obj) {
              current = obj.data;
              continue;
            }
            return current;
          }
          return current;
        };

        const maybeWrapped = (resp as { data?: unknown } | undefined)?.data;
        const extracted = unwrap(maybeWrapped) as { items?: Planning[] } | Planning[] | undefined;
        const items = Array.isArray(extracted) ? extracted : extracted?.items || [];
        setPlannings(items);
      } catch (error) {
        console.error('Error fetching plannings:', error);
      }
    };
    fetchPlannings();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <WorkOrdersHeader onCreate={() => handleOpenDialog()} canCreate={canManage} />

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
        canEdit={canManage}
        canDelete={canManage}
        onViewDetails={(wo) => {
          setDetailsWorkOrder(wo);
          setDetailsOpen(true);
        }}
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
        plannings={plannings}
        attachments={attachments}
        setAttachments={setAttachments}
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

      <WorkOrderDetailsDialog
        open={detailsOpen}
        onOpenChange={setDetailsOpen}
        workOrder={detailsWorkOrder}
        machines={machines}
      />
    </div>
  );
}