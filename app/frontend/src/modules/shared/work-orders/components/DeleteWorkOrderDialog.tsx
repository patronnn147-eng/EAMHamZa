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
import type { OrdreTravail } from '@/lib/types';

interface DeleteWorkOrderDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  deletingWorkOrder: OrdreTravail | null;
  onDelete: () => void;
}

export const DeleteWorkOrderDialog: React.FC<DeleteWorkOrderDialogProps> = ({
  open,
  onOpenChange,
  deletingWorkOrder,
  onDelete,
}) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Confirm Deletion</DialogTitle>
          <DialogDescription>
            Are you sure you want to delete Work Order #{deletingWorkOrder?.id}? This action cannot be undone.
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
