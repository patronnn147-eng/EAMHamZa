import React from 'react';
import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';

interface WorkOrdersHeaderProps {
  onCreate: () => void;
  canCreate: boolean;
}

export const WorkOrdersHeader: React.FC<WorkOrdersHeaderProps> = ({ onCreate, canCreate }) => {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h2 className="text-4xl font-bold text-white">Work Orders</h2>
        <p className="mt-1 text-sm text-blue-200">Manage and track all maintenance work orders</p>
      </div>
      {canCreate ? (
        <Button onClick={onCreate} className="bg-blue-600 hover:bg-blue-700 text-white font-medium">
          <Plus className="mr-2 h-4 w-4" />
          Create Work Order
        </Button>
      ) : null}
    </div>
  );
};
