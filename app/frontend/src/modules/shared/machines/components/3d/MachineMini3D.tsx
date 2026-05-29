import { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { Float } from '@react-three/drei';
import { MachineModel } from './MachineModel';
import { ErrorBoundary3D } from './ErrorBoundary3D';

interface MachineMini3DProps {
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
}

export function MachineMini3D({ riskLevel }: MachineMini3DProps) {
  return (
    <ErrorBoundary3D height={120}>
      <div style={{ width: 120, height: 120, flexShrink: 0 }}>
        <Canvas
          frameloop="always"
          dpr={[1, 1.5]}
          camera={{ position: [0, 0.5, 3.5], fov: 50 }}
          style={{ width: '100%', height: '100%', borderRadius: '0.5rem' }}
        >
          <ambientLight intensity={0.6} />
          <pointLight position={[2, 2, 2]} intensity={0.8} />
          <Suspense fallback={null}>
            <Float
              speed={1.4}
              rotationIntensity={0.4}
              floatIntensity={0.6}
              floatingRange={[-0.05, 0.05]}
            >
              <MachineModel
                healthScore={50}
                riskLevel={riskLevel}
                autoRotate
                rotationSpeed={0.3}
              />
            </Float>
          </Suspense>
        </Canvas>
      </div>
    </ErrorBoundary3D>
  );
}
