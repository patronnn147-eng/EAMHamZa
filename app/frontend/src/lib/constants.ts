export const ZONE_OPTIONS = [
    'ZONE CMS1 - COMPONENT SURFACE MOUNTING',
    'ZONE CMS2 - TEST ZONE (Résumé des Machines Essentielles)',
    'ZONE TEST FONCTIONNEL',
    'ZONE TEST WiFi',
    'ZONE ASSEMBLAGE',
    'ZONE EMBALLAGE',
    'ZONE QUALITÉ',
    'ZONE MAINTENANCE',
];

export const SOUS_ZONE_OPTIONS_BY_ZONE: Record<string, string[]> = {
    'ZONE CMS1 - COMPONENT SURFACE MOUNTING': [
        'CMS LINE 1 (e.g., BBS - Broadband Products)',
        'CMS LINE 2 (e.g., AVS - Audio Video Products)',
    ],
    'ZONE CMS2 - TEST ZONE (Résumé des Machines Essentielles)': [
        'TEST IN-SITU (Test des Composants)',
        'TEST FONCTIONNEL (Test de Fonctionnement)',
        'TEST WiFi (Test Sans Fil)',
    ],
    'ZONE TEST FONCTIONNEL': [],
    'ZONE TEST WiFi': [],
    'ZONE ASSEMBLAGE': [],
    'ZONE EMBALLAGE': [],
    'ZONE QUALITÉ': [],
    'ZONE MAINTENANCE': [],
};

export type OrdreTemplate = { ordre: number; nom: string; fonction?: string };

export const ORDRE_TEMPLATES: Record<string, Record<string, OrdreTemplate[]>> = {
    'ZONE CMS1 - COMPONENT SURFACE MOUNTING': {
        'CMS LINE 1 (e.g., BBS - Broadband Products)': [
            { ordre: 1, nom: 'Dépileur (Card Loader)' },
            { ordre: 2, nom: 'Machine de Sérigraphie (DEK/MPM)' },
            { ordre: 3, nom: 'Machine de Pose (Pick & Place)' },
            { ordre: 4, nom: 'Machine SPI (Solder Paste Inspection)' },
            { ordre: 5, nom: 'Machine 2D Scanner (Component Inspection)' },
            { ordre: 6, nom: 'Machine AOI 3D (Final Inspection)' },
            { ordre: 7, nom: 'Four de Refusions (Reflow Oven)' },
            { ordre: 8, nom: 'Poste Insertion Manuelle (Manual THT)' },
            { ordre: 9, nom: 'Machine de Brassage à la Vague (Wave Soldering)' },
        ],
        'CMS LINE 2 (e.g., AVS - Audio Video Products)': [
            { ordre: 1, nom: 'Dépileur' },
            { ordre: 2, nom: 'Machine de Sérigraphie' },
            { ordre: 3, nom: 'Machine de Pose' },
            { ordre: 4, nom: 'Machine SPI' },
            { ordre: 5, nom: 'Machine 2D Scanner' },
            { ordre: 6, nom: 'Machine AOI 3D' },
            { ordre: 7, nom: 'Four de Refusions' },
            { ordre: 8, nom: 'Poste Insertion Manuelle' },
            { ordre: 9, nom: 'Machine de Brassage à la Vague' },
        ],
    },
    'ZONE CMS2 - TEST ZONE (Résumé des Machines Essentielles)': {
        'TEST IN-SITU (Test des Composants)': [
            { ordre: 1, nom: 'Interface de Test (Bed of Nails)', fonction: 'Interface avec sondes pour accéder aux composants' },
            { ordre: 2, nom: 'Testeur Marconi 4220', fonction: 'Testeur principal qui effectue tous les tests électroniques' },
        ],
        'TEST FONCTIONNEL (Test de Fonctionnement)': [
            { ordre: 1, nom: 'Banc TF' },
            { ordre: 2, nom: 'BFE (Banc Front End)' },
            { ordre: 3, nom: 'BAV (Banc Audio Video)' },
            { ordre: 4, nom: 'Routeur' },
        ],
        'TEST WiFi (Test Sans Fil)': [
            { ordre: 1, nom: 'PC avec Logiciels de Test' },
            { ordre: 2, nom: 'Caisson Faraday (Shielding Box)' },
            { ordre: 3, nom: 'IQflex Analyzer' },
            { ordre: 4, nom: 'Routeur' },
            { ordre: 5, nom: 'Switch' },
            { ordre: 6, nom: 'Atténuateurs (30dB, 6dB, 3dB)' },
            { ordre: 7, nom: 'Power Splitter' },
        ],
    },
};
