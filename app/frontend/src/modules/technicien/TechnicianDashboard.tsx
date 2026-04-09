import { useEffect, useMemo, useState } from 'react';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Calendar, AlertTriangle, CheckCircle, Clock, Wrench } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useToast } from '@/hooks/use-toast';
import type { Intervention, OrdreTravail, Machine } from '@/lib/types';
import { InterventionRequestDialog } from './components/InterventionRequestDialog';

export default function TechnicianDashboard() {
  const { toast } = useToast();
  const [workOrders, setWorkOrders] = useState<OrdreTravail[]>([]);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [interventions, setInterventions] = useState<Intervention[]>([]);
  const [loading, setLoading] = useState(true);
  const [requestOpen, setRequestOpen] = useState(false);
  const [selectedOrdreId, setSelectedOrdreId] = useState<number>(0);
  const [selectedMachineId, setSelectedMachineId] = useState<number | null>(null);

  const [stats, setStats] = useState({
    total: 0,
    enCours: 0,
    enAttente: 0,
    termine: 0,
    urgent: 0,
  });
  const navigate = useNavigate();

  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  const formatDuration = (ms: number) => {
    const totalSeconds = Math.max(0, Math.floor(ms / 1000));
    const h = Math.floor(totalSeconds / 3600);
    const m = Math.floor((totalSeconds % 3600) / 60);
    const s = totalSeconds % 60;
    const pad = (n: number) => n.toString().padStart(2, '0');
    return `${pad(h)}:${pad(m)}:${pad(s)}`;
  };

  const getElapsedMs = (i: Intervention) => {
    const status = i.statut || 'EN_ATTENTE';
    const startIso = i.date_debut || (status === 'APPROVED' ? i.approved_at : undefined);
    const start = startIso ? new Date(startIso).getTime() : null;
    if (!start) return 0;
    const end = i.date_fin ? new Date(i.date_fin).getTime() : now;
    return Math.max(0, end - start);
  };

  const activeInterventions = useMemo(
    () =>
      interventions.filter((i) => {
        const s = i.statut || 'EN_ATTENTE';
        return s === 'APPROVED' || s === 'VALIDE' || s === 'EN_COURS' || s === 'BLOQUÉ';
      }),
    [interventions],
  );

  const overdueInterventions = useMemo(() => interventions.filter((i) => i.is_overdue), [interventions]);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const user = await client.auth.me();
      if (!user.data) return;

      // Fetch work orders assigned to current technician
      const [ordresResponse, machinesResponse] = await Promise.all([
        client.entities.ordres_travail.query({
          query: { utilisateur_id: user.data.id },
          sort: '-priorite,-date_echeance',
          limit: 100,
        }),
        client.entities.machines.queryAll({
          query: {},
          limit: 100,
        }),
      ]);

      const ordresList = ordresResponse.data.items || [];
      const machinesList = machinesResponse.data.items || [];

      setWorkOrders(ordresList);
      setMachines(machinesList);

      try {
        const token = localStorage.getItem('access_token');
        if (token) {
          const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/technicien/interventions`, {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          });
          if (res.ok) {
            const ints = await res.json();
            setInterventions(Array.isArray(ints) ? ints : []);
          }
        }
      } catch {
        // ignore
      }

      // Calculate stats
      const statsData = {
        total: ordresList.length,
        enCours: ordresList.filter((o) => o.statut === 'EN_COURS' || o.statut === 'VALIDE').length,
        enAttente: ordresList.filter((o) => o.statut === 'EN_ATTENTE').length,
        termine: ordresList.filter((o) => o.statut === 'TERMINE' || o.statut === 'TERMINÉ').length,
        urgent: ordresList.filter((o) => o.priorite === 'URGENTE').length,
      };
      setStats(statsData);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    for (const i of overdueInterventions) {
      const key = `overdue_intervention_alert_${i.id}`;
      if (localStorage.getItem(key)) continue;
      localStorage.setItem(key, '1');
      toast({
        title: 'Échéance dépassée',
        description: `Intervention #${i.id} (OT #${i.ordre_travail_id}) a dépassé la date d'échéance.`,
        variant: 'destructive',
      });
    }
  }, [overdueInterventions, toast]);

  const getMachineInfo = (machineId: number) => {
    return machines.find((m) => m.id === machineId);
  };

  const getPriorityColor = (priorite: string) => {
    switch (priorite) {
      case 'URGENTE':
        return 'bg-gradient-to-r from-red-600 to-rose-600 text-white shadow-[0_2px_8px_rgba(225,29,72,0.3)] border-none px-3 py-1';
      case 'HAUTE':
        return 'bg-gradient-to-r from-orange-500 to-amber-500 text-white shadow-[0_2px_8px_rgba(245,158,11,0.3)] border-none px-3 py-1';
      case 'MOYENNE':
        return 'bg-gradient-to-r from-yellow-400 to-orange-400 text-white border-none px-3 py-1';
      default:
        return 'bg-gray-200 text-blue-100 font-bold px-3 py-1';
    }
  };

  const getStatusColor = (statut: string) => {
    const base = "rounded-full px-4 py-1.5 text-[11px] font-black uppercase tracking-widest border transition-all duration-300 ";
    switch (statut) {
      case 'EN_COURS':
        return base + 'text-blue-700 bg-blue-50/50 border-blue-200/50 animate-pulse shadow-[0_0_12px_rgba(59,130,246,0.2)]';
      case 'VALIDE':
        return base + 'text-emerald-700 bg-emerald-50/50 border-emerald-200/50 shadow-[0_0_10px_rgba(16,185,129,0.1)]';
      case 'EN_ATTENTE':
        return base + 'text-amber-700 bg-amber-50/50 border-amber-200/50';
      case 'TERMINE':
      case 'TERMINÉ':
        return base + 'text-emerald-800 bg-emerald-100/50 border-emerald-300/50';
      default:
        return base + 'text-blue-200 bg-slate-800/50/50 border-blue-700/50/50';
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
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-4xl font-bold text-white">Tableau de Bord Technicien</h2>
          <p className="mt-1 text-sm text-blue-300">Vue d'ensemble de vos tâches et interventions</p>
        </div>
        <Button 
          variant="destructive" 
          className="flex items-center gap-2 shadow-lg hover:scale-105 transition-transform"
          onClick={() => {
            if (workOrders.length > 0) {
              setSelectedOrdreId(workOrders[0].id);
              setSelectedMachineId(workOrders[0].machine_id);
              setRequestOpen(true);
            } else {
              toast({
                title: "Aucun OT",
                description: "Vous devez avoir au moins un Ordre de Travail assigné pour demander une intervention.",
                variant: "destructive"
              });
            }
          }}
        >
          <AlertTriangle className="h-4 w-4" />
          Besoin d'aide / Alerte
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
        <Card className="border-none shadow-lg hover:shadow-xl transition-all duration-300 bg-slate-800 dark:bg-slate-900 group">
          <CardHeader className="pb-2">
            <CardTitle className="text-[11px] font-bold text-blue-400 uppercase tracking-widest">Total</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-black text-white dark:text-white transition-transform group-hover:scale-110 origin-left duration-300">{stats.total}</div>
            <p className="text-[11px] font-medium text-blue-300 mt-1">Ordres de travail</p>
          </CardContent>
        </Card>

        <Card className="border-none shadow-lg hover:shadow-xl transition-all duration-300 bg-slate-800 dark:bg-slate-900 group">
          <CardHeader className="pb-2">
            <CardTitle className="text-[11px] font-bold text-blue-400 uppercase tracking-widest">En Cours</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-black text-blue-600 transition-transform group-hover:scale-110 origin-left duration-300">{stats.enCours}</div>
            <p className="text-[11px] font-medium text-blue-300 mt-1">Interventions actives</p>
          </CardContent>
        </Card>

        <Card className="border-none shadow-lg hover:shadow-xl transition-all duration-300 bg-slate-800 dark:bg-slate-900 group">
          <CardHeader className="pb-2">
            <CardTitle className="text-[11px] font-bold text-blue-400 uppercase tracking-widest">En Attente</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-black text-amber-500 transition-transform group-hover:scale-110 origin-left duration-300">{stats.enAttente}</div>
            <p className="text-[11px] font-medium text-blue-300 mt-1">À démarrer</p>
          </CardContent>
        </Card>

        <Card className="border-none shadow-lg hover:shadow-xl transition-all duration-300 bg-slate-800 dark:bg-slate-900 group">
          <CardHeader className="pb-2">
            <CardTitle className="text-[11px] font-bold text-blue-400 uppercase tracking-widest">Terminés</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-black text-emerald-500 transition-transform group-hover:scale-110 origin-left duration-300">{stats.termine}</div>
            <p className="text-[11px] font-medium text-blue-300 mt-1">Complétés</p>
          </CardContent>
        </Card>

        <Card className="border-none shadow-lg hover:shadow-xl transition-all duration-300 bg-slate-800 dark:bg-slate-900 group border-l-4 border-red-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-[11px] font-bold text-blue-400 uppercase tracking-widest text-red-500">Urgent</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-black text-red-600 transition-transform group-hover:scale-110 origin-left duration-300">{stats.urgent}</div>
            <p className="text-[11px] font-medium text-blue-300 mt-1">Priorité haute</p>
          </CardContent>
        </Card>
      </div>

      {/* Work Orders List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Mes Ordres de Travail</CardTitle>
            <Button onClick={() => navigate('/technician/work-orders')} className="bg-blue-600 hover:bg-blue-700 text-white">Voir Tout</Button>
          </div>
        </CardHeader>
        <CardContent>
          {workOrders.length === 0 ? (
            <div className="text-center py-8 text-blue-300">
              <Wrench className="mx-auto h-12 w-12 mb-2 opacity-50" />
              <p>Aucun ordre de travail assigné</p>
            </div>
          ) : (
            <div className="space-y-3">
              {workOrders.slice(0, 5).map((ordre) => {
                const machine = getMachineInfo(ordre.machine_id);
                return (
                  <div
                    key={ordre.id}
                    className={`p-6 border-none rounded-2xl shadow-sm hover:shadow-xl transition-all duration-300 cursor-pointer animate-premium-fade-in group relative overflow-hidden ${
                      ordre.priorite === 'URGENTE' ? 'bg-red-50/50 dark:bg-red-950/20 ring-1 ring-red-200' : 'bg-slate-800 dark:bg-slate-900'
                    }`}
                    onClick={() => navigate(`/technician/work-orders/${ordre.id}`)}
                  >
                    <div className="absolute right-0 top-0 w-32 h-32 bg-gradient-premium opacity-[0.03] -mr-16 -mt-16 rounded-full group-hover:opacity-[0.08] transition-opacity" />
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h3 className="font-semibold text-white">Ordre #{ordre.id}</h3>
                          <Badge className={getPriorityColor(ordre.priorite)}>{ordre.priorite}</Badge>
                          <Badge className={getStatusColor(ordre.statut)}>
                            {ordre.statut === 'VALIDE' ? 'PRÊT / VALIDÉ' : ordre.statut}
                          </Badge>
                        </div>
                        {machine && (
                          <p className="text-sm text-blue-200 mb-1">
                            Machine: {machine.nom} (#{machine.id})
                          </p>
                        )}
                        <div className="flex items-center gap-4 text-xs text-blue-300">
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            Échéance: {new Date(ordre.date_echeance).toLocaleDateString()}
                          </span>
                          {ordre.priorite === 'URGENTE' && (
                            <span className="flex items-center gap-1 text-red-600">
                              <AlertTriangle className="h-3 w-3" />
                              Urgent
                            </span>
                          )}
                        </div>
                      </div>
                      {ordre.statut === 'EN_COURS' && (
                        <Clock className="h-5 w-5 text-blue-600 animate-pulse" />
                      )}
                      {ordre.statut === 'TERMINE' && <CheckCircle className="h-5 w-5 text-green-600" />}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Active Interventions Chrono */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Chrono Interventions</CardTitle>
            <Button onClick={() => navigate('/technician/interventions')} className="bg-blue-600 hover:bg-blue-700 text-white">Voir Tout</Button>
          </div>
        </CardHeader>
        <CardContent>
          {activeInterventions.length === 0 ? (
            <div className="text-sm text-blue-300">Aucune intervention approuvée / en cours</div>
          ) : (
            <div className="space-y-3">
              {activeInterventions.slice(0, 5).map((i) => (
                <div key={i.id} className="p-3 border rounded-lg">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="font-medium">Intervention #{i.id}</div>
                      <div className="text-xs text-blue-300">OT #{i.ordre_travail_id}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      {i.is_overdue ? <Badge className="bg-red-100 text-red-800">Overdue</Badge> : null}
                      <Badge variant="outline">{formatDuration(getElapsedMs(i))}</Badge>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
      {/* Request Intervention Dialog */}
      <InterventionRequestDialog
        open={requestOpen}
        onOpenChange={setRequestOpen}
        initialOrdreTravailId={selectedOrdreId}
        initialMachineId={selectedMachineId}
        onSubmit={async (data) => {
          try {
            const token = localStorage.getItem('access_token');
            const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/technicien/interventions/request`, {
              method: 'POST',
              headers: {
                Authorization: `Bearer ${token}`,
                'Content-Type': 'application/json',
              },
              body: JSON.stringify(data),
            });
            if (res.ok) {
              toast({ title: "Demande envoyée", description: "Votre demande d'intervention est en attente de validation." });
              setRequestOpen(false);
              fetchData();
            }
          } catch (e) {
            console.error(e);
          }
        }}
      />
    </div>
  );
}