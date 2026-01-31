export const getPriorityColor = (priority: string) => {
  switch (priority) {
    case 'URGENTE':
      return 'bg-red-100 text-red-800';
    case 'ÉLEVÉE':
      return 'bg-orange-100 text-orange-800';
    case 'MOYENNE':
      return 'bg-yellow-100 text-yellow-800';
    case 'BASSE':
      return 'bg-green-100 text-green-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
};

export const getStatusColor = (status: string) => {
  switch (status) {
    case 'EN_COURS':
      return 'bg-blue-100 text-blue-800';
    case 'TERMINÉ':
      return 'bg-green-100 text-green-800';
    case 'EN_ATTENTE':
      return 'bg-yellow-100 text-yellow-800';
    case 'CRITIQUE':
      return 'bg-red-100 text-red-800';
    case 'MAINTENANCE':
      return 'bg-orange-100 text-orange-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
};
