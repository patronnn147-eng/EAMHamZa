import React from 'react';
import { AlertCircle, CheckCircle, Clock, XCircle } from 'lucide-react';

export const getPriorityColor = (priority: string) => {
  switch (priority) {
    case 'URGENTE':
      return 'bg-gradient-to-r from-red-600 to-rose-600 text-white shadow-[0_2px_10px_rgba(225,29,72,0.3)] border-none';
    case 'ÉLEVÉE':
      return 'bg-gradient-to-r from-orange-500 to-amber-500 text-white shadow-[0_2px_10px_rgba(245,158,11,0.3)] border-none';
    case 'MOYENNE':
      return 'bg-gradient-to-r from-yellow-400 to-orange-400 text-gray-900 border-none';
    case 'BASSE':
      return 'bg-gradient-to-r from-emerald-500 to-teal-500 text-white border-none';
    default:
      return 'bg-gray-500 text-white';
  }
};

export const getStatusIcon = (status: string) => {
  switch (status) {
    case 'EN_ATTENTE':
      return <Clock className="h-4 w-4" />;
    case 'VALIDE':
      return <CheckCircle className="h-4 w-4" />;
    case 'REJETE':
      return <XCircle className="h-4 w-4" />;
    case 'EN_COURS':
      return <AlertCircle className="h-4 w-4" />;
    case 'TERMINÉ':
      return <CheckCircle className="h-4 w-4" />;
    case 'ANNULÉ':
      return <XCircle className="h-4 w-4" />;
    default:
      return <Clock className="h-4 w-4" />;
  }
};

export const getStatusColor = (status: string) => {
  const base = "rounded-full px-3 py-1 text-[10px] font-black uppercase tracking-widest border transition-all duration-300 ";
  switch (status) {
    case 'EN_ATTENTE':
      return base + 'text-amber-700 bg-amber-50/50 border-amber-200/50 shadow-[0_0_8px_rgba(245,158,11,0.1)]';
    case 'VALIDE':
      return base + 'text-emerald-700 bg-emerald-50/50 border-emerald-200/50 shadow-[0_0_8px_rgba(16,185,129,0.1)]';
    case 'REJETE':
      return base + 'text-rose-700 bg-rose-50/50 border-rose-200/50';
    case 'EN_COURS':
      return base + 'text-blue-700 bg-blue-50/50 border-blue-200/50 animate-pulse shadow-[0_0_12px_rgba(59,130,246,0.2)]';
    case 'TERMINÉ':
    case 'TERMINE':
      return base + 'text-emerald-800 bg-emerald-100/50 border-emerald-300/50';
    case 'ANNULÉ':
      return base + 'text-gray-500 bg-gray-50/50 border-gray-200/50';
    default:
      return base + 'text-gray-600 bg-gray-50/50 border-gray-200/50';
  }
};
