import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { TrendingUp, Zap, RefreshCcw } from 'lucide-react';
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
                        En cours d'amélioration
                    </Badge>
                </div>
                <p className="text-xs font-bold text-white line-clamp-2 leading-tight mb-1">{item.title}</p>
                <p className="text-[10px] text-blue-300 flex items-center gap-1 mb-2 italic">
                    Cause: {item.subtitle.replace('Cause:', '')}
                </p>
                
                <div className="space-y-2 mt-auto pt-2 border-t border-blue-800/50">
                    {item.effectiveness && (
                        <div className="grid grid-cols-2 gap-1 mb-2">
                            <div className="flex items-center gap-1 bg-slate-800 p-1 rounded border border-green-800/50">
                                <TrendingUp className="w-3 h-3 text-green-500" />
                                <span className="text-[9px] text-blue-200">
                                    {item.effectiveness.downtimeReduction} d'arrêt
                                </span>
                            </div>
                            <div className="flex items-center gap-1 bg-slate-800 p-1 rounded border border-blue-800/50">
                                <Zap className="w-3 h-3 text-blue-500" />
                                <span className="text-[9px] text-blue-200">
                                    {item.effectiveness.costSavings} sauvés
                                </span>
                            </div>
                        </div>
                    )}
                    <div className="flex gap-2">
                        <Button 
                            size="sm" 
                            variant="outline" 
                            onClick={() => onAction(item, 'STD')}
                            className="flex-1 text-[9px] h-7 bg-slate-800 border-indigo-800/50 text-indigo-300"
                        >
                            MAJ Gamme
                        </Button>
                        <Button 
                            size="sm" 
                            onClick={() => onAction(item, 'RETRAIN')}
                            disabled={actionLoading === 'retrain'}
                            className="flex-1 text-[9px] h-7 bg-slate-800 hover:bg-slate-900 text-white"
                        >
                            {actionLoading === 'retrain' 
                                ? <RefreshCcw className="w-3 h-3 animate-spin" /> 
                                : 'Ré-entraîner ML'}
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
                <div className="h-24 mt-4 flex flex-col items-center justify-center border-2 border-dashed border-indigo-800/50 rounded-lg text-indigo-400 text-xs italic bg-slate-900/40">
                    <span className="not-italic font-medium">Aucun élément</span>
                    <span className="not-italic text-[10px] opacity-70">
                        Ajoutez le feedback PDCA sur les interventions
                    </span>
                </div>
            )}
        </div>
    );
};