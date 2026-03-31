import React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { 
  Clock, 
  CheckCircle2, 
  XCircle,
  AlertCircle
} from 'lucide-react';
import type { InterventionRequest } from '../types';

interface InterventionRequestsTabProps {
  requests: InterventionRequest[];
}

export const InterventionRequestsTab: React.FC<InterventionRequestsTabProps> = ({ requests }) => {
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'EN_ATTENTE':
        return <Badge className="bg-amber-500/10 text-amber-500 border-amber-500/20"><Clock className="w-3 h-3 mr-1" /> En attente</Badge>;
      case 'ACCEPTED':
        return <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20"><CheckCircle2 className="w-3 h-3 mr-1" /> Approuvée</Badge>;
      case 'REJECTED':
        return <Badge className="bg-rose-500/10 text-rose-500 border-rose-500/20"><XCircle className="w-3 h-3 mr-1" /> Rejetée</Badge>;
      default:
        return <Badge>{status}</Badge>;
    }
  };

  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case 'URGENTE':
        return <Badge variant="destructive" className="font-bold">URGENTE</Badge>;
      case 'ÉLEVÉE':
        return <Badge className="bg-orange-500 text-white border-none font-bold">ÉLEVÉE</Badge>;
      default:
        return <Badge variant="secondary" className="font-bold">{priority}</Badge>;
    }
  };

  return (
    <Card className="border-none shadow-2xl bg-white/80 backdrop-blur-md rounded-[2.5rem] overflow-hidden">
      <div className="p-8 border-b border-gray-100/50 bg-gray-50/30 flex justify-between items-center">
        <h3 className="text-xl font-black text-gray-900 tracking-tight">Demandes Récentes</h3>
        <p className="text-xs font-bold text-gray-400 uppercase tracking-widest">Suivi en temps réel</p>
      </div>
      <Table>
        <TableHeader className="bg-gray-50/50">
          <TableRow className="border-b border-gray-100">
            <TableHead className="py-6 px-8 font-black text-[10px] uppercase tracking-widest text-gray-400">Machine</TableHead>
            <TableHead className="font-black text-[10px] uppercase tracking-widest text-gray-400">Priorité</TableHead>
            <TableHead className="font-black text-[10px] uppercase tracking-widest text-gray-400">Description</TableHead>
            <TableHead className="font-black text-[10px] uppercase tracking-widest text-gray-400">Date</TableHead>
            <TableHead className="font-black text-[10px] uppercase tracking-widest text-gray-400">Statut</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {requests.length === 0 ? (
            <TableRow>
              <TableCell colSpan={5} className="text-center py-20 text-gray-400 italic">Aucune demande récente</TableCell>
            </TableRow>
          ) : (
            requests.map((req) => (
              <TableRow key={req.id} className="hover:bg-gray-50/50 transition-all border-b border-gray-50/50">
                <TableCell className="py-6 px-8 font-black text-gray-900">{req.machine_nom || 'N/A'}</TableCell>
                <TableCell>{getPriorityBadge(req.priorite)}</TableCell>
                <TableCell className="max-w-md">
                  <p className="text-sm font-medium text-gray-600 truncate">{req.description}</p>
                </TableCell>
                <TableCell className="text-gray-400 font-bold text-xs">
                  {new Date(req.requested_at).toLocaleDateString()}
                </TableCell>
                <TableCell>{getStatusBadge(req.statut)}</TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </Card>
  );
};
