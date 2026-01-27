import { useEffect, useState } from 'react';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Search, Plus, FileText, Image, Video, File, Download } from 'lucide-react';
import type { Archive } from '@/lib/types';

export default function Archives() {
  const [archives, setArchives] = useState<Archive[]>([]);
  const [filteredArchives, setFilteredArchives] = useState<Archive[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState('ALL');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchArchives();
  }, []);

  useEffect(() => {
    let filtered = archives;

    if (searchTerm) {
      filtered = filtered.filter(
        (a) =>
          a.nom.toLowerCase().includes(searchTerm.toLowerCase()) ||
          a.identifiant_archive.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    if (typeFilter !== 'ALL') {
      filtered = filtered.filter((a) => a.type === typeFilter);
    }

    setFilteredArchives(filtered);
  }, [searchTerm, typeFilter, archives]);

  const fetchArchives = async () => {
    try {
      const response = await client.entities.archives.query({
        query: {},
        sort: '-date_archivage',
        limit: 100
      });
      const archivesList = response.data.items || [];
      setArchives(archivesList);
      setFilteredArchives(archivesList);
    } catch (error) {
      console.error('Error fetching archives:', error);
    } finally {
      setLoading(false);
    }
  };

  const getTypeIcon = (type: string) => {
    const icons = {
      DOCUMENT: FileText,
      IMAGE: Image,
      VIDEO: Video,
      AUTRE: File,
    };
    const Icon = icons[type as keyof typeof icons] || File;
    return <Icon className="h-5 w-5" />;
  };

  const getTypeBadge = (type: string) => {
    const typeConfig = {
      DOCUMENT: { label: 'Document', className: 'bg-blue-100 text-blue-800' },
      IMAGE: { label: 'Image', className: 'bg-green-100 text-green-800' },
      VIDEO: { label: 'Video', className: 'bg-purple-100 text-purple-800' },
      AUTRE: { label: 'Other', className: 'bg-gray-100 text-gray-800' },
    };
    const config = typeConfig[type as keyof typeof typeConfig] || typeConfig.AUTRE;
    return <Badge className={config.className}>{config.label}</Badge>;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Archives</h2>
          <p className="mt-1 text-sm text-gray-500">
            Access and manage archived documents and files
          </p>
        </div>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          Upload Archive
        </Button>
      </div>

      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            type="text"
            placeholder="Search archives by name or ID..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-full sm:w-[180px]">
            <SelectValue placeholder="Filter by type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">All Types</SelectItem>
            <SelectItem value="DOCUMENT">Document</SelectItem>
            <SelectItem value="IMAGE">Image</SelectItem>
            <SelectItem value="VIDEO">Video</SelectItem>
            <SelectItem value="AUTRE">Other</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredArchives.length === 0 ? (
          <div className="col-span-full text-center py-12">
            <p className="text-gray-500">No archives found</p>
          </div>
        ) : (
          filteredArchives.map((archive) => (
            <Card key={archive.id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2 flex-1">
                    {getTypeIcon(archive.type)}
                    <div className="flex-1 min-w-0">
                      <CardTitle className="text-base truncate">{archive.nom}</CardTitle>
                      <p className="text-xs text-gray-500 mt-1">{archive.identifiant_archive}</p>
                    </div>
                  </div>
                  {getTypeBadge(archive.type)}
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Archived:</span>
                    <span className="font-medium">
                      {new Date(archive.date_archivage).toLocaleDateString()}
                    </span>
                  </div>
                  {archive.ordre_travail_id && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Work Order:</span>
                      <span className="font-medium">#{archive.ordre_travail_id}</span>
                    </div>
                  )}
                  {archive.object_key && (
                    <div className="bg-gray-50 rounded p-2">
                      <p className="text-xs text-gray-600 truncate">
                        Key: {archive.object_key}
                      </p>
                    </div>
                  )}
                </div>
                <div className="mt-4 flex gap-2">
                  <Button variant="outline" size="sm" className="flex-1">
                    <Download className="mr-2 h-4 w-4" />
                    Download
                  </Button>
                  <Button variant="outline" size="sm" className="flex-1">
                    View
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}