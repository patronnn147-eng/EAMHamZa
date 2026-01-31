import React from 'react';
import { Badge } from '@/components/ui/badge';

export const StatusBadge: React.FC<{ statut: string }> = ({ statut }) => {
  const statusConfig = {
    EN_ATTENTE: { label: 'Pending', variant: 'secondary' as const },
    EN_COURS: { label: 'In Progress', variant: 'default' as const },
    TERMINE: { label: 'Completed', variant: 'outline' as const },
    ANNULE: { label: 'Cancelled', variant: 'destructive' as const },
  };

  const config = statusConfig[statut as keyof typeof statusConfig] || statusConfig.EN_ATTENTE;
  return <Badge variant={config.variant}>{config.label}</Badge>;
};

export const PriorityBadge: React.FC<{ priorite: string }> = ({ priorite }) => {
  const priorityConfig = {
    BASSE: { label: 'Low', className: 'bg-gray-100 text-gray-800' },
    MOYENNE: { label: 'Medium', className: 'bg-blue-100 text-blue-800' },
    ELEVEE: { label: 'High', className: 'bg-orange-100 text-orange-800' },
    URGENTE: { label: 'Urgent', className: 'bg-red-100 text-red-800' },
  };

  const config = priorityConfig[priorite as keyof typeof priorityConfig] || priorityConfig.MOYENNE;
  return <Badge className={config.className}>{config.label}</Badge>;
};

export const isOverdue = (dueDate: string, status: string) => {
  if (status === 'TERMINE' || status === 'ANNULE') return false;
  return new Date(dueDate) < new Date();
};
