import React from 'react';
import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight } from 'lucide-react';

function buildPageNumbers(totalPages: number, currentPage: number): (number | string)[] {
  if (totalPages <= 5) return Array.from({ length: totalPages }, (_, i) => i + 1);
  if (currentPage <= 3) return [1, 2, 3, 4, '...', totalPages];
  if (currentPage >= totalPages - 2) return [1, '...', totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
  return [1, '...', currentPage - 1, currentPage, currentPage + 1, '...', totalPages];
}

interface InterventionsPaginationProps {
  currentPage: number;
  totalPages: number;
  total: number;
  onPageChange: (page: number) => void;
}

export const InterventionsPagination: React.FC<InterventionsPaginationProps> = ({
  currentPage,
  totalPages,
  total,
  onPageChange,
}) => {
  if (totalPages <= 1) {
    return (
      <div className="flex items-center justify-between py-4">
        <span className="text-sm text-blue-400">
          Showing {((currentPage - 1) * 100) + 1} - {Math.min(currentPage * 100, total)} of {total} interventions
        </span>
      </div>
    );
  }

  const getPageNumbers = () => buildPageNumbers(totalPages, currentPage);

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-4 py-4">
      <span className="text-sm text-blue-400">
        Showing {((currentPage - 1) * 100) + 1} - {Math.min(currentPage * 100, total)} of {total} interventions
      </span>
      
      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className="h-8 w-8"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        
        {getPageNumbers().map((page, idx) => (
          <React.Fragment key={page === '...' ? `ellipsis-${idx}` : page}>
            {page === '...' ? (
              <span className="px-2 text-blue-300">...</span>
            ) : (
              <Button
                variant={currentPage === page ? 'default' : 'ghost'}
                size="icon"
                onClick={() => onPageChange(page)}
                className={`h-8 w-8 ${currentPage === page ? 'bg-primary text-white' : ''}`}
              >
                {page}
              </Button>
            )}
          </React.Fragment>
        ))}
        
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className="h-8 w-8"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
};
