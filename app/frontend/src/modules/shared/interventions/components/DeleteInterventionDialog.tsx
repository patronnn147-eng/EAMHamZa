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
import type { Intervention } from '@/lib/types';

interface DeleteInterventionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  deletingIntervention: Intervention | null;
  onDelete: () => void;
}

export const DeleteInterventionDialog: React.FC<DeleteInterventionDialogProps> = ({
  open,
  onOpenChange,
  deletingIntervention,
  onDelete,
}) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Confirm Deletion</DialogTitle>
          <DialogDescription>
            Are you sure you want to delete Intervention #{deletingIntervention?.id}? This action cannot be undone.
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
