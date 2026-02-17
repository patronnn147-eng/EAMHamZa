import React, { useEffect } from 'react';
import { InterventionsTab } from './dashboard/components';
import { useCheftechDashboardData } from './dashboard/hooks';

const CheftechInterventionsPage: React.FC = () => {
  const {
    interventions,
    loading,
    fetchInterventions,
    approveIntervention,
    rejectIntervention,
  } = useCheftechDashboardData();

  useEffect(() => {
    fetchInterventions();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <InterventionsTab
        interventions={interventions}
        fetchInterventions={fetchInterventions}
        approveIntervention={approveIntervention}
        rejectIntervention={rejectIntervention}
      />
    </div>
  );
};

export default CheftechInterventionsPage;
