import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { 
  Plus, 
  Clock, 
  CheckCircle2, 
  XCircle, 
  AlertCircle,
  Search
} from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { useToast } from '@/hooks/use-toast';
import { CreateItvRequestModal } from '@/modules/chetop/components/CreateItvRequestModal';

interface ItvRequest {
  id: number;
  machine_id: number;
  machine_nom: string;
  priorite: string;
  description: string;
  statut: string;
  requested_at: string;
  rejection_reason?: string;
  ordre_travail_id?: number;
}

const ChefOpItvRequests: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [requests, setRequests] = useState<ItvRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const fetchRequests = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const apiBase = import.meta.env.VITE_API_BASE_URL || '';
      const response = await fetch(`${apiBase}/api/v1/chetop/intervention-requests`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setRequests(data);
      }
    } catch (error) {
      console.error('Error fetching requests:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PENDING_APPROVAL':
        return <Badge className="bg-amber-500/10 text-amber-500 border-amber-500/20"><Clock className="w-3 h-3 mr-1" /> En attente d'approbation</Badge>;
      case 'EN_ATTENTE':
        return <Badge className="bg-amber-500/10 text-amber-500 border-amber-500/20"><Clock className="w-3 h-3 mr-1" /> En attente</Badge>;
      case 'APPROVED':
      case 'ACCEPTED':
        return <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20"><CheckCircle2 className="w-3 h-3 mr-1" /> Approuvée</Badge>;
      case 'REJECTED':
      case 'DECLINED':
        return <Badge className="bg-rose-500/10 text-rose-500 border-rose-500/20"><XCircle className="w-3 h-3 mr-1" /> Rejetée</Badge>;
      default:
        return <Badge>{status}</Badge>;
    }
  };

  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case 'URGENTE':
        return <Badge variant="destructive">URGENTE</Badge>;
      case 'ÉLEVÉE':
        return <Badge className="bg-orange-500 text-white border-none">ÉLEVÉE</Badge>;
      default:
        return <Badge variant="secondary">{priority}</Badge>;
    }
  };

  const filteredRequests = requests.filter(req => 
    req.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    req.machine_nom?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-8 animate-premium-fade-in">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex justify-between items-end">
          <div>
            <h1 className="text-3xl font-black text-gray-900 dark:text-white tracking-tight">Demandes d'intervention</h1>
            <p className="text-gray-500 font-medium">Gérez vos demandes et suivez leur approbation par l'admin</p>
          </div>
          <Button 
            onClick={() => setShowModal(true)}
            className="bg-gradient-premium hover:opacity-90 transition-all rounded-xl font-bold py-6 px-6 shadow-lg"
          >
            <Plus className="w-5 h-5 mr-2" /> Nouvelle Demande
          </Button>
        </div>

        <div className="relative group">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400 group-focus-within:text-gradient-premium transition-colors" />
          <Input
            placeholder="Rechercher une demande ou une machine..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-12 py-6 bg-white/50 backdrop-blur-sm border-gray-200 rounded-2xl focus:ring-2 focus:ring-violet-500/20 transition-all shadow-sm"
          />
        </div>

        <div className="bg-white/70 backdrop-blur-md rounded-3xl border border-white/20 shadow-xl overflow-hidden">
          <Table>
            <TableHeader className="bg-gray-50/50">
              <TableRow>
                <TableHead className="font-bold py-5">Machine</TableHead>
                <TableHead className="font-bold">Priorité</TableHead>
                <TableHead className="font-bold">Description</TableHead>
                <TableHead className="font-bold">Date</TableHead>
                <TableHead className="font-bold">Statut</TableHead>
                <TableHead className="font-bold">Notes Admin</TableHead>
                <TableHead className="font-bold text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-12 text-gray-400">Chargement...</TableCell>
                </TableRow>
              ) : filteredRequests.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-12 text-gray-400">Aucune demande trouvée</TableCell>
                </TableRow>
              ) : filteredRequests.map((req) => (
                <TableRow key={req.id} className="hover:bg-gray-50/50 transition-colors">
                  <TableCell className="font-bold py-5">{req.machine_nom}</TableCell>
                  <TableCell>{getPriorityBadge(req.priorite)}</TableCell>
                  <TableCell className="max-w-xs truncate text-gray-600 font-medium">{req.description}</TableCell>
                  <TableCell className="text-gray-500">{new Date(req.requested_at).toLocaleDateString()}</TableCell>
                  <TableCell>{getStatusBadge(req.statut)}</TableCell>
                  <TableCell>
                    {req.rejection_reason && (
                      <div className="flex items-center text-rose-500 text-xs font-bold gap-1 bg-rose-50 p-2 rounded-lg">
                        <AlertCircle className="w-3 h-3" />
                        {req.rejection_reason}
                      </div>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    {req.statut === 'ACCEPTED' && req.ordre_travail_id && (
                      <Button
                          size="sm"
                          variant="outline"
                          className="rounded-full border-emerald-500 text-emerald-600 hover:bg-emerald-50 font-bold"
                          onClick={() => navigate(`/chetop/work-orders/${req.ordre_travail_id}`)}
                        >
                          Voir l'Ordre
                        </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>

      <CreateItvRequestModal 
        open={showModal} 
        onOpenChange={(open) => setShowModal(open)} 
        onSuccess={() => {
          setShowModal(false);
          fetchRequests();
          toast({ title: "Succès", description: "Demande envoyée avec succès" });
        }}
      />
    </div>
  );
};

export default ChefOpItvRequests;
