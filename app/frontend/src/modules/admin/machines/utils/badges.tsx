import React from 'react';
import { Badge } from '@/components/ui/badge';

export const StatusBadge: React.FC<{ statut: string }> = ({ statut }) => {
  const statusConfig = {
    EN_ATTENTE: { label: 'Pending', className: 'bg-yellow-100 text-yellow-800' },
    EN_COURS: { label: 'In Progress', className: 'bg-blue-100 text-blue-800' },
    TERMINE: { label: 'Completed', className: 'bg-green-100 text-green-800' },
    ANNULE: { label: 'Cancelled', className: 'bg-red-100 text-red-800' },
  };

  const config = statusConfig[statut as keyof typeof statusConfig] || statusConfig.EN_ATTENTE;
  return <Badge className={config.className}>{config.label}</Badge>;
};
