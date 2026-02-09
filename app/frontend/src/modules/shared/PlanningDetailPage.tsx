import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  Calendar, 
  Users, 
  ArrowLeft, 
  Clock, 
  MapPin, 
  User, 
  Settings,
  AlertTriangle,
  CheckCircle,
  XCircle
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface User {
  id: number;
  nom: string;
  email: string;
  role: string;
  shift_type?: string | null;
}

interface Planning {
  id: number;
  identifiant_planning: string;
  date_debut: string;
  date_fin: string;
  type: string;
  shift_type?: string;
  chef_operation_id?: number;
  chef_technique_id?: number;
  zone_travail?: string;
  assigned_users: User[];
  created_at?: string;
}

export default function PlanningDetailPage() {
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
      console.log('PlanningDetailPage raw response:', response);

      const unwrap = (value: unknown) => {
        let current = value;
        for (let i = 0; i < 5; i += 1) {
          if (!current || typeof current !== 'object') return current;
          const obj = current as Record<string, unknown>;
          
          // Check for specific fields to identify the Planning object
          if ('identifiant_planning' in obj) return current;
          
          // Check for list response
          if ('items' in obj && Array.isArray(obj.items)) return current;

          if ('data' in obj) {
            current = obj.data;
            continue;
          }
          
          // Fallback checks
          if ('id' in obj && 'type' in obj) return current;
          
          return current;
        }
        return current;
      };

      const maybeWrapped = (response as { data?: unknown } | undefined)?.data;
      const extracted = unwrap(maybeWrapped);

      console.log('PlanningDetailPage raw response:', response);
      try {
        console.log('PlanningDetailPage response.data (stringified):', JSON.stringify(maybeWrapped, null, 2));
        console.log('PlanningDetailPage extracted planning (stringified):', JSON.stringify(extracted, null, 2));
      } catch (e) {
        console.log('PlanningDetailPage serialization error:', e);
      }

      let planningObj = extracted as Planning;

      if (planningObj && (planningObj.zone_travail == null || `${planningObj.zone_travail}`.trim() === '')) {
        try {
          const listResponse = await client.apiCall.invoke({
            url: '/api/v1/plannings',
            method: 'GET',
            data: { skip: 0, limit: 200 },
          });

          const listWrapped = (listResponse as { data?: unknown } | undefined)?.data;
          const listExtracted = unwrap(listWrapped) as { items?: Planning[] } | Planning[] | undefined;

          const items = Array.isArray(listExtracted)
            ? listExtracted
            : (listExtracted as { items?: Planning[] } | undefined)?.items;

          const match = items?.find((p) => `${p.id}` === `${planningId}`);
          if (match?.zone_travail) {
            planningObj = { ...planningObj, zone_travail: match.zone_travail };
          }
        } catch (e) {
          console.error('Error fetching planning list fallback:', e);
        }
      }

      setPlanning(planningObj);
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

  const getTypeBadge = (type: string) => {
    const typeConfig = {
      MAINTENANCE: { label: 'Maintenance', className: 'bg-orange-100 text-orange-800' },
      SHIFT: { label: 'Shift', className: 'bg-blue-100 text-blue-800' },
    };
    const config = typeConfig[type as keyof typeof typeConfig] || typeConfig.MAINTENANCE;
    return <Badge className={config.className}>{config.label}</Badge>;
  };

  const getShiftBadge = (shiftType?: string) => {
    if (!shiftType) return null;
    const shiftConfig = {
      MORNING: { label: 'Morning Shift', className: 'bg-yellow-100 text-yellow-800' },
      NIGHT: { label: 'Night Shift', className: 'bg-indigo-100 text-indigo-800' },
    };
    const config = shiftConfig[shiftType as keyof typeof shiftConfig];
    return config ? <Badge className={config.className}>{config.label}</Badge> : null;
  };

  const getUserShiftBadge = (shiftType?: string | null) => {
    if (!shiftType) return null;
    const shiftConfig = {
      MORNING: { label: 'Morning', className: 'bg-yellow-100 text-yellow-800' },
      NIGHT: { label: 'Night', className: 'bg-indigo-100 text-indigo-800' },
    };
    const config = shiftConfig[shiftType as keyof typeof shiftConfig];
    return config ? <Badge className={config.className}>{config.label}</Badge> : null;
  };

  const getStatusIcon = (dateDebut: string, dateFin: string) => {
    const now = new Date();
    const start = new Date(dateDebut);
    const end = new Date(dateFin);
    
    if (now < start) {
      return <Clock className="h-5 w-5 text-gray-400" title="Upcoming" />;
    } else if (now >= start && now <= end) {
      return <CheckCircle className="h-5 w-5 text-green-600" title="Active" />;
    } else {
      return <XCircle className="h-5 w-5 text-gray-400" title="Completed" />;
    }
  };

  const getStatusText = (dateDebut: string, dateFin: string) => {
    const now = new Date();
    const start = new Date(dateDebut);
    const end = new Date(dateFin);
    
    if (now < start) {
      return 'Upcoming';
    } else if (now >= start && now <= end) {
      return 'Active';
    } else {
      return 'Completed';
    }
  };

  const getStatusColor = (dateDebut: string, dateFin: string) => {
    const now = new Date();
    const start = new Date(dateDebut);
    const end = new Date(dateFin);
    
    if (now < start) {
      return 'text-gray-600';
    } else if (now >= start && now <= end) {
      return 'text-green-600';
    } else {
      return 'text-gray-400';
    }
  };

  const getDuration = (dateDebut: string, dateFin: string) => {
    const start = new Date(dateDebut);
    const end = new Date(dateFin);
    const diffTime = Math.abs(end.getTime() - start.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return `${diffDays} day${diffDays !== 1 ? 's' : ''}`;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getRoleColor = (role: string) => {
    const roleColors = {
      ADMIN: 'bg-purple-100 text-purple-800',
      CHETOP: 'bg-blue-100 text-blue-800',
      CHEFTECH: 'bg-green-100 text-green-800',
      TECHNICIEN: 'bg-orange-100 text-orange-800',
    };
    return roleColors[role as keyof typeof roleColors] || 'bg-gray-100 text-gray-800';
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
          <p className="text-gray-500">The planning you're looking for doesn't exist or has been removed.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" onClick={() => navigate(-1)}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold text-gray-900">{planning.identifiant_planning}</h1>
            {getTypeBadge(planning.type)}
            {getShiftBadge(planning.shift_type)}
            <div className={`flex items-center gap-1 ${getStatusColor(planning.date_debut, planning.date_fin)}`}>
              {getStatusIcon(planning.date_debut, planning.date_fin)}
              <span className="font-medium">{getStatusText(planning.date_debut, planning.date_fin)}</span>
            </div>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            Duration: {getDuration(planning.date_debut, planning.date_fin)}
          </p>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Main Info */}
        <div className="lg:col-span-2 space-y-6">
          {/* Schedule Information */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                Schedule Information
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-500">Start Date & Time</label>
                  <div className="text-lg font-semibold">{formatDate(planning.date_debut)}</div>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-500">End Date & Time</label>
                  <div className="text-lg font-semibold">{formatDate(planning.date_fin)}</div>
                </div>
              </div>
              
              {(planning.zone_travail && planning.zone_travail.trim() !== '') ? (
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-500">Work Zone</label>
                  <div className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-gray-400" />
                    <span className="text-lg font-semibold">{planning.zone_travail}</span>
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-500">Work Zone</label>
                  <div className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-gray-400" />
                    <span className="text-lg font-semibold text-gray-400">Not specified</span>
                  </div>
                </div>
              )}

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-500">Planning Type</label>
                <div className="flex items-center gap-2">
                  <Settings className="h-4 w-4 text-gray-400" />
                  <span className="font-medium capitalize">{planning.type.toLowerCase()}</span>
                  {planning.shift_type && (
                    <span className="text-gray-500">({planning.shift_type.toLowerCase()})</span>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-500">Created</label>
                <div className="text-sm text-gray-600">
                  {planning.created_at ? formatDate(planning.created_at) : 'N/A'}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Team Assignment */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5" />
                Team Assignment
              </CardTitle>
            </CardHeader>
            <CardContent>
              {planning.assigned_users.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <Users className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>No team members assigned to this planning</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {planning.assigned_users.map((user) => (
                    <div key={user.id} className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50">
                      <div className="flex items-center gap-3">
                        <div className="h-10 w-10 bg-gray-200 rounded-full flex items-center justify-center">
                          <User className="h-5 w-5 text-gray-600" />
                        </div>
                        <div>
                          <div className="font-medium">{user.nom}</div>
                          <div className="text-sm text-gray-500">{user.email}</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge className={getRoleColor(user.role)}>
                          {user.role}
                        </Badge>
                        {getUserShiftBadge(user.shift_type)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column - Status & Actions */}
        <div className="space-y-6">
          {/* Status Card */}
          <Card>
            <CardHeader>
              <CardTitle>Status Overview</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="text-center">
                {getStatusIcon(planning.date_debut, planning.date_fin)}
                <div className={`text-2xl font-bold mt-2 ${getStatusColor(planning.date_debut, planning.date_fin)}`}>
                  {getStatusText(planning.date_debut, planning.date_fin)}
                </div>
              </div>
              
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Duration:</span>
                  <span className="font-medium">{getDuration(planning.date_debut, planning.date_fin)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Team Size:</span>
                  <span className="font-medium">{planning.assigned_users.length} members</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Work Zone:</span>
                  <span className="font-medium">{planning.zone_travail || 'Not specified'}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button variant="outline" className="w-full justify-start">
                <Calendar className="mr-2 h-4 w-4" />
                View Calendar
              </Button>
              <Button variant="outline" className="w-full justify-start">
                <Users className="mr-2 h-4 w-4" />
                Contact Team
              </Button>
              <Button variant="outline" className="w-full justify-start">
                <Settings className="mr-2 h-4 w-4" />
                Export Details
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
