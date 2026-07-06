import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { AlertTriangle, Clock, Activity, User, RefreshCcw } from 'lucide-react';
import { KanbanItem } from './types';

interface PlanColumnProps {
    items: KanbanItem[];
    actionLoading: string | null;
    onAction: (item: KanbanItem) => void;
    onCreateWorkOrder: () => void;
    getPriorityColor: (priority: string) => string;
}

export const PlanColumn: React.FC<PlanColumnProps> = ({
    items,
    actionLoading,
    onAction,
    onCreateWorkOrder,
    getPriorityColor,
}) => {
    const predictions = items.filter(i => i.type === 'PREDICTION');
    const workOrders = items.filter(i => i.type === 'WORK_ORDER');

    const renderCard = (item: KanbanItem) => {
        const baseCardClasses = "flex flex-col bg-slate-800 rounded-lg border border-blue-800/50 p-3 shadow-sm hover:shadow-md transition-all group relative";

        let actionButtonLabel: React.ReactNode;
        if (actionLoading === item.id.toString()) {
            actionButtonLabel = <RefreshCcw className="w-3 h-3 animate-spin" />;
        } else if (item.type === 'PREDICTION') {
            actionButtonLabel = 'Create Work Order';
        } else if (item.statut === 'DRAFT') {
            actionButtonLabel = 'Submit for approval';
        } else if (item.statut === 'SUBMITTED') {
            actionButtonLabel = 'Approve (CHEFTECH)';
        } else if (item.statut === 'APPROVED') {
            actionButtonLabel = 'Assign to technician';
        } else {
            actionButtonLabel = 'Advance status';
        }

        return (
            <motion.div 
                key={item.id} 
                layout 
                initial={{ opacity: 0, y: 10 }} 
                animate={{ opacity: 1, y: 0 }} 
                exit={{ opacity: 0, scale: 0.95 }} 
                className={baseCardClasses}
            >
                <div className="flex justify-between items-start mb-2">
                    <Badge className={`text-[10px] font-bold ${getPriorityColor(item.priority)}`}>
                        {item.priority}
                    </Badge>
                    <span className="text-[10px] text-blue-400 flex items-center gap-1 font-mono">
                        <Clock className="w-3 h-3" />
                        {new Date(item.date).toLocaleDateString('fr-FR')}
                    </span>
                </div>
                <p className="text-xs font-bold text-white line-clamp-2 leading-tight mb-1">{item.title}</p>
                <p className="text-[10px] text-blue-300 flex items-center gap-1 mb-2">
                    <Activity className="w-3 h-3" />
                    {item.machineName}
                </p>
                
                <div className="space-y-2 mt-auto pt-2 border-t border-blue-800/50">
                    {item.type === 'PREDICTION' && (
                        <div className="flex justify-between items-center text-[10px] bg-red-900/30 text-red-300 border border-red-800/50 p-1.5 rounded">
                            <span className="flex items-center gap-1">
                                <AlertTriangle className="w-3 h-3"/>
                                Alerte Triage
                            </span>
                            <span className="font-bold">{item.riskScore}% Risque</span>
                        </div>
                    )}
                    {item.type === 'WORK_ORDER' && (
                        <div className="flex justify-between items-center text-[10px] bg-blue-900/30 text-blue-300 border border-blue-800/50 p-1.5 rounded">
                            <span className="flex items-center gap-1">
                                <User className="w-3 h-3"/>
                                Assigné: {item.technician}
                            </span>
                        </div>
                    )}
                    <Button
                        size="sm"
                        onClick={() => onAction(item)}
                        disabled={actionLoading === item.id.toString()}
                        className={`w-full text-[10px] h-7 ${item.type === 'PREDICTION' ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'}`}
                    >
                        {actionButtonLabel}
                    </Button>
                </div>
            </motion.div>
        );
    };

    return (
        <div className="flex-1 flex flex-col gap-3 overflow-y-auto no-scrollbar pb-4">
            {/* Predictions Swimlane */}
            <div className="flex flex-col gap-3">
                {predictions.length > 0 && (
                    <div className="flex items-center gap-2 px-1 mb-1">
                        <div className="h-px bg-red-200 flex-1"></div>
                        <span className="text-[10px] font-bold text-red-400 uppercase tracking-wider">
                            AI Predictions ({predictions.length})
                        </span>
                        <div className="h-px bg-red-200 flex-1"></div>
                    </div>
                )}
                <AnimatePresence>
                    {predictions.map(item => renderCard(item))}
                </AnimatePresence>
            </div>

            {/* Work Orders Swimlane */}
            <div className="flex flex-col gap-3 mt-2">
                {workOrders.length > 0 && (
                    <div className="flex items-center gap-2 px-1 mb-1">
                        <div className="h-px bg-blue-200 flex-1"></div>
                        <span className="text-[10px] font-bold text-blue-400 uppercase tracking-wider">
                            Work Orders ({workOrders.length})
                        </span>
                        <div className="h-px bg-blue-200 flex-1"></div>
                    </div>
                )}
                <AnimatePresence>
                    {workOrders.map(item => renderCard(item))}
                </AnimatePresence>
            </div>
            
            {items.length === 0 && (
                <div className="h-auto mt-4 p-4 flex flex-col items-center justify-center border-2 border-dashed border-blue-800/50 rounded-lg text-blue-400 text-xs bg-slate-900/40">
                    <span className="font-medium text-center">Nothing to plan right now</span>
                    <span className="text-[10px] opacity-70 text-center mt-1 mb-2">
                        AI alerts and draft work orders appear here.
                    </span>
                    <Button
                        size="sm"
                        variant="outline"
                        className="mt-2 h-7 text-[10px] border-blue-600 text-blue-400 hover:bg-blue-900/30"
                        onClick={onCreateWorkOrder}
                    >
                        + Create Work Order manually
                    </Button>
                </div>
            )}
        </div>
    );
};