import React, { useState, useEffect } from 'react';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Badge } from '@/components/ui/badge';
import { Zap, Thermometer, RotateCcw, Activity, AlertTriangle, ShieldCheck } from 'lucide-react';
import { Machine } from '@/lib/types';
import { client } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

interface TelemetrySimulatorProps {
    machine: Machine;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSuccess?: () => void;
}

const PRESETS = [
    {
        name: 'Normal',
        icon: <ShieldCheck className="w-4 h-4 text-green-500" />,
        values: { air: 300, process: 310, rpm: 1500, torque: 40, wear: 0 },
        description: 'Statut nominal',
    },
    {
        name: 'Surchauffe',
        icon: <Thermometer className="w-4 h-4 text-orange-500" />,
        values: { air: 305, process: 325, rpm: 1800, torque: 50, wear: 120 },
        description: 'Processus haute température',
    },
    {
        name: 'Usure (TWF)',
        icon: <RotateCcw className="w-4 h-4 text-yellow-500" />,
        values: { air: 300, process: 310, rpm: 1400, torque: 45, wear: 205 },
        description: 'Changement d\'outil imminent',
    },
    {
        name: 'Critique (PWF)',
        icon: <Zap className="w-4 h-4 text-red-500" />,
        values: { air: 298, process: 308, rpm: 2500, torque: 75, wear: 50 },
        description: 'Surcharge de puissance',
    },
];

export const TelemetrySimulator: React.FC<TelemetrySimulatorProps> = ({
    machine,
    open,
    onOpenChange,
    onSuccess,
}) => {
    const { toast } = useToast();
    const [loading, setLoading] = useState(false);
    const [telemetry, setTelemetry] = useState({
        air: machine.air_temperature || 300,
        process: machine.process_temperature || 310,
        rpm: machine.rotational_speed || 1500,
        torque: machine.torque || 40,
        wear: machine.tool_wear || 0,
    });

    useEffect(() => {
        if (open) {
            setTelemetry({
                air: machine.air_temperature || 300,
                process: machine.process_temperature || 310,
                rpm: machine.rotational_speed || 1500,
                torque: machine.torque || 40,
                wear: machine.tool_wear || 0,
            });
        }
    }, [open, machine]);

    const handleApplyPreset = (values: typeof telemetry) => {
        setTelemetry(values);
    };

    const handleSave = async () => {
        setLoading(true);
        try {
            await client.apiCall.invoke({
                url: `/api/v1/ml/machines/${machine.id}/telemetry`,
                method: 'PATCH',
                data: {
                    air_temperature: telemetry.air,
                    process_temperature: telemetry.process,
                    rotational_speed: telemetry.rpm,
                    torque: telemetry.torque,
                    tool_wear: telemetry.wear,
                },
            });

            toast({
                title: 'Succès',
                description: `Simulateur : Données appliquées à ${machine.nom}`,
            });
            onSuccess?.();
            onOpenChange(false);
        } catch (error) {
            toast({
                title: 'Erreur',
                description: 'Échec de l\'envoi des données simulées',
                variant: 'destructive',
            });
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-2xl">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Activity className="w-5 h-5 text-indigo-500" />
                        Simulateur de Capteurs - {machine.nom}
                    </DialogTitle>
                    <DialogDescription>
                        Ajustez les paramètres de la machine pour simuler des défaillances et tester les prédictions ML.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8 my-4">
                    <div className="space-y-6">
                        <div className="space-y-3">
                            <div className="flex justify-between items-center">
                                <Label className="flex items-center gap-2">
                                    <Thermometer className="w-4 h-4 text-blue-400" />
                                    Température Air (K)
                                </Label>
                                <span className="text-sm font-medium">{telemetry.air}K</span>
                            </div>
                            <Slider
                                value={[telemetry.air]}
                                min={290}
                                max={310}
                                step={0.1}
                                onValueChange={([v]) => setTelemetry(t => ({ ...t, air: v }))}
                            />
                        </div>

                        <div className="space-y-3">
                            <div className="flex justify-between items-center">
                                <Label className="flex items-center gap-2">
                                    <Thermometer className="w-4 h-4 text-red-400" />
                                    Température Process (K)
                                </Label>
                                <span className="text-sm font-medium">{telemetry.process}K</span>
                            </div>
                            <Slider
                                value={[telemetry.process]}
                                min={300}
                                max={330}
                                step={0.1}
                                onValueChange={([v]) => setTelemetry(t => ({ ...t, process: v }))}
                            />
                        </div>

                        <div className="space-y-3">
                            <div className="flex justify-between items-center">
                                <Label className="flex items-center gap-2">
                                    <RotateCcw className="w-4 h-4 text-green-400" />
                                    Vitesse (RPM)
                                </Label>
                                <span className="text-sm font-medium">{telemetry.rpm} RPM</span>
                            </div>
                            <Slider
                                value={[telemetry.rpm]}
                                min={1000}
                                max={3000}
                                step={1}
                                onValueChange={([v]) => setTelemetry(t => ({ ...t, rpm: v }))}
                            />
                        </div>
                    </div>

                    <div className="space-y-6">
                        <div className="space-y-3">
                            <div className="flex justify-between items-center">
                                <Label className="flex items-center gap-2">
                                    <Zap className="w-4 h-4 text-yellow-400" />
                                    Couple (Nm)
                                </Label>
                                <span className="text-sm font-medium">{telemetry.torque} Nm</span>
                            </div>
                            <Slider
                                value={[telemetry.torque]}
                                min={10}
                                max={80}
                                step={0.1}
                                onValueChange={([v]) => setTelemetry(t => ({ ...t, torque: v }))}
                            />
                        </div>

                        <div className="space-y-3">
                            <div className="flex justify-between items-center">
                                <Label className="flex items-center gap-2">
                                    <Activity className="w-4 h-4 text-blue-400" />
                                    Usure Outil (min)
                                </Label>
                                <span className="text-sm font-medium">{telemetry.wear} min</span>
                            </div>
                            <Slider
                                value={[telemetry.wear]}
                                min={0}
                                max={250}
                                step={1}
                                onValueChange={([v]) => setTelemetry(t => ({ ...t, wear: v }))}
                            />
                            {telemetry.wear > 200 && (
                                <div className="flex items-center gap-1 text-xs text-orange-500">
                                    <AlertTriangle className="w-3 h-3" />
                                    Zone d'alerte TWF
                                </div>
                            )}
                        </div>

                        <div className="pt-2">
                            <Label className="text-xs uppercase text-blue-300 mb-2 block">Scénarios Prédéfinis</Label>
                            <div className="grid grid-cols-2 gap-2">
                                {PRESETS.map((preset) => (
                                    <Button
                                        key={preset.name}
                                        variant="outline"
                                        size="sm"
                                        className="flex flex-col h-auto py-2 gap-1 items-start text-left"
                                        onClick={() => handleApplyPreset(preset.values)}
                                    >
                                        <div className="flex items-center gap-1 font-semibold text-xs">
                                            {preset.icon}
                                            {preset.name}
                                        </div>
                                        <div className="text-[10px] text-blue-300 line-clamp-1">{preset.description}</div>
                                    </Button>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>

                <DialogFooter>
                    <Button variant="ghost" onClick={() => onOpenChange(false)}>Annuler</Button>
                    <Button
                        className="bg-indigo-600 hover:bg-indigo-700 text-white"
                        onClick={handleSave}
                        disabled={loading}
                    >
                        {loading ? 'Application...' : 'Appliquer la simulation'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};
