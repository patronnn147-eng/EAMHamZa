import {
  ChefTechMachinesGrid,
  ChefTechMachinesHeader,
  ChefTechMachinesSearch,
} from './machines/components';
import { useChefTechMachines } from './machines/hooks';

export default function ChefTechMachines() {
  const {
    filteredMachines,
    searchTerm,
    setSearchTerm,
    loading,
  } = useChefTechMachines();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <ChefTechMachinesHeader />

      <ChefTechMachinesSearch searchTerm={searchTerm} setSearchTerm={setSearchTerm} />

      <ChefTechMachinesGrid machines={filteredMachines} />
    </div>
  );
}
