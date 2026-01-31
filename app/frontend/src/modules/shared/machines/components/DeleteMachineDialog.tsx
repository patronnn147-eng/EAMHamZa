import React from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import type { Machine } from '@/lib/types';

interface DeleteMachineDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  deletingMachine: Machine | null;
  onDelete: () => void;
}

export const DeleteMachineDialog: React.FC<DeleteMachineDialogProps> = ({
  open,
  onOpenChange,
  deletingMachine,
  onDelete,
}) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Confirm Deletion</DialogTitle>
          <DialogDescription>
            Are you sure you want to delete "{deletingMachine?.nom}"? This action cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={onDelete}>
            Delete
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
