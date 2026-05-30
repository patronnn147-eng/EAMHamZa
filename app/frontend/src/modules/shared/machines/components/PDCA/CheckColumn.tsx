import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Activity, CheckSquare, Square, RefreshCcw } from 'lucide-react';
import { KanbanItem } from './types';

interface CheckColumnProps {
    items: KanbanItem[];
    actionLoading: string | null;
    onAction: (item: KanbanItem, action: 'DIAG' | 'VALIDATE') => void;
    getPriorityColor: (priority: string) => string;
}

export const CheckColumn: React.FC<CheckColumnProps> = ({
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
                className={baseCardClasses}
            >
                <div className="flex justify-between items-start mb-2">
                    <Badge className={`text-[10px] font-bold ${getPriorityColor(item.priority)}`}>
                        {item.priority}
                    </Badge>
                    <Badge className="text-[10px] bg-yellow-900/40 text-yellow-300 border border-yellow-700/50">
                        Validation Requise
                    </Badge>
                </div>
                <p className="text-xs font-bold text-white line-clamp-2 leading-tight mb-1">{item.title}</p>
                <p className="text-[10px] text-blue-300 flex items-center gap-1 mb-2">
                    <Activity className="w-3 h-3" />
                    {item.machineName}
                </p>
                
                <div className="space-y-2 mt-auto pt-2 border-t border-blue-800/50 bg-slate-800/50 -mx-3 px-3 pb-3 -mb-3 rounded-b-lg">
                    <div className="flex flex-col gap-1 mt-1">
                        <div className="flex items-center gap-2 text-[10px] text-blue-200">
                            <CheckSquare className="w-3 h-3 text-green-500" />
                            Work completed
                        </div>
                        <div className="flex items-center gap-2 text-[10px] text-blue-200">
                            {item.hasDiagnostic
                                ? <CheckSquare className="w-3 h-3 text-green-500"/>
                                : <Square className="w-3 h-3 text-slate-500" />}
                            Root-cause diagnosis added
                        </div>
                        <div className="flex items-center gap-2 text-[10px] text-blue-200">
                            {item.hasValidation
                                ? <CheckSquare className="w-3 h-3 text-green-500"/>
                                : <Square className="w-3 h-3 text-slate-500" />}
                            CHEFTECH validation (required)
                        </div>
                    </div>
                    <div className="flex gap-2 pt-2">
                        <Button
                            size="sm"
                            variant="outline"
                            onClick={() => onAction(item, 'DIAG')}
                            className="flex-1 text-[10px] h-7 bg-slate-800"
                            title={item.hasDiagnostic ? 'Review diagnosis' : 'Add root-cause diagnosis'}
                        >
                            {item.hasDiagnostic ? 'Review diag' : 'Add diagnosis'}
                        </Button>
                        <Button
                            size="sm"
                            onClick={() => onAction(item, 'VALIDATE')}
                            disabled={actionLoading === item.id.toString() || !item.hasDiagnostic}
                            className="flex-1 text-[10px] h-7 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-700 disabled:cursor-not-allowed"
                            title={!item.hasDiagnostic ? 'Add diagnosis first' : 'CHEFTECH validates this intervention'}
                        >
                            {actionLoading === item.id.toString()
                                ? <RefreshCcw className="w-3 h-3 animate-spin" />
                                : 'Validate (CHEFTECH)'}
                        </Button>
                    </div>
                    {!item.hasDiagnostic && (
                        <p className="text-[9px] text-yellow-400 italic mt-1">
                            ⚠️ Add diagnosis before validation
                        </p>
                    )}
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
                <div className="h-auto mt-4 p-4 flex flex-col items-center justify-center border-2 border-dashed border-green-800/50 rounded-lg text-green-400 text-xs bg-slate-900/40">
                    <span className="font-medium text-center">Nothing to validate</span>
                    <span className="text-[10px] opacity-70 text-center mt-1">
                        Completed work orders + interventions appear here for CHEFTECH validation.
                    </span>
                </div>
            )}
        </div>
    );
};