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
        <h2 className="text-4xl font-bold text-white">Interventions</h2>
        <p className="mt-1 text-sm text-blue-200">Track and document all maintenance interventions</p>
      </div>
      <Button onClick={onCreate} className="bg-blue-600 hover:bg-blue-700 text-white font-medium">
        <Plus className="mr-2 h-4 w-4" />
        Record Intervention
      </Button>
    </div>
  );
};
