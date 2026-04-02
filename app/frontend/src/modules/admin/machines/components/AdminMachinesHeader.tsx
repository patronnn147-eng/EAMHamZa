import React from 'react';
import { Button } from '@/components/ui/button';
import { Plus, Upload } from 'lucide-react';

interface AdminMachinesHeaderProps {
  onCreate: () => void;
  onImport: () => void;
}

export const AdminMachinesHeader: React.FC<AdminMachinesHeaderProps> = ({ onCreate, onImport }) => {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Machines</h2>
        <p className="mt-1 text-sm text-gray-500">Manage and monitor all machines in your facility</p>
      </div>
      <div className="flex items-center gap-2">
        <Button variant="outline" onClick={onImport}>
          <Upload className="mr-2 h-4 w-4" />
          Importer
        </Button>
        <Button onClick={onCreate}>
          <Plus className="mr-2 h-4 w-4" />
          Nouvelle Machine
        </Button>
      </div>
    </div>
  );
};
