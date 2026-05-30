import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Wrench, RefreshCcw } from 'lucide-react';
import { KanbanItem } from './types';

interface DoColumnProps {
    items: KanbanItem[];
    actionLoading: string | null;
    onAction: (item: KanbanItem, action: 'BLOCK' | 'FINISH') => void;
    getPriorityColor: (priority: string) => string;
}

export const DoColumn: React.FC<DoColumnProps> = ({
    items,
    actionLoading,
    onAction,
    getPriorityColor,
}) => {
    const renderCard = (item: KanbanItem) => {
        const baseCardClasses = "flex flex-col bg-slate-800 rounded-lg border border-blue-800/50 p-3 shadow-sm hover:shadow-md transition-all group relative";
        
        return (
            <motion.div 
                key={item.id} 
                layout 
                initial={{ opacity: 0, y: 10 }} 
                animate={{ opacity: 1, y: 0 }} 
                exit={{ opacity: 0, scale: 0.95 }} 
                className={`${baseCardClasses} ${item.isBlocked ? 'ring-2 ring-red-400 border-red-400' : ''}`}
            >
                <div className="flex justify-between items-start mb-2">
                    <Badge className={`text-[10px] font-bold ${getPriorityColor(item.priority)}`}>
                        {item.priority}
                    </Badge>
                    <Badge className="text-[10px] bg-orange-900/40 text-orange-300 border border-orange-700/50">
                        {item.statut === 'ASSIGNED' ? 'Assigned' : 'In Progress'}
                    </Badge>
                </div>
                <p className="text-xs font-bold text-white line-clamp-2 leading-tight mb-1">{item.title}</p>
                <p className="text-[10px] text-blue-300 flex items-center gap-1 mb-2">
                    <Wrench className="w-3 h-3" />
                    {item.machineName}
                </p>
                {item.technician && (
                    <p className="text-[10px] text-slate-400 mb-2">👤 {item.technician}</p>
                )}

                <div className="space-y-2 mt-auto pt-2 border-t border-blue-800/50">
                    <div className="w-full bg-slate-700 rounded-full h-1.5 overflow-hidden">
                        <div
                            className="h-1.5 rounded-full bg-orange-500 transition-all"
                            style={{ width: `${item.progress}%` }}
                        />
                    </div>
                    <div className="flex justify-between text-[10px] text-blue-300">
                        <span>{item.subtitle}</span>
                    </div>
                    <div className="flex gap-2">
                        <Button
                            size="sm"
                            variant="outline"
                            onClick={() => onAction(item, 'BLOCK')}
                            disabled={actionLoading === item.id.toString()}
                            className="flex-1 text-[10px] h-7 text-red-400 border-red-800/50"
                            title="Open technician interface to log a blocking reason"
                        >
                            Report Block
                        </Button>
                        <Button
                            size="sm"
                            onClick={() => onAction(item, 'FINISH')}
                            disabled={actionLoading === item.id.toString()}
                            className="flex-1 text-[10px] h-7 bg-green-600 hover:bg-green-700"
                        >
                            {actionLoading === item.id.toString()
                                ? <RefreshCcw className="w-3 h-3 animate-spin" />
                                : 'Mark Complete'}
                        </Button>
                    </div>
                </div>
            </motion.div>
        );
    };

    return (
        <div className="flex-1 flex flex-col gap-3 overflow-y-auto no-scrollbar pb-4">
            <AnimatePresence>
                {items.map(item => renderCard(item))}
            </AnimatePresence>

            {items.length === 0 && (
                <div className="h-auto mt-4 p-4 flex flex-col items-center justify-center border-2 border-dashed border-orange-800/50 rounded-lg text-orange-400 text-xs bg-slate-900/40">
                    <span className="font-medium text-center">No work in progress</span>
                    <span className="text-[10px] opacity-70 text-center mt-1">
                        Work orders move here once a CHEFTECH assigns them or a technician starts them.
                    </span>
                </div>
            )}
        </div>
    );
};