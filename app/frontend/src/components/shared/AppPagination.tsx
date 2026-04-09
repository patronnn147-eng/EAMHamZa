import React from 'react';
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from '@/components/ui/pagination';

interface AppPaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export function AppPagination({ currentPage, totalPages, onPageChange }: AppPaginationProps) {
  if (totalPages <= 1) return null;

  const handlePrevious = (e: React.MouseEvent) => {
    e.preventDefault();
    if (currentPage > 1) onPageChange(currentPage - 1);
  };

  const handleNext = (e: React.MouseEvent) => {
    e.preventDefault();
    if (currentPage < totalPages) onPageChange(currentPage + 1);
  };

  const handleSetPage = (e: React.MouseEvent, page: number) => {
    e.preventDefault();
    onPageChange(page);
  };

  return (
    <Pagination className="mt-4">
      <PaginationContent>
        <PaginationItem>
          <PaginationPrevious 
            href="#" 
            onClick={handlePrevious} 
            className={currentPage <= 1 ? 'pointer-events-none opacity-50' : ''} 
          />
        </PaginationItem>
        
        {Array.from({ length: totalPages }).map((_, idx) => {
          const page = idx + 1;
          // Show 1, last, and window around current page
          if (page === 1 || page === totalPages || (page >= currentPage - 1 && page <= currentPage + 1)) {
            return (
              <PaginationItem key={page}>
                <PaginationLink 
                  href="#" 
                  isActive={page === currentPage} 
                  onClick={(e) => handleSetPage(e, page)}
                >
                  {page}
                </PaginationLink>
              </PaginationItem>
            );
          }
          if (page === currentPage - 2 || page === currentPage + 2) {
            return (
              <PaginationItem key={page}>
                <PaginationEllipsis />
              </PaginationItem>
            );
          }
          return null;
        })}

        <PaginationItem>
          <PaginationNext 
            href="#" 
            onClick={handleNext} 
            className={currentPage >= totalPages ? 'pointer-events-none opacity-50' : ''} 
          />
        </PaginationItem>
      </PaginationContent>
    </Pagination>
  );
}
