import React from 'react';
import { Input } from '@/components/ui/input';
import { Search } from 'lucide-react';

interface MachinesSearchProps {
  searchTerm: string;
  setSearchTerm: (value: string) => void;
}

export const MachinesSearch: React.FC<MachinesSearchProps> = ({ searchTerm, setSearchTerm }) => {
  return (
    <div className="relative">
      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
      <Input
        type="text"
        placeholder="Search machines by name, ID, location, or type..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        className="pl-10"
      />
    </div>
  );
};
