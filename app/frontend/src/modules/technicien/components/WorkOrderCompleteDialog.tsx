import React, { useState, useEffect } from 'react';
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
import { Input } from '@/components/ui/input';
import { CheckCircle2, Activity, AlertTriangle } from 'lucide-react';

interface WorkOrderCompleteDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onConfirm: (data: WorkOrderCompletePayload) => void;
    workOrderId: number;
    workOrderTitle: string;
    machineName?: string;
}

export interface WorkOrderCompletePayload {
    rapport: string;
    intervention_type?: string;
    root_cause_category?: string;
    root_cause_description?: string;
    actions_performed?: string;
    parts_replaced?: string;
    tools_used?: string;
    machine_status_after?: string;
    plan_hypothesis?: string;
    check_resolved?: boolean;
    check_verification_method?: string;
    act_preventive_actions?: string;
    act_recommendations?: string;
    telemetry_temperature?: number;
    telemetry_vibration?: number;
    telemetry_rpm?: number;
    telemetry_torque?: number;
    telemetry_power?: number;
    telemetry_notes?: string;
}

const INTERVENTION_TYPES = [
    { value: 'PREVENTIVE', label: 'Maintenance préventive' },
    { value: 'CORRECTIVE', label: 'Maintenance corrective' },
    { value: 'PREDICTIVE', label: 'Maintenance prédictive' },
    { value: 'EMERGENCY', label: 'Urgence / Dépannage' },
    { value: 'INSPECTION', label: 'Inspection / Audit' },
    { value: 'OTHER', label: 'Autre' },
];

const ROOT_CAUSE_CATEGORIES = [
    { value: 'MECHANICAL', label: 'Défaillance mécanique' },
    { value: 'ELECTRICAL', label: 'Défaillance électrique' },
    { value: 'HYDRAULIC', label: 'Problème hydraulique' },
    { value: 'SOFTWARE', label: 'Problème logiciel / firmware' },
    { value: 'WEAR', label: 'Usure normale' },
    { value: 'OVERLOAD', label: 'Surcharge / Stress excessif' },
    { value: 'ENVIRONMENTAL', label: 'Conditions environnementales' },
    { value: 'MATERIAL', label: 'Problème de matière première' },
    { value: 'UNKNOWN', label: 'Cause indéterminée' },
];

const MACHINE_STATUS_OPTIONS = [
    { value: 'OPERATIONAL', label: 'Opérationnel' },
    { value: 'DEGRADED', label: 'Dégradé (fonctionne partiellement)' },
    { value: 'STOPPED', label: 'Arrêté (en attente)' },
    { value: 'SCRAP', label: 'Mettre au rebut' },
];

export const WorkOrderCompleteDialog: React.FC<WorkOrderCompleteDialogProps> = ({
    open,
    onOpenChange,
    onConfirm,
    workOrderId,
    workOrderTitle,
    machineName,
}) => {
    const [loading, setLoading] = useState(false);

    const [rapport, setRapport] = useState('');
    const [interventionType, setInterventionType] = useState<string>('CORRECTIVE');
    const [rootCauseCategory, setRootCauseCategory] = useState<string>('');
    const [rootCauseDescription, setRootCauseDescription] = useState('');
    const [actionsPerformed, setActionsPerformed] = useState('');
    const [partsReplaced, setPartsReplaced] = useState('');
    const [toolsUsed, setToolsUsed] = useState('');
    const [machineStatusAfter, setMachineStatusAfter] = useState<string>('OPERATIONAL');

    const [planHypothesis, setPlanHypothesis] = useState('');
    const [checkResolved, setCheckResolved] = useState(true);
    const [checkVerificationMethod, setCheckVerificationMethod] = useState('');
    const [actPreventiveActions, setActPreventiveActions] = useState('');
    const [actRecommendations, setActRecommendations] = useState('');

    const [telemetryTemp, setTelemetryTemp] = useState('');
    const [telemetryVibration, setTelemetryVibration] = useState('');
    const [telemetryRpm, setTelemetryRpm] = useState('');
    const [telemetryTorque, setTelemetryTorque] = useState('');
    const [telemetryPower, setTelemetryPower] = useState('');
    const [telemetryNotes, setTelemetryNotes] = useState('');

    const resetForm = () => {
        setRapport('');
        setInterventionType('CORRECTIVE');
        setRootCauseCategory('');
        setRootCauseDescription('');
        setActionsPerformed('');
        setPartsReplaced('');
        setToolsUsed('');
        setMachineStatusAfter('OPERATIONAL');
        setPlanHypothesis('');
        setCheckResolved(true);
        setCheckVerificationMethod('');
        setActPreventiveActions('');
        setActRecommendations('');
        setTelemetryTemp('');
        setTelemetryVibration('');
        setTelemetryRpm('');
        setTelemetryTorque('');
        setTelemetryPower('');
        setTelemetryNotes('');
    };

    useEffect(() => {
        if (!open) {
            resetForm();
        }
    }, [open]);

    const handleConfirm = async () => {
        setLoading(true);
        try {
            const payload: WorkOrderCompletePayload = {
                rapport: rapport.trim(),
                intervention_type: interventionType || undefined,
                root_cause_category: rootCauseCategory || undefined,
                root_cause_description: rootCauseDescription.trim() || undefined,
                actions_performed: actionsPerformed.trim() || undefined,
                parts_replaced: partsReplaced.trim() || undefined,
                tools_used: toolsUsed.trim() || undefined,
                machine_status_after: machineStatusAfter || undefined,
                plan_hypothesis: planHypothesis.trim() || undefined,
                check_resolved: checkResolved,
                check_verification_method: checkVerificationMethod.trim() || undefined,
                act_preventive_actions: actPreventiveActions.trim() || undefined,
                act_recommendations: actRecommendations.trim() || undefined,
                telemetry_temperature: telemetryTemp ? parseFloat(telemetryTemp) : undefined,
                telemetry_vibration: telemetryVibration ? parseFloat(telemetryVibration) : undefined,
                telemetry_rpm: telemetryRpm ? parseInt(telemetryRpm) : undefined,
                telemetry_torque: telemetryTorque ? parseFloat(telemetryTorque) : undefined,
                telemetry_power: telemetryPower ? parseFloat(telemetryPower) : undefined,
                telemetry_notes: telemetryNotes.trim() || undefined,
            };
            onConfirm(payload);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2 text-green-600">
                        <CheckCircle2 className="h-5 w-5" />
                        Terminer l'OT #{workOrderId}
                    </DialogTitle>
                    <DialogDescription className="text-blue-300">
                        {workOrderTitle}
                        {machineName && <span className="ml-2 font-semibold">• {machineName}</span>}
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-6 py-4">
                    {/* RAPPORT FINAL */}
                    <div className="grid gap-2">
                        <Label className="text-sm font-semibold text-red-400 flex items-center gap-1">
                            <AlertTriangle className="h-4 w-4" />
                            Rapport final *
                        </Label>
                        <Textarea
                            placeholder="Décrivez le travail effectué sur la machine..."
                            value={rapport}
                            onChange={(e) => setRapport(e.target.value)}
                            className="min-h-[100px]"
                        />
                    </div>

                    {/* TYPE INTERVENTION + ETAT MACHINE */}
                    <div className="grid grid-cols-2 gap-4">
                        <div className="grid gap-2">
                            <Label className="text-sm font-semibold">Type d'intervention</Label>
                            <Select value={interventionType} onValueChange={setInterventionType}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Sélectionner..." />
                                </SelectTrigger>
                                <SelectContent>
                                    {INTERVENTION_TYPES.map((type) => (
                                        <SelectItem key={type.value} value={type.value}>
                                            {type.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="grid gap-2">
                            <Label className="text-sm font-semibold">État de la machine après</Label>
                            <Select value={machineStatusAfter} onValueChange={setMachineStatusAfter}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Sélectionner..." />
                                </SelectTrigger>
                                <SelectContent>
                                    {MACHINE_STATUS_OPTIONS.map((status) => (
                                        <SelectItem key={status.value} value={status.value}>
                                            {status.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    {/* CAUSE RACINE */}
                    <div className="grid gap-2">
                        <Label className="text-sm font-semibold">Catégorie de cause racine</Label>
                        <Select value={rootCauseCategory} onValueChange={setRootCauseCategory}>
                            <SelectTrigger>
                                <SelectValue placeholder="Sélectionner la cause..." />
                            </SelectTrigger>
                            <SelectContent>
                                {ROOT_CAUSE_CATEGORIES.map((cat) => (
                                    <SelectItem key={cat.value} value={cat.value}>
                                        {cat.label}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="grid gap-2">
                        <Label className="text-sm font-semibold">Description de la cause</Label>
                        <Textarea
                            placeholder="Décrivez la cause du problème..."
                            value={rootCauseDescription}
                            onChange={(e) => setRootCauseDescription(e.target.value)}
                        />
                    </div>

                    {/* ACTIONS */}
                    <div className="grid gap-2">
                        <Label className="text-sm font-semibold">Actions effectuées</Label>
                        <Textarea
                            placeholder="- Action 1&#10;- Action 2&#10;- Action 3"
                            value={actionsPerformed}
                            onChange={(e) => setActionsPerformed(e.target.value)}
                            rows={3}
                        />
                    </div>

                    {/* PIECES + OUTILS */}
                    <div className="grid grid-cols-2 gap-4">
                        <div className="grid gap-2">
                            <Label className="text-sm font-semibold">Pièces remplacées</Label>
                            <Input
                                placeholder="Ex: Roulement 6204, Courroie..."
                                value={partsReplaced}
                                onChange={(e) => setPartsReplaced(e.target.value)}
                            />
                        </div>

                        <div className="grid gap-2">
                            <Label className="text-sm font-semibold">Outils utilisés</Label>
                            <Input
                                placeholder="Ex: Clé à douille, Multimètre..."
                                value={toolsUsed}
                                onChange={(e) => setToolsUsed(e.target.value)}
                            />
                        </div>
                    </div>

                    {/* TELEMETRIE */}
                    <div className="border-t border-blue-800 pt-4">
                        <h4 className="text-sm font-semibold text-amber-400 mb-3 flex items-center gap-2">
                            <Activity className="h-4 w-4" />
                            Telémétrie (IoT Dashboard)
                        </h4>
                        <p className="text-xs text-blue-400 mb-3">
                            Enregistrez les données telemetry de la machine après intervention.
                        </p>
                        <div className="grid grid-cols-5 gap-3">
                            <div className="grid gap-1">
                                <Label className="text-xs">Température (°C)</Label>
                                <Input
                                    type="number"
                                    step="0.1"
                                    placeholder="0.0"
                                    value={telemetryTemp}
                                    onChange={(e) => setTelemetryTemp(e.target.value)}
                                />
                            </div>
                            <div className="grid gap-1">
                                <Label className="text-xs">Vibration (mm/s)</Label>
                                <Input
                                    type="number"
                                    step="0.1"
                                    placeholder="0.0"
                                    value={telemetryVibration}
                                    onChange={(e) => setTelemetryVibration(e.target.value)}
                                />
                            </div>
                            <div className="grid gap-1">
                                <Label className="text-xs">RPM</Label>
                                <Input
                                    type="number"
                                    placeholder="0"
                                    value={telemetryRpm}
                                    onChange={(e) => setTelemetryRpm(e.target.value)}
                                />
                            </div>
                            <div className="grid gap-1">
                                <Label className="text-xs">Torque (Nm)</Label>
                                <Input
                                    type="number"
                                    step="0.1"
                                    placeholder="0.0"
                                    value={telemetryTorque}
                                    onChange={(e) => setTelemetryTorque(e.target.value)}
                                />
                            </div>
                            <div className="grid gap-1">
                                <Label className="text-xs">Puissance (kW)</Label>
                                <Input
                                    type="number"
                                    step="0.1"
                                    placeholder="0.0"
                                    value={telemetryPower}
                                    onChange={(e) => setTelemetryPower(e.target.value)}
                                />
                            </div>
                        </div>
                        <div className="mt-3">
                            <Label className="text-xs">Notes</Label>
                            <Input
                                placeholder="Notes supplémentaires..."
                                value={telemetryNotes}
                                onChange={(e) => setTelemetryNotes(e.target.value)}
                            />
                        </div>
                    </div>

                    {/* PDCA */}
                    <div className="border-t border-blue-800 pt-4">
                        <h4 className="text-sm font-semibold text-purple-400 mb-3">
                            Méthode PDCA - Amélioration continue
                        </h4>
                        
                        <div className="grid gap-2 mb-3">
                            <Label className="text-xs">PLAN - Hypothèse / Cause identifiée</Label>
                            <Textarea
                                placeholder="Quelle est votre hypothèse sur la cause..."
                                value={planHypothesis}
                                onChange={(e) => setPlanHypothesis(e.target.value)}
                                rows={2}
                            />
                        </div>

                        <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 border border-blue-800/50 mb-3">
                            <div className="space-y-0.5">
                                <Label className="text-sm font-semibold">CHECK - Problème résolu ?</Label>
                                <p className="text-[10px] text-blue-300">Le problème a-t-il été résolu ?</p>
                            </div>
                            <Switch
                                checked={checkResolved}
                                onCheckedChange={setCheckResolved}
                            />
                        </div>

                        <div className="grid gap-2 mb-3">
                            <Label className="text-xs">CHECK - Méthode de vérification</Label>
                            <Input
                                placeholder="Comment avez-vous vérifié ?"
                                value={checkVerificationMethod}
                                onChange={(e) => setCheckVerificationMethod(e.target.value)}
                            />
                        </div>

                        <div className="grid gap-2 mb-3">
                            <Label className="text-xs">ACT - Actions préventives</Label>
                            <Textarea
                                placeholder="Quelles actions préventives mettre en place ?"
                                value={actPreventiveActions}
                                onChange={(e) => setActPreventiveActions(e.target.value)}
                                rows={2}
                            />
                        </div>

                        <div className="grid gap-2">
                            <Label className="text-xs">ACT - Recommandations</Label>
                            <Textarea
                                placeholder="Autres recommandations pour éviter la récurrence..."
                                value={actRecommendations}
                                onChange={(e) => setActRecommendations(e.target.value)}
                                rows={2}
                            />
                        </div>
                    </div>
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)}>
                        Annuler
                    </Button>
                    <Button 
                        onClick={handleConfirm} 
                        disabled={!rapport.trim() || loading}
                        className="bg-green-600 hover:bg-green-700"
                    >
                        {loading ? 'Enregistrement...' : 'Terminer'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};