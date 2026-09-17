import React, { useState } from 'react';
import { ImageOff } from 'lucide-react';

interface MachineImageProps {
    src?: string | null;
    alt: string;
    /** Square thumbnail edge. Ignored when width/height are given. */
    size?: number;
    width?: number | string;
    height?: number;
    /** Placeholder glyph size; defaults to a fraction of the box height. */
    iconSize?: number;
}

/**
 * Photo of the physical machine, as set by whoever created it.
 *
 * Falls back to a neutral placeholder in two cases, not one: no image was ever
 * set, and the stored URL fails to load. `image_url` is a free-text field on
 * the machine form, so a dead link is at least as likely as an empty value —
 * without the onError path those machines would render a broken-image icon.
 */
export function MachineImage({
    src,
    alt,
    size = 120,
    width,
    height,
    iconSize,
}: Readonly<MachineImageProps>) {
    const [failed, setFailed] = useState(false);

    const boxWidth = width ?? size;
    const boxHeight = height ?? size;
    const glyph = iconSize ?? Math.round(boxHeight * 0.22);

    const box: React.CSSProperties = {
        width: boxWidth,
        height: boxHeight,
        flexShrink: 0,
        borderRadius: '0.75rem',
        border: '1px solid rgba(255,255,255,0.08)',
        background: 'rgba(255,255,255,0.03)',
        overflow: 'hidden',
    };

    if (!src || failed) {
        return (
            <div
                style={{
                    ...box,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '0.4rem',
                }}
            >
                <ImageOff size={glyph} color="#475569" />
                <span
                    style={{
                        fontSize: '0.55rem',
                        color: '#475569',
                        fontFamily: 'Space Grotesk, monospace',
                        textTransform: 'uppercase',
                        letterSpacing: '0.1em',
                    }}
                >
                    No image
                </span>
            </div>
        );
    }

    return (
        <img
            src={src}
            alt={alt}
            onError={() => setFailed(true)}
            style={{ ...box, objectFit: 'cover', display: 'block' }}
        />
    );
}
