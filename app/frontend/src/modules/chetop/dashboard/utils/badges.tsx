import React from 'react';
import { AlertCircle, CheckCircle, Clock, XCircle } from 'lucide-react';

export const getPriorityColor = (priority: string) => {
  switch (priority) {
    case 'URGENTE':
      return 'bg-red-500';
    case 'ÉLEVÉE':
      return 'bg-orange-500';
    case 'MOYENNE':
      return 'bg-yellow-500';
    case 'BASSE':
      return 'bg-green-500';
    default:
      return 'bg-gray-500';
  }
};

export const getStatusIcon = (status: string) => {
  switch (status) {
    case 'EN_ATTENTE':
      return <Clock className="h-4 w-4" />;
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
  switch (status) {
    case 'EN_ATTENTE':
      return 'text-yellow-600 bg-yellow-50';
    case 'EN_COURS':
      return 'text-blue-600 bg-blue-50';
    case 'TERMINÉ':
      return 'text-green-600 bg-green-50';
    case 'ANNULÉ':
      return 'text-red-600 bg-red-50';
    default:
      return 'text-gray-600 bg-gray-50';
  }
};
