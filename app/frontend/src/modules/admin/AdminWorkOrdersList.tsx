import React, { useEffect, useState } from 'react';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Eye, Calendar, User, Search } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { PriorityBadge, StatusBadge } from '@/modules/shared/work-orders/utils/badges';

import type { Machine, OrdreTravail } from '@/lib/types';
import { useNavigate } from 'react-router-dom';
import ChetopValidationQueue from './ChetopValidationQueue';

export default function AdminWorkOrdersList() {
  const navigate = useNavigate();
  const [workOrders, setWorkOrders] = useState<OrdreTravail[]>([]);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [priorityFilter, setPriorityFilter] = useState('ALL');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [voRes, mRes] = await Promise.all([
          client.entities.ordres_travail.query({ sort: '-created_at', limit: 200 }),
          client.entities.machines.query({ limit: 1000 })
        ]);
        setWorkOrders(voRes.data.items || []);
        setMachines(mRes.data.items || []);
      } catch (error) {
        console.error('Failed to fetch admin work orders data:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const getMachineName = (id?: number) => {
    if (!id) return 'Unknown Machine';
    const m = machines.find((m) => m.id === id);
    return m ? m.nom : `Machine #${id}`;
  };

  const filtered = workOrders.filter((wo) => {
    const matchesSearch = wo.titre.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          wo.id.toString().includes(searchTerm);
    const matchesStatus = statusFilter === 'ALL' || wo.statut === statusFilter;
    const matchesPriority = priorityFilter === 'ALL' || wo.priorite === priorityFilter;
    return matchesSearch && matchesStatus && matchesPriority;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* CHETOP Admin Validation Queue - Phase 3 */}
      <ChetopValidationQueue />

      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Administration des Ordres de Travail</h1>
          <p className="text-blue-300 mt-2">
            Vue globale des ordres de travail (générés par les Chefs d'Opérations et validés par les Chefs Techniques).
          </p>
        </div>
      </div>

      <div className="flex flex-col md:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-blue-400" />
          <Input
            placeholder="Rechercher (Titre, ID)..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="w-full md:w-64">
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger>
              <SelectValue placeholder="Tous les statuts" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">Tous les statuts</SelectItem>
              <SelectItem value="EN_ATTENTE">En attente</SelectItem>
              <SelectItem value="PENDING_ADMIN_VALIDATION">En attente validation ADMIN</SelectItem>
              <SelectItem value="ASSIGNE">Assigné</SelectItem>
              <SelectItem value="EN_COURS">En cours</SelectItem>
              <SelectItem value="TERMINE">Terminé</SelectItem>
              <SelectItem value="REJETE">Rejeté</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="w-full md:w-64">
          <Select value={priorityFilter} onValueChange={setPriorityFilter}>
            <SelectTrigger>
              <SelectValue placeholder="Toutes les priorités" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">Toutes les priorités</SelectItem>
              <SelectItem value="BASSE">Basse</SelectItem>
              <SelectItem value="MOYENNE">Moyenne</SelectItem>
              <SelectItem value="ELEVEE">Élevée</SelectItem>
              <SelectItem value="CRITIQUE">Critique</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {filtered.map((wo) => {
          const isPreventive = wo.titre.startsWith('[PRÉVENTIF]');

          let sourceLabel: string;
          if (wo.created_by_role === 'CHETOP') {
            sourceLabel = 'CHETOP (En attente ADMIN)';
          } else if (wo.utilisateur_id) {
            sourceLabel = 'ChefTech (Validation)';
          } else {
            sourceLabel = 'Généré Automatiquement';
          }

          return (
            <Card key={wo.id} className={`hover:shadow-md transition-shadow ${isPreventive ? 'border-amber-200' : ''}`}>
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg flex items-center gap-2">
                      Ordre #{wo.id} - {wo.titre}
                    </CardTitle>
                    <p className="text-sm text-blue-300 mt-1">{getMachineName(wo.machine_id)}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <PriorityBadge priorite={wo.priorite} />
                    <StatusBadge statut={wo.statut} />
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm mb-4">
                  <div>
                    <p className="text-blue-300 flex items-center gap-1">
                      <Calendar className="h-4 w-4" /> Date Cible
                    </p>
                    <p className="font-medium mt-1">
                      {wo.date_echeance ? new Date(wo.date_echeance).toLocaleDateString() : 'Non définie'}
                    </p>
                  </div>
                  <div>
                    <p className="text-blue-300 flex items-center gap-1">
                      <Calendar className="h-4 w-4" /> Créé le
                    </p>
                    <p className="font-medium mt-1">
                      {new Date(wo.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div>
                    <p className="text-blue-300 flex items-center gap-1">
                      <User className="h-4 w-4" /> Source
                    </p>
                    <p className="font-medium mt-1">
                      {sourceLabel}
                    </p>
                  </div>
                </div>
                <div className="flex justify-end pt-2 border-t mt-4">
                  <Button
                    variant="default"
                    size="sm"
                    onClick={() => navigate(`/work-orders/${wo.id}`)}
                  >
                    <Eye className="mr-2 h-4 w-4" />
                    Voir les Détails
                  </Button>
                </div>
              </CardContent>
            </Card>
          );
        })}
        {filtered.length === 0 && (
          <div className="text-center py-12 text-blue-300 bg-slate-800/50 rounded-lg border">
            Aucun ordre de travail ne correspond à vos filtres.
          </div>
        )}
      </div>
    </div>
  );
}
