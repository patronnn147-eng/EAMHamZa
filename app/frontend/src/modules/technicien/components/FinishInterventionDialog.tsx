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
import { Textarea } from '@/components/ui/textarea';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { CheckCircle2, AlertCircle } from 'lucide-react';

interface FinishInterventionDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onConfirm: (data: {
        rapport?: string;
        date_debut?: string;
        date_fin?: string;
        failure_type?: string;
        ml_matched?: boolean;
    }) => void;
    interventionId: number;
}

const FAILURE_TYPES = [
    { value: 'mechanical', label: 'Mécanique' },
    { value: 'electrical', label: 'Électrique' },
    { value: 'software', label: 'Logiciel' },
    { value: 'other', label: 'Autre' },
];

export const FinishInterventionDialog: React.FC<FinishInterventionDialogProps> = ({
    open,
    onOpenChange,
    onConfirm,
    interventionId,
}) => {
    const [finalReport, setFinalReport] = useState('');
    const [failureType, setFailureType] = useState<string>('');
    const [mlMatched, setMlMatched] = useState(false);

    const now = new Date();
    const defaultDateStr = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
        .toISOString()
        .slice(0, 16);

    const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
    const defaultStartStr = new Date(
        oneHourAgo.getTime() - oneHourAgo.getTimezoneOffset() * 60000
    )
        .toISOString()
        .slice(0, 16);

    const [startDate, setStartDate] = useState(defaultStartStr);
    const [endDate, setEndDate] = useState(defaultDateStr);

    const handleConfirm = () => {
        onConfirm({
            rapport: finalReport.trim() || undefined,
            date_debut: new Date(startDate).toISOString(),
            date_fin: new Date(endDate).toISOString(),
            failure_type: failureType || undefined,
            ml_matched: mlMatched,
        });

        // reset
        setFinalReport('');
        setFailureType('');
        setMlMatched(false);
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
                    {/* Failure type */}
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

                    {/* ML match */}
                    <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 border border-blue-800/50">
                        <div className="space-y-0.5">
                            <Label className="text-sm font-semibold">
                                Prédiction IA correcte ?
                            </Label>
                            <p className="text-[10px] text-blue-300">
                                L'IA avait-elle bien anticipé ce problème ?
                            </p>
                        </div>
                        <Switch checked={mlMatched} onCheckedChange={setMlMatched} />
                    </div>

                    {/* Report */}
                    <div className="grid gap-2">
                        <Label htmlFor="final-report" className="text-sm font-semibold">
                            Observations finales (Optionnel)
                        </Label>
                        <Textarea
                            id="final-report"
                            placeholder={`Exemples:
- Nettoyage des buses d'injection effectué.
- Remplacement du capteur de température défectueux.
- Graissage des paliers et vérification des courroies.`}
                            value={finalReport}
                            onChange={(e) => setFinalReport(e.target.value)}
                            className="resize-none"
                            rows={3}
                        />
                    </div>

                    {/* Dates */}
                    <div className="grid grid-cols-2 gap-4">
                        <div className="grid gap-2">
                            <Label htmlFor="start-date" className="text-sm font-semibold">
                                Début d'Intervention
                            </Label>
                            <input
                                type="datetime-local"
                                id="start-date"
                                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                                value={startDate}
                                onChange={(e) => setStartDate(e.target.value)}
                            />
                        </div>

                        <div className="grid gap-2">
                            <Label htmlFor="end-date" className="text-sm font-semibold">
                                Fin d'Intervention
                            </Label>
                            <input
                                type="datetime-local"
                                id="end-date"
                                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                                value={endDate}
                                onChange={(e) => setEndDate(e.target.value)}
                            />
                        </div>
                    </div>

                    {/* Info */}
                    <div className="bg-blue-50 p-3 rounded-lg flex gap-2 items-start border border-blue-100">
                        <AlertCircle className="h-4 w-4 text-blue-600 mt-0.5" />
                        <p className="text-[11px] text-blue-700 leading-relaxed">
                            Ce feedback sera utilisé pour améliorer la précision des futures alertes.
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