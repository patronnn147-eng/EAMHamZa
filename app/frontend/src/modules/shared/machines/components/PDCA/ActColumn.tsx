import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { TrendingUp, RefreshCcw } from 'lucide-react';
import { KanbanItem } from './types';

interface ActColumnProps {
    items: KanbanItem[];
    actionLoading: string | null;
    onAction: (item: KanbanItem, action: 'STD' | 'RETRAIN') => void;
}

export const ActColumn: React.FC<ActColumnProps> = ({
    items,
    actionLoading,
    onAction,
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
                className={`${baseCardClasses} bg-slate-800/50 border-blue-700/50 opacity-90 hover:opacity-100`}
            >
                <div className="flex justify-between items-start mb-2">
                    <Badge className="text-[10px] bg-indigo-900/40 text-indigo-300 border border-indigo-700/50">
                        {item.implementationStatus === 'RETRAINED' ? '✓ AI updated' : 'Ready to standardize'}
                    </Badge>
                </div>
                <p className="text-xs font-bold text-white line-clamp-2 leading-tight mb-1">{item.title}</p>
                <p className="text-[10px] text-blue-300 flex items-center gap-1 mb-2 italic">
                    {item.subtitle}
                </p>

                <div className="space-y-2 mt-auto pt-2 border-t border-blue-800/50">
                    {item.effectiveness && (
                        <div className="grid grid-cols-1 gap-1 mb-2">
                            <div className="flex items-center gap-1 bg-slate-800 p-1.5 rounded border border-green-800/50">
                                <TrendingUp className="w-3 h-3 text-green-500 flex-shrink-0" />
                                <span className="text-[9px] text-blue-200">
                                    AI feedback: <strong>{item.effectiveness.downtimeReduction}</strong>
                                </span>
                            </div>
                        </div>
                    )}
                    <p className="text-[9px] text-slate-400 italic">
                        Update the standard procedure, then retrain the model with this validated outcome.
                    </p>
                    <div className="flex gap-2 pt-1">
                        <Button
                            size="sm"
                            variant="outline"
                            onClick={() => onAction(item, 'STD')}
                            className="flex-1 text-[9px] h-7 bg-slate-800 border-indigo-800/50 text-indigo-300 hover:bg-indigo-900/30"
                            title="Open intervention to update standard procedure"
                        >
                            Update Procedure
                        </Button>
                        <Button
                            size="sm"
                            onClick={() => onAction(item, 'RETRAIN')}
                            disabled={actionLoading === 'retrain' || item.implementationStatus === 'RETRAINED'}
                            className="flex-1 text-[9px] h-7 bg-purple-700 hover:bg-purple-800 text-white disabled:bg-slate-700"
                            title="Trigger ML retraining with validated feedback"
                        >
                            {actionLoading === 'retrain'
                                ? <RefreshCcw className="w-3 h-3 animate-spin" />
                                : item.implementationStatus === 'RETRAINED'
                                    ? '✓ Done'
                                    : 'Retrain AI'}
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
                <div className="h-auto mt-4 p-4 flex flex-col items-center justify-center border-2 border-dashed border-indigo-800/50 rounded-lg text-indigo-400 text-xs bg-slate-900/40">
                    <span className="font-medium text-center">No validated work yet</span>
                    <span className="text-[10px] opacity-70 text-center mt-1">
                        Validated interventions move here so you can standardize the fix and retrain the AI.
                    </span>
                </div>
            )}
        </div>
    );
};