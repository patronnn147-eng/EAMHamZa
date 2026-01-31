import React from 'react';
import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';

interface MachinesHeaderProps {
  onCreate: () => void;
  canCreate?: boolean;
}

export const MachinesHeader: React.FC<MachinesHeaderProps> = ({ onCreate, canCreate = true }) => {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Machines</h2>
        <p className="mt-1 text-sm text-gray-500">Manage and monitor all machines in your facility</p>
      </div>
      {canCreate && (
        <Button onClick={onCreate}>
          <Plus className="mr-2 h-4 w-4" />
          Add Machine
        </Button>
      )}
    </div>
  );
};
