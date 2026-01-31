import React from 'react';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Search } from 'lucide-react';

interface WorkOrdersFiltersProps {
  searchTerm: string;
  setSearchTerm: (value: string) => void;
  statusFilter: string;
  setStatusFilter: (value: string) => void;
  priorityFilter: string;
  setPriorityFilter: (value: string) => void;
}

export const WorkOrdersFilters: React.FC<WorkOrdersFiltersProps> = ({
  searchTerm,
  setSearchTerm,
  statusFilter,
  setStatusFilter,
  priorityFilter,
  setPriorityFilter,
}) => {
  return (
    <div className="flex flex-col sm:flex-row gap-4">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        <Input
          type="text"
          placeholder="Search by work order ID..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-10"
        />
      </div>
      <Select value={statusFilter} onValueChange={setStatusFilter}>
        <SelectTrigger className="w-full sm:w-[180px]">
          <SelectValue placeholder="Filter by status" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="ALL">All Status</SelectItem>
          <SelectItem value="EN_ATTENTE">Pending</SelectItem>
          <SelectItem value="EN_COURS">In Progress</SelectItem>
          <SelectItem value="TERMINE">Completed</SelectItem>
          <SelectItem value="ANNULE">Cancelled</SelectItem>
        </SelectContent>
      </Select>
      <Select value={priorityFilter} onValueChange={setPriorityFilter}>
        <SelectTrigger className="w-full sm:w-[180px]">
          <SelectValue placeholder="Filter by priority" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="ALL">All Priority</SelectItem>
          <SelectItem value="BASSE">Low</SelectItem>
          <SelectItem value="MOYENNE">Medium</SelectItem>
          <SelectItem value="ELEVEE">High</SelectItem>
          <SelectItem value="URGENTE">Urgent</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
};
