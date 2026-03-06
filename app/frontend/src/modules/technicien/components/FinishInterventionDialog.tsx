import React, { useState } from 'react';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { AlertCircle, CheckCircle2 } from 'lucide-react';

interface FinishInterventionDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onConfirm: (data: {
        actual_failure_type: string;
        ml_prediction_matched: boolean;
        rapport?: string;
    }) => void;
    interventionId: number;
}

const FAILURE_TYPES = [
    { value: 'NONE', label: 'Aucune panne détectée (Maintenance préventive)' },
    { value: 'TWF', label: 'TWF — Usure de l\'outil' },
    { value: 'HDF', label: 'HDF — Dissipation thermique' },
    { value: 'PWF', label: 'PWF — Défaillance électrique' },
    { value: 'OSF', label: 'OSF — Surcharge / Effort excessif' },
    { value: 'RNF', label: 'RNF — Panne aléatoire' },
];

export const FinishInterventionDialog: React.FC<FinishInterventionDialogProps> = ({
    open,
    onOpenChange,
    onConfirm,
    interventionId,
}) => {
    const [failureType, setFailureType] = useState('NONE');
    const [mlMatched, setMlMatched] = useState(true);
    const [finalReport, setFinalReport] = useState('');

    const handleConfirm = () => {
        onConfirm({
            actual_failure_type: failureType,
            ml_prediction_matched: mlMatched,
            rapport: finalReport.trim() || undefined,
        });
        // Reset state for next use
        setFailureType('NONE');
        setFinalReport('');
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-md">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <CheckCircle2 className="h-5 w-5 text-green-600" />
                        Clôturer l'Intervention #{interventionId}
                    </DialogTitle>
                    <DialogDescription>
                        Veuillez fournir un feedback final pour boucler le cycle de maintenance.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-6 py-4">
                    <div className="grid gap-2">
                        <Label htmlFor="failure-type" className="text-sm font-semibold">
                            Quel était le type de panne réel ?
                        </Label>
                        <Select value={failureType} onValueChange={setFailureType}>
                            <SelectTrigger id="failure-type">
                                <SelectValue placeholder="Sélectionner le type de panne" />
                            </SelectTrigger>
                            <SelectContent>
                                {FAILURE_TYPES.map((ft) => (
                                    <SelectItem key={ft.value} value={ft.value}>
                                        {ft.label}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="flex items-center justify-between p-3 rounded-lg bg-gray-50 border border-gray-100">
                        <div className="space-y-0.5">
                            <Label className="text-sm font-semibold">Prédiction IA correcte ?</Label>
                            <p className="text-[10px] text-gray-500">L'IA avait-elle bien anticipé ce problème ?</p>
                        </div>
                        <Switch
                            checked={mlMatched}
                            onCheckedChange={setMlMatched}
                        />
                    </div>

                    <div className="grid gap-2">
                        <Label htmlFor="final-report" className="text-sm font-semibold">
                            Observations finales (Optionnel)
                        </Label>
                        <Textarea
                            id="final-report"
                            placeholder="Exemples:
- Nettoyage des buses d'injection effectué.
- Remplacement du capteur de température défectueux.
- Graissage des paliers et vérification des courroies."
                            value={finalReport}
                            onChange={(e) => setFinalReport(e.target.value)}
                            className="resize-none"
                            rows={5}
                        />
                    </div>

                    <div className="bg-blue-50 p-3 rounded-lg flex gap-2 items-start border border-blue-100">
                        <AlertCircle className="h-4 w-4 text-blue-600 mt-0.5" />
                        <p className="text-[11px] text-blue-700 leading-relaxed">
                            Ce feedback sera utilisé pour ré-entraîner nos modèles d'IA et améliorer la précision des futures alertes.
                        </p>
                    </div>
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)}>
                        Annuler
                    </Button>
                    <Button onClick={handleConfirm} className="bg-green-600 hover:bg-green-700">
                        Confirmer & Clôturer
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};
