import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { 
  Check, 
  X, 
  Clock, 
  Search,
  MessageSquare
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";

interface ItvRequest {
  id: number;
  machine_id: number;
  machine_nom: string;
  priorite: string;
  description: string;
  statut: string;
  requested_at: string;
  requested_by_nom: string;
}

const AdminItvApprovals: React.FC = () => {
  const { toast } = useToast();
  const [requests, setRequests] = useState<ItvRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [selectedRequestId, setSelectedRequestId] = useState<number | null>(null);
  const [rejectionReason, setRejectionReason] = useState('');

  const fetchRequests = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const apiBase = import.meta.env.VITE_API_BASE_URL || '';
      const response = await fetch(`${apiBase}/api/v1/admin/itv-requests`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setRequests(data.items || data || []);
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

  const handleValidate = async (id: number, status: 'APPROVED' | 'REJECTED', reason?: string) => {
    try {
      const token = localStorage.getItem('access_token');
      const apiBase = import.meta.env.VITE_API_BASE_URL || '';
      const response = await fetch(`${apiBase}/api/v1/admin/itv-requests/${id}/validate`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ status, rejection_reason: reason })
      });

      if (response.ok) {
        const result = await response.json();
        toast({ 
          title: status === 'ACCEPTED' ? "Demande Approuvée" : "Demande Rejetée",
          description: status === 'ACCEPTED' ? "Un ordre de travail a été créé automatiquement." : "Le demandeur sera notifié."
        });
        await fetchRequests();
        setTimeout(() => fetchRequests(), 500);
      } else {
        const error = await response.json();
        toast({
          title: "Erreur",
          description: error.detail || "Échec de la validation",
          variant: 'destructive'
        });
      }
    } catch (error) {
      console.error('Error validating request:', error);
      toast({
        title: "Erreur",
        description: "Une erreur est survenue lors de la validation",
        variant: 'destructive'
      });
    }
  };

  const openRejectModal = (id: number) => {
    setSelectedRequestId(id);
    setRejectModalOpen(true);
  };

  const filteredRequests = requests.filter(req => 
    req.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    req.machine_nom?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    req.requested_by_nom?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-8 animate-premium-fade-in bg-transparent">
      <div className="max-w-7xl mx-auto space-y-8">
        <div>
          <h1 className="text-4xl font-black text-white tracking-tight mb-2">Approbations ITV</h1>
          <p className="text-blue-300 font-medium border-l-4 border-violet-500 pl-4 py-1">
            Validez ou rejetez les demandes d'intervention des Chefs d'Opérations.
          </p>
        </div>

        <div className="relative group">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-blue-400 group-focus-within:text-violet-500 transition-colors" />
          <Input
            placeholder="Rechercher par description, machine ou demandeur..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-12 py-6 bg-white/50 backdrop-blur-sm border-blue-700/50 rounded-2xl focus:ring-2 focus:ring-violet-500/20 transition-all shadow-sm"
          />
        </div>

        <div className="bg-white/80 backdrop-blur-md rounded-[2.5rem] border border-white/20 shadow-2xl overflow-hidden">
          <Table>
            <TableHeader className="bg-slate-800/50/50">
              <TableRow className="border-b border-blue-800/50">
                <TableHead className="font-black py-6 px-6 text-blue-400 uppercase tracking-widest text-[10px]">Demandeur</TableHead>
                <TableHead className="font-black text-blue-400 uppercase tracking-widest text-[10px]">Machine</TableHead>
                <TableHead className="font-black text-blue-400 uppercase tracking-widest text-[10px]">Priorité</TableHead>
                <TableHead className="font-black text-blue-400 uppercase tracking-widest text-[10px]">Description</TableHead>
                <TableHead className="font-black text-blue-400 uppercase tracking-widest text-[10px]">Date</TableHead>
                <TableHead className="font-black text-blue-400 uppercase tracking-widest text-[10px] text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-20 text-blue-400 italic font-medium">Récupération des demandes...</TableCell>
                </TableRow>
              ) : filteredRequests.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-20 text-blue-400 font-bold tracking-tight">Aucune demande en attente</TableCell>
                </TableRow>
              ) : filteredRequests.map((req) => (
                <TableRow key={req.id} className="hover:bg-white/50 transition-all group flex-wrap">
                  <TableCell className="py-6 px-6">
                    <div className="font-black text-white">{req.requested_by_nom}</div>
                    <div className="text-[10px] text-blue-400 font-bold uppercase tracking-wider">Chef Opérateur</div>
                  </TableCell>
                  <TableCell>
                    <Badge className="bg-violet-500/10 text-violet-600 border-none px-3 font-bold">{req.machine_nom}</Badge>
                  </TableCell>
                  <TableCell>
                    {req.priorite === 'URGENTE' ? (
                      <Badge className="bg-rose-500 text-white border-none animate-pulse">URGENTE</Badge>
                    ) : (
                      <Badge variant="secondary" className="font-bold">{req.priorite}</Badge>
                    )}
                  </TableCell>
                  <TableCell className="max-w-sm">
                    <div className="text-sm font-medium text-blue-200 leading-relaxed italic border-l-2 border-blue-800/50 pl-3">
                      "{req.description}"
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center text-blue-400 font-bold text-xs gap-1.5">
                      <Clock className="w-3 h-3" />
                      {new Date(req.requested_at).toLocaleDateString()}
                    </div>
                  </TableCell>
                  <TableCell className="text-right px-6">
                    <div className="flex justify-end gap-2 translate-x-4 opacity-0 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300">
                      <Button 
                        size="sm" 
                        onClick={() => handleValidate(req.id, 'APPROVED')}
                        className="bg-emerald-500 hover:bg-emerald-600 text-white rounded-full h-10 w-10 p-0 shadow-lg shadow-emerald-500/20 active:scale-90"
                      >
                        <Check className="w-5 h-5" />
                      </Button>
                      <Button 
                        size="sm" 
                        variant="destructive"
                        onClick={() => openRejectModal(req.id)}
                        className="bg-rose-500 hover:bg-rose-600 text-white rounded-full h-10 w-10 p-0 shadow-lg shadow-rose-500/20 active:scale-90"
                      >
                        <X className="w-5 h-5" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>

      <Dialog open={rejectModalOpen} onOpenChange={setRejectModalOpen}>
        <DialogContent className="sm:max-w-[425px] rounded-[2rem] glass-card border-none p-0 overflow-hidden shadow-2xl">
          <div className="bg-rose-500 p-8 text-white relative">
            <XCircle className="absolute -right-4 -top-4 w-32 h-32 opacity-10" />
            <DialogHeader>
              <DialogTitle className="text-2xl font-black tracking-tight">Rejeter la demande</DialogTitle>
              <p className="text-rose-100 font-medium">Expliquez brièvement pourquoi cette demande est rejetée.</p>
            </DialogHeader>
          </div>
          
          <div className="p-8 space-y-6 bg-white/80">
            <div className="space-y-3">
              <Label className="text-[10px] font-black uppercase tracking-widest text-blue-400">Motif de rejet</Label>
              <div className="relative">
                <MessageSquare className="absolute left-4 top-4 w-4 h-4 text-gray-300" />
                <Textarea 
                  placeholder="Ex: Machine déjà planifiée pour demain, pièces manquantes..." 
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  className="min-h-[120px] bg-slate-800/50/50 border-blue-800/50 rounded-2xl pl-11 py-4 font-medium leading-relaxed focus:ring-violet-500/20 focus:border-violet-500/30 transition-all"
                />
              </div>
            </div>

            <DialogFooter className="flex gap-2">
              <Button variant="ghost" onClick={() => setRejectModalOpen(false)} className="rounded-xl font-bold flex-1">
                Annuler
              </Button>
              <Button 
                onClick={() => {
                  if (selectedRequestId) {
                    handleValidate(selectedRequestId, 'REJECTED', rejectionReason);
                    setRejectModalOpen(false);
                    setRejectionReason('');
                  }
                }}
                disabled={!rejectionReason}
                className="bg-rose-500 hover:bg-rose-600 text-white rounded-xl font-black px-8 flex-1 active:scale-95 disabled:grayscale transition-all"
              >
                Confirmer le rejet
              </Button>
            </DialogFooter>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

const XCircle = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor font-sans">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

export default AdminItvApprovals;
