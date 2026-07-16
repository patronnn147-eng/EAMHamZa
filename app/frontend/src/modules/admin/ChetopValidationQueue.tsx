import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Loader2, Shield, CheckCircle2, XCircle, Clock, AlertTriangle } from 'lucide-react';
import { useAdminWorkOrderValidation, type PendingAdminWorkOrder } from '@/hooks/useAdminWorkOrderValidation';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';

interface ChetopValidationQueueProps {
  className?: string;
}

const ChetopValidationQueue: React.FC<ChetopValidationQueueProps> = ({ className }) => {
  const { pendingWorkOrders, loading, validatingId, validateByAdmin, rejectByAdmin } = useAdminWorkOrderValidation();
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [selectedWorkOrder, setSelectedWorkOrder] = useState<PendingAdminWorkOrder | null>(null);
  const [rejectReason, setRejectReason] = useState('');

  const openRejectDialog = (wo: PendingAdminWorkOrder) => {
    setSelectedWorkOrder(wo);
    setRejectReason('');
    setRejectDialogOpen(true);
  };

  const handleReject = async () => {
    if (!selectedWorkOrder) return;
    await rejectByAdmin(selectedWorkOrder.id, rejectReason || undefined);
    setRejectDialogOpen(false);
    setSelectedWorkOrder(null);
  };

  if (loading) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
        </CardContent>
      </Card>
    );
  }

  if (pendingWorkOrders.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-emerald-500" />
            Validation CHETOP
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <CheckCircle2 className="w-12 h-12 text-emerald-500 mb-3" />
            <p className="text-muted-foreground">Aucun ordre de travail en attente de validation</p>
            <p className="text-sm text-muted-foreground mt-1">
              Les ordres de travail créés par CHETOP apparaîtront ici
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-amber-500" />
            Validation CHETOP
            <Badge variant="warning" className="ml-2">
              {pendingWorkOrders.length}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {pendingWorkOrders.map((wo) => (
            <div
              key={wo.id}
              className="border rounded-lg p-4 bg-amber-50/50 dark:bg-amber-950/20 border-amber-200/50 dark:border-amber-800/50"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap mb-2">
                    <Badge variant="info" className="bg-blue-100 text-blue-800 border-blue-300">
                      CHETOP
                    </Badge>
                    <span className="font-bold text-foreground">#{wo.id}</span>
                    {wo.machine_nom && (
                      <span className="text-sm text-muted-foreground">
                        Machine: {wo.machine_nom}
                      </span>
                    )}
                  </div>
                  <h4 className="font-semibold text-foreground mb-1">{wo.titre}</h4>
                  {wo.description && (
                    <p className="text-sm text-muted-foreground line-clamp-2 mb-2">
                      {wo.description}
                    </p>
                  )}
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      Créé: {new Date(wo.created_at).toLocaleDateString('fr-FR')}
                    </span>
                    {wo.utilisateur_nom && (
                      <span>Par: {wo.utilisateur_nom}</span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <Button
                    size="sm"
                    variant="outline"
                    className="border-red-200 text-red-700 hover:bg-red-50"
                    onClick={() => openRejectDialog(wo)}
                    disabled={validatingId === wo.id}
                  >
                    <XCircle className="w-4 h-4 mr-1" />
                    Rejeter
                  </Button>
                  <Button
                    size="sm"
                    className="bg-emerald-600 hover:bg-emerald-700 text-white"
                    onClick={() => validateByAdmin(wo.id)}
                    disabled={validatingId === wo.id}
                  >
                    {validatingId === wo.id ? (
                      <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                    ) : (
                      <CheckCircle2 className="w-4 h-4 mr-1" />
                    )}
                    Valider
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Dialog open={rejectDialogOpen} onOpenChange={setRejectDialogOpen}>
        <DialogContent className="sm:max-w-[480px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-500" />
              Rejeter l'ordre de travail
            </DialogTitle>
            <DialogDescription>
              Vous êtes sur le point de rejeter l'ordre de travail créé par CHETOP. Cette action nécessite un motif.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="reason">Motif du rejet (optionnel)</Label>
              <Textarea
                id="reason"
                placeholder="Entrez le motif du rejet..."
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                className="min-h-[100px]"
              />
            </div>
          </div>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setRejectDialogOpen(false)}>
              Annuler
            </Button>
            <Button
              variant="destructive"
              onClick={handleReject}
              disabled={validatingId !== null}
            >
              {validatingId === null ? null : <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Confirmer le rejet
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default ChetopValidationQueue;