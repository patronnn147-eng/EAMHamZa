import { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import {
  OrbitControls,
  Environment,
  SoftShadows,
  ContactShadows,
  Html,
} from '@react-three/drei';
import { MachineModel } from './MachineModel';
import { ErrorBoundary3D } from './ErrorBoundary3D';

const RISK_COLOR: Record<string, string> = {
  CRITICAL: '#ef4444',
  HIGH: '#f97316',
  MEDIUM: '#f59e0b',
  LOW: '#22c55e',
};

interface MachineViewer3DProps {
  machine: { nom: string } | null;
  mlPrediction: {
    health_score?: number;
    risk_level?: string;
    rul_days?: number;
  } | null;
}

export default function MachineViewer3D({ machine, mlPrediction }: Readonly<MachineViewer3DProps>) {
  if (!machine) return null;

  const healthScore = mlPrediction?.health_score ?? 50;
  const riskLevel =
    (['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].includes(mlPrediction?.risk_level ?? '')
      ? mlPrediction.risk_level
      : 'LOW') as 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  const rulDays = mlPrediction?.rul_days ?? null;

  return (
    <ErrorBoundary3D height={500}>
      <div style={{ height: 'min(500px, 60vh)', borderRadius: '0.75rem', overflow: 'hidden' }}>
        <Suspense
          fallback={
            <div
              style={{
                height: '100%',
                background: '#0a1628',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#475569',
                fontSize: '0.8rem',
                fontFamily: 'Manrope, sans-serif',
              }}
            >
              Loading 3D…
            </div>
          }
        >
          <Canvas
            shadows="soft"
            camera={{ position: [0, 1.5, 5], fov: 45 }}
            style={{ width: '100%', height: '100%' }}
          >
            <SoftShadows size={25} samples={10} />
            <Environment preset="warehouse" background backgroundBlurriness={0.6} />
            <directionalLight
              position={[5, 5, 5]}
              intensity={1.2}
              castShadow
              shadow-mapSize={[1024, 1024]}
            />
            <directionalLight position={[-5, 3, 5]} intensity={0.4} />
            <directionalLight position={[0, 5, -5]} intensity={0.25} />
            <ContactShadows position={[0, -0.7, 0]} opacity={0.5} blur={2} />
            <OrbitControls
              enablePan={false}
              minDistance={2}
              maxDistance={8}
              autoRotate
              autoRotateSpeed={0.5}
            />
            <MachineModel healthScore={healthScore} riskLevel={riskLevel} />
            <Html position={[1.5, 1.2, 0]} style={{ pointerEvents: 'none' }}>
              <div
                style={{
                  background: 'rgba(5, 11, 24, 0.88)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: '0.5rem',
                  padding: '0.75rem',
                  minWidth: 150,
                  fontFamily: 'Manrope, sans-serif',
                }}
              >
                <div
                  style={{
                    color: '#94a3b8',
                    fontSize: '0.6rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.1em',
                    marginBottom: '0.4rem',
                  }}
                >
                  Machine Health
                </div>
                <div
                  style={{
                    color: '#fff',
                    fontWeight: 700,
                    fontSize: '1.5rem',
                    marginBottom: '0.4rem',
                  }}
                >
                  {Math.round(healthScore)}%
                </div>
                {rulDays !== null && (
                  <div style={{ color: '#94a3b8', fontSize: '0.7rem', marginBottom: '0.4rem' }}>
                    RUL:{' '}
                    <span style={{ color: '#f59e0b', fontWeight: 600 }}>
                      {Math.round(rulDays)}d
                    </span>
                  </div>
                )}
                <div
                  style={{
                    display: 'inline-block',
                    background: RISK_COLOR[riskLevel] ?? '#22c55e',
                    color: '#fff',
                    fontSize: '0.6rem',
                    fontWeight: 700,
                    borderRadius: '0.25rem',
                    padding: '0.15rem 0.5rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                  }}
                >
                  {riskLevel}
                </div>
              </div>
            </Html>
          </Canvas>
        </Suspense>
      </div>
    </ErrorBoundary3D>
  );
}
