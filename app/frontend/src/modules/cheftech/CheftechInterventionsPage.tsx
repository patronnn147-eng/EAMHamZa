import React, { useEffect } from 'react';
import { InterventionsTab } from './dashboard/components';
import { useCheftechDashboardData } from './dashboard/hooks';
import { AppPagination } from '@/components/shared/AppPagination';

const CheftechInterventionsPage: React.FC = () => {
  const {
    interventions,
    loading,
    fetchInterventions,
    approveIntervention,
    rejectIntervention,
    interventionsPage,
    interventionsTotalPages,
    setInterventionsPage,
  } = useCheftechDashboardData();

  useEffect(() => {
    fetchInterventions({ page: interventionsPage });
  }, [interventionsPage]);

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
        noGrouping={true}
      />
      <div className="flex justify-end mt-4">
        <AppPagination
          currentPage={interventionsPage}
          totalPages={interventionsTotalPages}
          onPageChange={setInterventionsPage}
        />
      </div>
    </div>
  );
};

export default CheftechInterventionsPage;
