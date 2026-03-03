import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
    ClipboardList,
    CheckCircle2,
    PlayCircle,
    Search,
    ArrowRight,
    AlertCircle,
    Clock,
    ExternalLink,
    RefreshCcw,
    Activity
} from 'lucide-react';
import { client } from '@/lib/api';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';

interface KanbanItem {
    id: string | number;
    title: string;
    subtitle: string;
    machineId: number;
    machineName: string;
    priority: string;
    riskLevel?: string;
    phase: 'PLAN' | 'DO' | 'CHECK' | 'ACT';
    type: 'PREDICTION' | 'WORK_ORDER' | 'INTERVENTION';
    date: string;
}

export const PDCACanbanBoard = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [items, setItems] = useState<KanbanItem[]>([]);

    const fetchData = async () => {
        setLoading(true);
        try {
            // 1. Fetch Plan Phase (High/Critical Predictions from Fleet Dashboard)
            const fleetRes = await client.apiCall.invoke({
                url: '/api/v1/ml/fleet/dashboard',
                method: 'GET'
            });
            const predictions = fleetRes.data || [];

            // 2. Fetch Do Phase (Active Work Orders)
            const woRes = await client.entities.ordres_travail.queryAll({
                query: {},
                limit: 100
            });
            const activeWOs = (woRes.data.items || []).filter((wo: any) =>
                ['EN_ATTENTE', 'EN_COURS'].includes(wo.statut)
            );

            // 3. Fetch Interventions for Check and Act
            const intRes = await client.entities.ordres_intervention.queryAll({
                query: {},
                limit: 100,
                sort: '-date_intervention'
            });
            const allInts = intRes.data.items || [];

            const kanbanItems: KanbanItem[] = [];

            // Map Predictions to PLAN
            predictions.forEach((p: any) => {
                const hasWO = activeWOs.some(wo => wo.machine_id === p.machine_id);
                if (!hasWO && (p.risk_level === 'CRITICAL' || p.risk_level === 'HIGH')) {
                    kanbanItems.push({
                        id: `pred-${p.machine_id}`,
                        machineId: p.machine_id,
                        machineName: p.machine_name,
                        title: `Risque ML: ${p.predicted_priority}`,
                        subtitle: `Probabilité: ${p.failure_probability}%`,
                        priority: p.predicted_priority,
                        riskLevel: p.risk_level,
                        phase: 'PLAN',
                        type: 'PREDICTION',
                        date: p.predicted_failure_date
                    });
                }
            });

            // Map Work Orders to DO
            activeWOs.forEach((wo: any) => {
                kanbanItems.push({
                    id: `wo-${wo.id}`,
                    machineId: wo.machine_id,
                    machineName: wo.machine_nom || `Machine #${wo.machine_id}`,
                    title: wo.titre,
                    subtitle: `OT en cours (${wo.statut})`,
                    priority: wo.priorite,
                    phase: 'DO',
                    type: 'WORK_ORDER',
                    date: wo.created_at
                });
            });

            // Map Interventions to CHECK and ACT
            allInts.forEach((i: any) => {
                const isActed = !!i.actual_failure_type;
                kanbanItems.push({
                    id: `int-${i.id}`,
                    machineId: i.machine_id,
                    machineName: `Machine #${i.machine_id}`,
                    title: `Intervention #${i.id}`,
                    subtitle: i.actual_failure_type ? `Feedback: ${i.actual_failure_type}` : 'En attente feedback',
                    priority: i.priority || 'MEDIUM',
                    phase: isActed ? 'ACT' : 'CHECK',
                    type: 'INTERVENTION',
                    date: i.date_intervention
                });
            });

            setItems(kanbanItems);
        } catch (error) {
            console.error('Board Error:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const columns = [
        { id: 'PLAN', label: 'PLAN', icon: <Search className="w-5 h-5 text-blue-500" />, color: 'bg-blue-50', border: 'border-blue-200' },
        { id: 'DO', label: 'DO', icon: <PlayCircle className="w-5 h-5 text-orange-500" />, color: 'bg-orange-50', border: 'border-orange-200' },
        { id: 'CHECK', label: 'CHECK', icon: <ClipboardList className="w-5 h-5 text-green-500" />, color: 'bg-green-50', border: 'border-green-200' },
        { id: 'ACT', label: 'ACT', icon: <CheckCircle2 className="w-5 h-5 text-indigo-500" />, color: 'bg-indigo-50', border: 'border-indigo-200' },
    ];

    const getPriorityColor = (p: string) => {
        const map: any = {
            'URGENTE': 'bg-red-100 text-red-700',
            'ÉLEVÉE': 'bg-orange-100 text-orange-700',
            'HIGH': 'bg-orange-100 text-orange-700',
            'CRITICAL': 'bg-red-100 text-red-700',
            'MOYENNE': 'bg-blue-100 text-blue-700',
            'MEDIUM': 'bg-blue-100 text-blue-700',
        };
        return map[p.toUpperCase()] || 'bg-gray-100 text-gray-700';
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center h-64 gap-3">
                <RefreshCcw className="w-8 h-8 text-blue-600 animate-spin" />
                <p className="text-sm text-gray-500 font-medium">Synchronisation du cycle PDCA...</p>
            </div>
        );
    }

    return (
        <div className="w-full space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-gray-900">Tableau Kanban PDCA</h2>
                    <p className="text-sm text-gray-500">Visualisation du cycle de maintenance prédictive</p>
                </div>
                <Button variant="outline" size="sm" onClick={fetchData} className="gap-2">
                    <RefreshCcw className="w-4 h-4" /> Actualiser
                </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 min-h-[600px]">
                {columns.map((col) => (
                    <div key={col.id} className={`flex flex-col rounded-xl border ${col.border} ${col.color} p-4 space-y-4`}>
                        <div className="flex items-center justify-between px-1">
                            <div className="flex items-center gap-2">
                                {col.icon}
                                <span className="font-bold text-gray-700 tracking-wider">{col.label}</span>
                            </div>
                            <Badge variant="outline" className="bg-white/50 backdrop-blur-sm">
                                {items.filter(i => i.phase === col.id).length}
                            </Badge>
                        </div>

                        <div className="flex-1 space-y-3 overflow-y-auto no-scrollbar pb-4">
                            <AnimatePresence>
                                {items
                                    .filter((i) => i.phase === col.id as any)
                                    .map((item) => (
                                        <motion.div
                                            key={item.id}
                                            layout
                                            initial={{ opacity: 0, y: 10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            exit={{ opacity: 0, scale: 0.95 }}
                                            className="bg-white p-4 rounded-lg shadow-sm border border-gray-100 hover:shadow-md transition-shadow cursor-default group"
                                        >
                                            <div className="flex flex-col gap-2">
                                                <div className="flex justify-between items-start">
                                                    <Badge className={`text-[10px] font-bold ${getPriorityColor(item.priority)}`}>
                                                        {item.priority}
                                                    </Badge>
                                                    <div className="text-[10px] text-gray-400 flex items-center gap-1 font-mono">
                                                        <Clock className="w-3 h-3" />
                                                        {new Date(item.date).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })}
                                                    </div>
                                                </div>

                                                <div>
                                                    <p className="text-xs font-bold text-gray-900 line-clamp-2 leading-tight group-hover:text-blue-600 transition-colors">
                                                        {item.title}
                                                    </p>
                                                    <p className="text-[10px] text-gray-500 mt-1 flex items-center gap-1">
                                                        <Activity className="w-3 h-3" />
                                                        {item.machineName}
                                                    </p>
                                                </div>

                                                <div className="flex items-center justify-between pt-2 mt-1 border-t border-gray-50">
                                                    <span className="text-[10px] text-gray-400 font-medium italic">
                                                        {item.subtitle}
                                                    </span>
                                                    <Button
                                                        variant="ghost"
                                                        size="icon"
                                                        className="h-6 w-6 rounded-full hover:bg-blue-50 text-blue-400"
                                                        onClick={() => navigate(`/machines/${item.machineId}`)}
                                                    >
                                                        <ExternalLink className="w-3 h-3" />
                                                    </Button>
                                                </div>
                                            </div>
                                        </motion.div>
                                    ))}
                            </AnimatePresence>

                            {items.filter(i => i.phase === col.id as any).length === 0 && (
                                <div className="h-24 flex items-center justify-center border-2 border-dashed border-gray-200 rounded-lg text-gray-400 text-xs italic">
                                    Aucun élément
                                </div>
                            )}
                        </div>

                        {col.id === 'PLAN' && (
                            <Button
                                variant="ghost"
                                size="sm"
                                className="w-full text-blue-600 hover:bg-blue-100/50 text-[10px] h-8 font-bold"
                                onClick={() => navigate('/machines')}
                            >
                                GÉRER LES ALERTES <ArrowRight className="ml-1 w-3 h-3" />
                            </Button>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
};
