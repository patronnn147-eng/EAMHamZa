import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, MapPin, Settings, AlertTriangle } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { addDays, format, isWithinInterval, startOfDay } from 'date-fns';

interface User {
    id: number;
    nom: string;
    email: string;
    role: string;
}

interface Planning {
    id: number;
    identifiant_planning: string;
    date_debut: string;
    date_fin: string;
    type: string;
    shift_type?: string;
    zone_travail?: string;
    assigned_users: User[];
}

export default function PlanningCalendarView() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const { toast } = useToast();
    const [planning, setPlanning] = useState<Planning | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (id) {
            fetchPlanningDetail(id);
        }
    }, [id]);

    const fetchPlanningDetail = async (planningId: string) => {
        try {
            const response = await client.apiCall.invoke({
                url: `/api/v1/plannings/${planningId}`,
                method: 'GET',
            });

            // Simple unwrap logic based on PlanningDetailPage.tsx
            const data = (response as any).data;
            setPlanning(data);
        } catch (error) {
            console.error('Error fetching planning detail:', error);
            toast({
                title: 'Error',
                description: 'Failed to load planning details',
                variant: 'destructive',
            });
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    if (!planning) {
        return (
            <div className="space-y-6">
                <div className="flex items-center gap-4">
                    <Button variant="ghost" onClick={() => navigate(-1)}>
                        <ArrowLeft className="mr-2 h-4 w-4" />
                        Back
                    </Button>
                </div>
                <div className="text-center py-12">
                    <AlertTriangle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">Planning Not Found</h3>
                    <p className="text-gray-500">The planning you're looking for doesn't exist.</p>
                </div>
            </div>
        );
    }

    const startDate = startOfDay(new Date(planning.date_debut));
    const endDate = startOfDay(new Date(planning.date_fin));

    const getTypeBadge = (type: string) => {
        const typeConfig = {
            MAINTENANCE: { label: 'Maintenance', className: 'bg-orange-100 text-orange-800' },
            SHIFT: { label: 'Shift', className: 'bg-blue-100 text-blue-800' },
        };
        const config = typeConfig[type as keyof typeof typeConfig] || typeConfig.MAINTENANCE;
        return <Badge className={config.className}>{config.label}</Badge>;
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-4">
                <Button variant="ghost" onClick={() => navigate(-1)}>
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back to Details
                </Button>
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">
                        Calendar: {planning.identifiant_planning}
                    </h1>
                    <div className="flex items-center gap-2 mt-1">
                        {getTypeBadge(planning.type)}
                        <span className="text-sm text-gray-500">
                            {format(startDate, 'PP')} - {format(endDate, 'PP')}
                        </span>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Card className="md:col-span-2">
                    <CardHeader>
                        <CardTitle>Schedule Visualization</CardTitle>
                    </CardHeader>
                    <CardContent className="flex justify-center">
                        <Calendar
                            mode="range"
                            selected={{
                                from: startDate,
                                to: endDate,
                            }}
                            defaultMonth={startDate}
                            className="rounded-md border shadow p-4"
                        // In a real app, we might want to disable dates outside the range 
                        // or color them differently, but DayPicker's "range" mode works well for display.
                        />
                    </CardContent>
                </Card>

                <div className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Planning Info</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="space-y-1">
                                <label className="text-xs font-medium text-gray-500 uppercase">Work Zone</label>
                                <div className="flex items-center gap-2">
                                    <MapPin className="h-4 w-4 text-gray-400" />
                                    <span className="font-medium">{planning.zone_travail || 'Not specified'}</span>
                                </div>
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-medium text-gray-500 uppercase">Type</label>
                                <div className="flex items-center gap-2">
                                    <Settings className="h-4 w-4 text-gray-400" />
                                    <span className="font-medium capitalize">{planning.type.toLowerCase()}</span>
                                </div>
                            </div>
                            <div className="pt-4 border-t">
                                <p className="text-sm text-gray-600">
                                    This calendar shows the scheduled period for this planning.
                                    Highlighting indicates the duration from start to end.
                                </p>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}
