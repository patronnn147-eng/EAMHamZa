import React from 'react';
import { PDCACanbanBoard } from './machines/components/PDCACanbanBoard';

const PDCAPage: React.FC = () => {
    return (
        <div className="container mx-auto py-6">
            <PDCACanbanBoard />
        </div>
    );
};

export default PDCAPage;
