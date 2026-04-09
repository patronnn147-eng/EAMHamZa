import React, { useRef, useState } from 'react';
import { QRCodeSVG, QRCodeCanvas } from 'qrcode.react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Download, Printer, QrCode, Copy, CheckCheck } from 'lucide-react';
import type { Machine } from '@/lib/types';

interface MachineQRCodeProps {
    machine: Machine;
    /** Base URL (defaults to window.location.origin) */
    baseUrl?: string;
    /** Compact card mode for use inside grids */
    compact?: boolean;
}

export const MachineQRCode: React.FC<MachineQRCodeProps> = ({
    machine,
    baseUrl,
    compact = false,
}) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const [copied, setCopied] = useState(false);

    const origin = baseUrl ?? window.location.origin;
    const machineUrl = `${origin}/machines/${machine.id}`;

    // Download the QR code as PNG
    const handleDownload = () => {
        const canvas = document.querySelector<HTMLCanvasElement>(
            `#qr-canvas-${machine.id}`
        );
        if (!canvas) return;
        const link = document.createElement('a');
        link.download = `QR_${machine.nom.replace(/\s+/g, '_')}_${machine.id}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
    };

    // Copy URL to clipboard
    const handleCopy = async () => {
        await navigator.clipboard.writeText(machineUrl);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    // Print the QR code in a clean print window  
    const handlePrint = () => {
        const canvas = document.querySelector<HTMLCanvasElement>(
            `#qr-canvas-${machine.id}`
        );
        if (!canvas) return;
        const dataUrl = canvas.toDataURL('image/png');
        const win = window.open('', '_blank', 'width=400,height=500');
        if (!win) return;
        win.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>QR Code – ${machine.nom}</title>
          <style>
            body { font-family: sans-serif; text-align: center; padding: 40px; }
            img { width: 220px; height: 220px; display: block; margin: 0 auto 16px; }
            h2 { font-size: 18px; font-weight: 700; margin: 0 0 4px; }
            p  { font-size: 12px; color: #6b7280; margin: 0 0 8px; }
            .url { font-size: 10px; color: #9ca3af; word-break: break-all; }
          </style>
        </head>
        <body onload="window.print();window.close()">
          <img src="${dataUrl}" alt="QR Code" />
          <h2>${machine.nom}</h2>
          <p>${[machine.zone, machine.sous_zone, machine.ordre].filter(Boolean).join(' · ')}</p>
          <p class="url">${machineUrl}</p>
        </body>
      </html>
    `);
        win.document.close();
    };

    if (compact) {
        // Inline compact version: just buttons, no card shell
        return (
            <div className="flex items-center gap-1.5">
                {/* Hidden canvas for download/print */}
                <div className="hidden">
                    <QRCodeCanvas
                        id={`qr-canvas-${machine.id}`}
                        value={machineUrl}
                        size={256}
                        level="M"
                        includeMargin
                    />
                </div>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={handleDownload}
                    title="Télécharger QR Code"
                    className="h-8 px-2"
                >
                    <QrCode className="h-3.5 w-3.5 mr-1" />
                    QR
                </Button>
            </div>
        );
    }

    return (
        <Card className="overflow-hidden">
            {/* Blue accent top bar */}
            <div className="h-1 w-full bg-gradient-to-r from-blue-500 to-indigo-500" />
            <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                    <QrCode className="h-4 w-4 text-blue-300" />
                    QR Code — Accès rapide
                </CardTitle>
                <p className="text-xs text-blue-400">
                    Scannez pour accéder directement à cette machine
                </p>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* QR Code display */}
                <div className="flex flex-col items-center gap-4">
                    {/* SVG for visual display */}
                    <div className="p-3 bg-slate-800 border-2 border-blue-800/50 rounded-xl shadow-sm">
                        <QRCodeSVG
                            value={machineUrl}
                            size={180}
                            level="M"
                            includeMargin={false}
                            imageSettings={{
                                src: '',
                                height: 0,
                                width: 0,
                                excavate: false,
                            }}
                        />
                    </div>

                    {/* Hidden canvas for PNG download/print */}
                    <div className="hidden" aria-hidden>
                        <QRCodeCanvas
                            id={`qr-canvas-${machine.id}`}
                            value={machineUrl}
                            size={512}
                            level="M"
                            includeMargin
                        />
                    </div>

                    {/* Machine info badge */}
                    <div className="text-center">
                        <p className="font-semibold text-sm text-blue-50">{machine.nom}</p>
                        {(machine.zone || machine.sous_zone) && (
                            <p className="text-xs text-blue-400 mt-0.5">
                                {[machine.zone, machine.sous_zone, machine.ordre].filter(Boolean).join(' · ')}
                            </p>
                        )}
                        <Badge variant="secondary" className="mt-1.5 text-xs">
                            #{machine.id}
                        </Badge>
                    </div>
                </div>

                {/* URL display */}
                <div
                    className="flex items-center gap-2 bg-slate-800/50 border border-blue-700/50 rounded-lg px-3 py-2 cursor-pointer hover:bg-blue-50 hover:border-blue-200 transition-colors"
                    onClick={handleCopy}
                    title="Copier le lien"
                >
                    <span className="text-xs text-blue-300 truncate flex-1 font-mono">{machineUrl}</span>
                    {copied
                        ? <CheckCheck className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                        : <Copy className="h-3.5 w-3.5 text-blue-400 shrink-0" />
                    }
                </div>
                {copied && (
                    <p className="text-xs text-center text-emerald-600 -mt-2">Lien copié !</p>
                )}

                {/* Action buttons */}
                <div className="grid grid-cols-2 gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={handleDownload}
                        className="flex items-center gap-1.5"
                    >
                        <Download className="h-3.5 w-3.5" />
                        Télécharger PNG
                    </Button>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={handlePrint}
                        className="flex items-center gap-1.5"
                    >
                        <Printer className="h-3.5 w-3.5" />
                        Imprimer
                    </Button>
                </div>

                <p className="text-xs text-blue-400 text-center">
                    Format: QR code PNG haute résolution (512×512px)
                </p>
            </CardContent>
        </Card>
    );
};

export default MachineQRCode;
