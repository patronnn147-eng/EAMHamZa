import React from 'react';
import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';

interface InterventionsHeaderProps {
  onCreate: () => void;
}

export const InterventionsHeader: React.FC<InterventionsHeaderProps> = ({ onCreate }) => {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Interventions</h2>
        <p className="mt-1 text-sm text-gray-500">Track and document all maintenance interventions</p>
      </div>
      <Button onClick={onCreate}>
        <Plus className="mr-2 h-4 w-4" />
        Record Intervention
      </Button>
    </div>
  );
};
