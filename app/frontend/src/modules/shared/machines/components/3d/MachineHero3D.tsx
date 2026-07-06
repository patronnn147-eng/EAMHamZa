import { useRef, useEffect, Suspense } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { Environment, AccumulativeShadows, RandomizedLight } from '@react-three/drei';
import * as THREE from 'three';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { MachineModel } from './MachineModel';
import { ErrorBoundary3D } from './ErrorBoundary3D';

gsap.registerPlugin(ScrollTrigger);

interface MachineHero3DProps {
  machine: { nom: string } | null;
  mlPrediction: { health_score?: number; risk_level?: string } | null;
}

interface HeroSceneProps {
  healthScore: number;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  wrapperRef: React.RefObject<HTMLDivElement>;
}

function HeroScene({ healthScore, riskLevel, wrapperRef }: Readonly<HeroSceneProps>) {
  const { camera } = useThree();

  useEffect(() => {
    if (!wrapperRef.current) return;

    const perspCam = camera as THREE.PerspectiveCamera;

    const xTo = gsap.quickTo(perspCam.rotation, 'y', { duration: 0.6, ease: 'power3' });
    const zTo = gsap.quickTo(perspCam.position, 'z', { duration: 0.6, ease: 'power3' });

    const trigger = ScrollTrigger.create({
      trigger: wrapperRef.current,
      start: 'top top',
      end: '+=200',
      scrub: 1,
      onUpdate: (self) => {
        xTo(-self.progress * 0.4);
        zTo(5 - self.progress * 1.5);
      },
    });

    return () => trigger.kill();
  }, [camera, wrapperRef]);

  return (
    <>
      <Environment preset="warehouse" environmentIntensity={0.8} />
      <directionalLight
        position={[5, 5, 5]}
        intensity={1.2}
        castShadow
        shadow-mapSize={[1024, 1024]}
      />
      <directionalLight position={[-5, 3, 5]} intensity={0.4} />
      <directionalLight position={[0, 5, -5]} intensity={0.25} />
      <AccumulativeShadows position={[0, -0.7, 0]} scale={6} frames={40} opacity={0.6}>
        <RandomizedLight amount={4} radius={3} position={[5, 5, -5]} />
      </AccumulativeShadows>
      <MachineModel healthScore={healthScore} riskLevel={riskLevel} autoRotate rotationSpeed={0.4} />
    </>
  );
}

export function MachineHero3D({ machine, mlPrediction }: Readonly<MachineHero3DProps>) {
  const wrapperRef = useRef<HTMLDivElement>(null!);

  if (!machine) return null;
  const healthScore = mlPrediction?.health_score ?? 50;
  const riskLevel =
    (['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].includes(mlPrediction?.risk_level ?? '')
      ? mlPrediction.risk_level
      : 'LOW') as 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

  return (
    <div ref={wrapperRef} style={{ height: 280, position: 'relative', marginBottom: '1.25rem' }}>
      <ErrorBoundary3D height={280}>
        <Suspense
          fallback={
            <div
              style={{
                height: 280,
                background: '#0a1628',
                borderRadius: '0.75rem',
              }}
            />
          }
        >
          <Canvas
            shadows
            camera={{ position: [0, 1.5, 5], fov: 45 }}
            style={{ width: '100%', height: '100%', borderRadius: '0.75rem' }}
          >
            <HeroScene
              healthScore={healthScore}
              riskLevel={riskLevel}
              wrapperRef={wrapperRef}
            />
          </Canvas>
        </Suspense>
      </ErrorBoundary3D>
    </div>
  );
}
