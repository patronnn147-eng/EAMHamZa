import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Search, MapPin, Wrench } from 'lucide-react';
import type { Machine } from '@/lib/types';
import { AppPagination } from '@/components/shared/AppPagination';

export default function TechnicianMachines() {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [filteredMachines, setFilteredMachines] = useState<Machine[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [pageSize] = useState(1200);
  const navigate = useNavigate();

  useEffect(() => {
    fetchData();
  }, [page]);

  useEffect(() => {
    if (searchTerm) {
      const filtered = machines.filter(
        (m) =>
          m.nom.toLowerCase().includes(searchTerm.toLowerCase()) ||
          (m.emplacement || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
          (m.zone || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
          (m.sous_zone || '').toLowerCase().includes(searchTerm.toLowerCase())
      );
      setFilteredMachines(filtered);
    } else {
      setFilteredMachines(machines);
    }
  }, [searchTerm, machines]);

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const apiBase = import.meta.env.VITE_API_BASE_URL || '';
      const response = await fetch(`${apiBase}/api/v1/technicien/machines`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!response.ok) throw new Error('Failed to fetch machines');
      const machinesList = await response.json();
      setMachines(machinesList);
      setFilteredMachines(machinesList);
      setTotalPages(1);
    } catch (error) {
      console.error('Error fetching machines:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (statut: string) => {
    const base = "rounded-full px-4 py-1.5 text-[11px] font-black uppercase tracking-widest border transition-all duration-300 ";
    switch (statut) {
      case 'OPERATIONNELLE':
        return base + 'text-green-700 bg-green-50/50 border-green-200/50 shadow-[0_0_10px_rgba(34,197,94,0.2)]';
      case 'EN_MAINTENANCE':
        return base + 'text-yellow-700 bg-yellow-50/50 border-yellow-200/50';
      case 'EN_PANNE':
        return base + 'text-red-700 bg-red-50/50 border-red-200/50';
      case 'HORS_SERVICE':
        return base + 'text-blue-200 bg-slate-800/50 border-blue-700/50';
      default:
        return base + 'text-blue-200 bg-slate-800/50 border-blue-700/50';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-4xl font-bold text-white">Machines</h2>
        <p className="mt-1 text-sm text-blue-300">Consultez les informations des équipements</p>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-blue-400" />
        <Input
          type="text"
          placeholder="Rechercher par nom ou emplacement..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-10"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredMachines.length === 0 ? (
          <Card className="col-span-full bg-slate-800/80 backdrop-blur-md border border-blue-800/30 shadow-xl">
            <CardContent className="text-center py-12">
              <p className="text-blue-300">Aucune machine trouvée</p>
            </CardContent>
          </Card>
        ) : (
          filteredMachines.map((machine) => (
            <Card key={machine.id} className="bg-slate-800/80 backdrop-blur-md border border-blue-800/30 hover:shadow-xl hover:border-blue-700/50 transition-all">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg">{machine.nom}</CardTitle>
                    <p className="text-sm text-blue-300 mt-1">#{machine.id}</p>
                  </div>
                  <Badge className={getStatusColor(machine.statut)}>{machine.statut}</Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-sm text-blue-200">
                    <MapPin className="h-4 w-4" />
                    <span>{machine.emplacement}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-blue-200">
                    <Wrench className="h-4 w-4" />
                    <span>{machine.type}</span>
                  </div>
                  {(machine.zone || machine.sous_zone) && (
                    <div className="flex items-center gap-2 text-sm text-blue-200">
                      <span className="font-medium">Zone:</span>
                      <span>
                        {[machine.zone, machine.sous_zone].filter(Boolean).join(' / ')}
                      </span>
                    </div>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full"
                    onClick={() => navigate(`/technician/machines/${machine.id}`)}
                  >
                    Voir Détails
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      <div className="flex justify-end mt-4">
        <AppPagination
          currentPage={page}
          totalPages={totalPages}
          onPageChange={setPage}
        />
      </div>
    </div>
  );
}