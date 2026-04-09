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
        <h2 className="text-4xl font-bold text-white">Machines</h2>
        <p className="mt-1 text-sm text-blue-200">Manage and monitor all machines in your facility</p>
      </div>
      <div className="flex items-center gap-2">
        <Button variant="outline" onClick={onImport} className="bg-blue-600 hover:bg-blue-700 text-white font-medium border-blue-500">
          <Upload className="mr-2 h-4 w-4" />
          Importer
        </Button>
        <Button onClick={onCreate} className="bg-blue-600 hover:bg-blue-700 text-white font-medium">
          <Plus className="mr-2 h-4 w-4" />
          Nouvelle Machine
        </Button>
      </div>
    </div>
  );
};
