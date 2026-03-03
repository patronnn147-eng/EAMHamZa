import React from 'react';

export const ChefTechMachinesHeader: React.FC = () => {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Machines</h2>
        <p className="mt-1 text-sm text-gray-500">Vue d'ensemble des machines et de leur état de santé</p>
      </div>
    </div>
  );
};
