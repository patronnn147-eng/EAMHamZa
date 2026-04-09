import React from 'react';

export const ChefTechMachinesHeader: React.FC = () => {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h2 className="text-4xl font-bold text-white">Machines</h2>
        <p className="mt-1 text-sm text-blue-200">Vue d'ensemble des machines et de leur état de santé</p>
      </div>
    </div>
  );
};
