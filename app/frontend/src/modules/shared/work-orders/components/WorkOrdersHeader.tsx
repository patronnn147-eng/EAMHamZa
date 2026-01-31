import React from 'react';
import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';

interface WorkOrdersHeaderProps {
  onCreate: () => void;
}

export const WorkOrdersHeader: React.FC<WorkOrdersHeaderProps> = ({ onCreate }) => {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Work Orders</h2>
        <p className="mt-1 text-sm text-gray-500">Manage and track all maintenance work orders</p>
      </div>
      <Button onClick={onCreate}>
        <Plus className="mr-2 h-4 w-4" />
        Create Work Order
      </Button>
    </div>
  );
};
