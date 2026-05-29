# Machine Detail 3D Motion UI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add immersive 3D motion UI to the machine detail page using React Three Fiber and GSAP — hero banner, dedicated 3D tab, and mini floating model inside the Health Donut card.

**Architecture:** Shared `MachineModel` procedural R3F component (no GLTF) consumed by three wrappers: hero banner (GSAP ScrollTrigger camera scrub), lazy-loaded 3D tab (OrbitControls), and 120×120 mini canvas (Drei Float). All 3D files live under `app/frontend/src/modules/shared/machines/components/3d/`.

**Tech Stack:** `@react-three/fiber`, `@react-three/drei`, `three`, `gsap`, `@gsap/react`. Build tool: Vite. Package manager: pnpm@8.10.0.

---

## File Map

| Status | File |
|--------|------|
| Create | `app/frontend/src/modules/shared/machines/components/3d/ErrorBoundary3D.tsx` |
| Create | `app/frontend/src/modules/shared/machines/components/3d/MachineModel.tsx` |
| Create | `app/frontend/src/modules/shared/machines/components/3d/MachineMini3D.tsx` |
| Create | `app/frontend/src/modules/shared/machines/components/3d/MachineHero3D.tsx` |
| Create | `app/frontend/src/modules/shared/machines/components/3d/MachineViewer3D.tsx` |
| Modify | `app/frontend/src/modules/shared/MachineDetailPage.tsx` |
| Modify | `app/frontend/src/modules/shared/machines/components/MLIntelligenceTab.tsx` |

---

## Task 1: Install Packages

**Files:**
- Modify: `app/frontend/package.json` (via pnpm)

- [ ] **Step 1: Install runtime + type packages**

```bash
cd app/frontend
pnpm add @react-three/fiber @react-three/drei three gsap @gsap/react
pnpm add -D @types/three
```

Expected: `node_modules/@react-three`, `node_modules/three`, `node_modules/gsap` present. No errors.

- [ ] **Step 2: Verify installs**

```bash
cd app/frontend
pnpm list @react-three/fiber @react-three/drei three gsap @gsap/react @types/three
```

Expected: All six packages listed with version numbers. `@react-three/fiber ^8.x`, `three ^0.x`, `gsap ^3.x`.

- [ ] **Step 3: Commit**

```bash
git add app/frontend/package.json app/frontend/pnpm-lock.yaml
git commit -m "chore(frontend): install r3f, drei, three, gsap for 3D motion UI"
```

---

## Task 2: ErrorBoundary3D

**Files:**
- Create: `app/frontend/src/modules/shared/machines/components/3d/ErrorBoundary3D.tsx`

- [ ] **Step 1: Create class-based error boundary**

Create `app/frontend/src/modules/shared/machines/components/3d/ErrorBoundary3D.tsx`:

```tsx
import { Component, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  height?: number;
}

interface State {
  hasError: boolean;
}

export class ErrorBoundary3D extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            height: this.props.height ?? 280,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: '#0a1628',
            borderRadius: '0.75rem',
            color: '#475569',
            gap: '0.5rem',
            fontSize: '0.8rem',
            fontFamily: 'Manrope, sans-serif',
          }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <rect x="2" y="7" width="20" height="14" rx="2" />
            <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
            <line x1="12" y1="12" x2="12" y2="16" />
            <line x1="12" y1="18.5" x2="12.01" y2="18.5" strokeLinecap="round" strokeWidth="2" />
          </svg>
          3D view unavailable
        </div>
      );
    }
    return this.props.children;
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add app/frontend/src/modules/shared/machines/components/3d/ErrorBoundary3D.tsx
git commit -m "feat(3d): add ErrorBoundary3D for per-canvas WebGL error isolation"
```

---

## Task 3: MachineModel

The core shared R3F component. Procedural geometry (no GLTF). Fresnel rim glow via `onBeforeCompile`. Rotor spins via `useFrame`.

**Files:**
- Create: `app/frontend/src/modules/shared/machines/components/3d/MachineModel.tsx`

- [ ] **Step 1: Create MachineModel.tsx**

Create `app/frontend/src/modules/shared/machines/components/3d/MachineModel.tsx`:

```tsx
import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { RoundedBox } from '@react-three/drei';
import * as THREE from 'three';

export interface MachineModelProps {
  healthScore?: number;
  riskLevel?: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  autoRotate?: boolean;
  rotationSpeed?: number;
}

const RISK_EMISSIVE: Record<string, string> = {
  CRITICAL: '#ef4444',
  HIGH: '#f97316',
  MEDIUM: '#f59e0b',
  LOW: '#22c55e',
};

export function MachineModel({
  healthScore = 50,
  riskLevel = 'LOW',
  autoRotate = false,
  rotationSpeed = 0.4,
}: MachineModelProps) {
  const groupRef = useRef<THREE.Group>(null!);
  const rotorRef = useRef<THREE.Mesh>(null!);

  // Ref holds live shader uniforms after onBeforeCompile fires
  const shaderUniformsRef = useRef<{
    uTime: { value: number };
    uHealthScore: { value: number };
  } | null>(null);

  // Body material with Fresnel rim glow via onBeforeCompile
  const bodyMat = useMemo(() => {
    const mat = new THREE.MeshStandardMaterial({
      metalness: 0.85,
      roughness: 0.15,
      color: '#78909c',
    });

    mat.onBeforeCompile = (shader) => {
      shader.uniforms.uTime = { value: 0 };
      shader.uniforms.uHealthScore = { value: 0.5 };

      // Vertex: declare varying + compute world position
      shader.vertexShader = shader.vertexShader.replace(
        '#include <common>',
        '#include <common>\nvarying vec3 vWorldPos;'
      );
      shader.vertexShader = shader.vertexShader.replace(
        '#include <begin_vertex>',
        '#include <begin_vertex>\nvWorldPos = (modelMatrix * vec4(position, 1.0)).xyz;'
      );

      // Fragment: declare uniforms + varying, inject rim after output
      shader.fragmentShader = shader.fragmentShader.replace(
        '#include <common>',
        '#include <common>\nvarying vec3 vWorldPos;\nuniform float uTime;\nuniform float uHealthScore;'
      );
      shader.fragmentShader = shader.fragmentShader.replace(
        '#include <dithering_fragment>',
        `#include <dithering_fragment>
        {
          vec3 viewDir = normalize(cameraPosition - vWorldPos);
          float fresnel = pow(1.0 - clamp(dot(viewDir, normal), 0.0, 1.0), 3.0);
          vec3 rimColor = mix(vec3(0.94, 0.27, 0.27), vec3(0.13, 0.77, 0.37), uHealthScore);
          float pulse = sin(uTime * 2.0) * 0.5 + 0.5;
          float rimStrength = 0.25 + pulse * (1.0 - uHealthScore) * 0.35;
          gl_FragColor.rgb += rimColor * fresnel * rimStrength;
        }`
      );

      shaderUniformsRef.current = shader.uniforms as any;
    };

    return mat;
  }, []);

  const metalMat = useMemo(
    () =>
      new THREE.MeshStandardMaterial({ metalness: 0.9, roughness: 0.1, color: '#546e7a' }),
    []
  );

  const healthRingMat = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        emissive: RISK_EMISSIVE[riskLevel] ?? '#22c55e',
        emissiveIntensity: 1.5,
        toneMapped: false,
      }),
    [riskLevel]
  );

  useFrame(({ clock }, delta) => {
    // Rotor spin
    if (rotorRef.current) {
      rotorRef.current.rotation.y += delta * rotationSpeed;
    }
    // Group auto-rotate
    if (autoRotate && groupRef.current) {
      groupRef.current.rotation.y += delta * 0.3;
    }
    // Update Fresnel uniforms
    if (shaderUniformsRef.current) {
      shaderUniformsRef.current.uTime.value = clock.elapsedTime;
      shaderUniformsRef.current.uHealthScore.value = healthScore / 100;
    }
  });

  return (
    <group ref={groupRef}>
      {/* Body */}
      <RoundedBox args={[2, 1.4, 1]} radius={0.08} smoothness={4} castShadow receiveShadow>
        <primitive object={bodyMat} attach="material" />
      </RoundedBox>

      {/* Left side panel */}
      <mesh position={[-1.075, 0, 0]} castShadow receiveShadow>
        <boxGeometry args={[0.15, 1.0, 1.05]} />
        <primitive object={bodyMat} attach="material" />
      </mesh>

      {/* Right side panel */}
      <mesh position={[1.075, 0, 0]} castShadow receiveShadow>
        <boxGeometry args={[0.15, 1.0, 1.05]} />
        <primitive object={bodyMat} attach="material" />
      </mesh>

      {/* Rotor on top */}
      <mesh ref={rotorRef} position={[0, 0.85, 0]} castShadow receiveShadow>
        <cylinderGeometry args={[0.25, 0.25, 0.3, 16]} />
        <primitive object={metalMat} attach="material" />
      </mesh>

      {/* Belt loop around mid-section */}
      <mesh position={[0, 0, 0]} rotation={[Math.PI / 2, 0, 0]} castShadow receiveShadow>
        <torusGeometry args={[0.55, 0.06, 8, 32]} />
        <primitive object={metalMat} attach="material" />
      </mesh>

      {/* Health ring at base */}
      <mesh position={[0, -0.72, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[1.1, 1.2, 64]} />
        <primitive object={healthRingMat} attach="material" />
      </mesh>

      {/* Exhaust ports on back face */}
      {([-0.4, 0, 0.4] as const).map((x, i) => (
        <mesh key={i} position={[x, 0.2, -0.55]} castShadow receiveShadow>
          <cylinderGeometry args={[0.06, 0.06, 0.2, 8]} />
          <primitive object={metalMat} attach="material" />
        </mesh>
      ))}
    </group>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd app/frontend
npx tsc --noEmit --project tsconfig.json 2>&1 | grep "3d/MachineModel"
```

Expected: No errors mentioning `MachineModel.tsx`.

- [ ] **Step 3: Commit**

```bash
git add app/frontend/src/modules/shared/machines/components/3d/MachineModel.tsx
git commit -m "feat(3d): add MachineModel — procedural R3F mesh with Fresnel rim shader"
```

---

## Task 4: MachineMini3D

120×120 canvas with Drei Float animation. `frameloop="always"` required — Drei `<Float>` uses `useFrame` internally.

**Files:**
- Create: `app/frontend/src/modules/shared/machines/components/3d/MachineMini3D.tsx`

- [ ] **Step 1: Create MachineMini3D.tsx**

Create `app/frontend/src/modules/shared/machines/components/3d/MachineMini3D.tsx`:

```tsx
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
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd app/frontend
npx tsc --noEmit --project tsconfig.json 2>&1 | grep "3d/MachineMini3D"
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add app/frontend/src/modules/shared/machines/components/3d/MachineMini3D.tsx
git commit -m "feat(3d): add MachineMini3D — 120x120 Float canvas for ML Intelligence card"
```

---

## Task 5: MachineHero3D

Hero banner Canvas (280px). GSAP ScrollTrigger scrubs camera Z and rotation Y as user scrolls past the hero. Camera moves from front (Z=5) to 3/4 view (Z=3.5, rotationY=-0.4) over 200px of scroll.

**Files:**
- Create: `app/frontend/src/modules/shared/machines/components/3d/MachineHero3D.tsx`

- [ ] **Step 1: Create MachineHero3D.tsx**

Create `app/frontend/src/modules/shared/machines/components/3d/MachineHero3D.tsx`:

```tsx
import { useRef, useEffect, Suspense } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { Environment, AccumulativeShadows, RandomizedLight } from '@react-three/drei';
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

function HeroScene({ healthScore, riskLevel, wrapperRef }: HeroSceneProps) {
  const { camera } = useThree();

  useEffect(() => {
    if (!wrapperRef.current) return;

    const xTo = gsap.quickTo(camera.rotation, 'y', { duration: 0.6, ease: 'power3' });
    const zTo = gsap.quickTo(camera.position, 'z', { duration: 0.6, ease: 'power3' });

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

export function MachineHero3D({ machine, mlPrediction }: MachineHero3DProps) {
  if (!machine) return null;

  const wrapperRef = useRef<HTMLDivElement>(null!);
  const healthScore = mlPrediction?.health_score ?? 50;
  const riskLevel =
    (['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].includes(mlPrediction?.risk_level ?? '')
      ? mlPrediction!.risk_level
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
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd app/frontend
npx tsc --noEmit --project tsconfig.json 2>&1 | grep "3d/MachineHero3D"
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add app/frontend/src/modules/shared/machines/components/3d/MachineHero3D.tsx
git commit -m "feat(3d): add MachineHero3D — hero banner with GSAP ScrollTrigger camera scrub"
```

---

## Task 6: MachineViewer3D

Lazy-loaded dedicated 3D tab. Default export (required by `React.lazy`). Full OrbitControls, soft shadows, warehouse environment, HTML data overlay.

**Files:**
- Create: `app/frontend/src/modules/shared/machines/components/3d/MachineViewer3D.tsx`

- [ ] **Step 1: Create MachineViewer3D.tsx**

Create `app/frontend/src/modules/shared/machines/components/3d/MachineViewer3D.tsx`:

```tsx
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

export default function MachineViewer3D({ machine, mlPrediction }: MachineViewer3DProps) {
  if (!machine) return null;

  const healthScore = mlPrediction?.health_score ?? 50;
  const riskLevel =
    (['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].includes(mlPrediction?.risk_level ?? '')
      ? mlPrediction!.risk_level
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
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd app/frontend
npx tsc --noEmit --project tsconfig.json 2>&1 | grep "3d/MachineViewer3D"
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add app/frontend/src/modules/shared/machines/components/3d/MachineViewer3D.tsx
git commit -m "feat(3d): add MachineViewer3D — lazy-loaded 3D tab with OrbitControls and HTML overlay"
```

---

## Task 7: MachineDetailPage — Hero + 3D Tab

Add `<MachineHero3D>` between header row and tabs. Add "3D Vue" as third tab with `React.lazy`. Change tab grid from 2 to 3 columns.

**Files:**
- Modify: `app/frontend/src/modules/shared/MachineDetailPage.tsx`

Key locations in current file:
- Line 1: `import { useEffect, useState } from 'react';` — add `lazy, Suspense`
- Lines 9–35: Lucide imports — add `Box as BoxIcon`
- Lines 40–41: Existing component imports — add `MachineHero3D` import
- After line 41: Add lazy import for `MachineViewer3D`
- Line 299: `{/* ── Full-width Tabs ── */}` — insert `<MachineHero3D>` above the `<Tabs>` component
- Line 301: `className="grid grid-cols-2 w-full max-w-sm"` — change to `"grid grid-cols-3 w-full max-w-lg"`
- Lines 305–308: After the Historique `TabsTrigger`, add the 3D Vue trigger
- After line 317 (end of ML tab content): Add the 3D Vue tab content

- [ ] **Step 1: Add `lazy` and `Suspense` to React import**

In `app/frontend/src/modules/shared/MachineDetailPage.tsx`, change line 1:

```tsx
import { useEffect, useState, lazy, Suspense } from 'react';
```

- [ ] **Step 2: Add `Box as BoxIcon` to Lucide imports**

In `app/frontend/src/modules/shared/MachineDetailPage.tsx`, find the Lucide import block (lines 25–35) and add `Box`:

```tsx
import {
    ArrowLeft,
    MapPin,
    History,
    FileText,
    AlertCircle,
    Activity,
    User,
    Beaker,
    Brain,
    Box,
} from 'lucide-react';
```

- [ ] **Step 3: Add component imports after line 41**

After `import { TelemetrySimulator } from './machines/components/TelemetrySimulator';` (line 41), add:

```tsx
import { MachineHero3D } from './machines/components/3d/MachineHero3D';

const MachineViewer3D = lazy(() => import('./machines/components/3d/MachineViewer3D'));
```

- [ ] **Step 4: Insert `<MachineHero3D>` above the Tabs component**

Find the comment `{/* ── Full-width Tabs ── */}` at line 299. Insert the hero above the `<Tabs>` component:

```tsx
            {/* ── Full-width Tabs ── */}
            <MachineHero3D machine={machine} mlPrediction={mlPrediction as any} />
            <Tabs defaultValue="ml" className="w-full">
```

- [ ] **Step 5: Expand TabsList to 3 columns**

Change line 301 from:
```tsx
                <TabsList className="grid grid-cols-2 w-full max-w-sm">
```
to:
```tsx
                <TabsList className="grid grid-cols-3 w-full max-w-lg">
```

- [ ] **Step 6: Add 3D Vue TabsTrigger after Historique**

After the Historique `TabsTrigger` (after line 307), add:

```tsx
                    <TabsTrigger value="3d" className="flex items-center gap-1.5 text-sm">
                        <Box className="h-3.5 w-3.5" /> 3D Vue
                    </TabsTrigger>
```

- [ ] **Step 7: Add 3D Vue TabsContent after ML tab content**

After the closing `</TabsContent>` of the ML tab (after line 317), add:

```tsx
                {/* 3D Vue Tab — lazy-loaded canvas */}
                <TabsContent value="3d" className="mt-4">
                    <Suspense
                        fallback={
                            <div
                                style={{
                                    height: 'min(500px, 60vh)',
                                    background: '#0a1628',
                                    borderRadius: '0.75rem',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    color: '#475569',
                                    fontSize: '0.8rem',
                                    fontFamily: 'Manrope, sans-serif',
                                }}
                            >
                                Chargement 3D…
                            </div>
                        }
                    >
                        <MachineViewer3D machine={machine} mlPrediction={mlPrediction as any} />
                    </Suspense>
                </TabsContent>
```

- [ ] **Step 8: Verify TypeScript**

```bash
cd app/frontend
npx tsc --noEmit --project tsconfig.json 2>&1 | grep "MachineDetailPage"
```

Expected: No errors.

- [ ] **Step 9: Commit**

```bash
git add app/frontend/src/modules/shared/MachineDetailPage.tsx
git commit -m "feat(ui): add 3D hero banner and 3D Vue tab to MachineDetailPage"
```

---

## Task 8: MLIntelligenceTab — Mini 3D in Health Donut Card

The Health Donut card at line 410 currently has `display: 'flex', flexDirection: 'column', alignItems: 'center'`. Change to a flex row: `MachineMini3D` on the left, existing DonutGauge + text on the right.

**Files:**
- Modify: `app/frontend/src/modules/shared/machines/components/MLIntelligenceTab.tsx`

- [ ] **Step 1: Add MachineMini3D import**

At the top of `app/frontend/src/modules/shared/machines/components/MLIntelligenceTab.tsx`, after the existing imports, add:

```tsx
import { MachineMini3D } from './3d/MachineMini3D';
```

(Add after any existing import statements, before the component definitions.)

- [ ] **Step 2: Replace the Health Donut card JSX**

Find the Health Donut card starting at line 410. The current code is:

```tsx
                {/* Health Donut */}
                <div style={{ ...glassAlt, padding: '2rem', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', gridRow: 'span 1' }}>
                    {p ? (
                        <>
                            <DonutGauge score={healthScore} />
                            <h4 style={{ fontSize: '1rem', fontWeight: 700, color: '#fff', textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: '1.25rem', marginBottom: '0.35rem' }}>
                                Unified Health
                            </h4>
                            <p style={{ fontSize: '0.75rem', color: '#94a3b8', maxWidth: 220 }}>
                                {isAnomaly ? 'Anomalous behaviour detected. Immediate attention recommended.' : 'DST-fused score across 8 active models.'}
                            </p>
                        </>
                    ) : (
                        <p style={{ color: '#475569', fontSize: '0.8rem' }}>No ML data yet</p>
                    )}
                </div>
```

Replace with:

```tsx
                {/* Health Donut */}
                <div style={{ ...glassAlt, padding: '1.25rem', display: 'flex', alignItems: 'center', gap: '1rem', gridRow: 'span 1' }}>
                    <MachineMini3D
                        riskLevel={
                            (['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].includes(riskLevel)
                                ? riskLevel
                                : 'LOW') as 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
                        }
                    />
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center' }}>
                        {p ? (
                            <>
                                <DonutGauge score={healthScore} />
                                <h4 style={{ fontSize: '1rem', fontWeight: 700, color: '#fff', textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: '1.25rem', marginBottom: '0.35rem' }}>
                                    Unified Health
                                </h4>
                                <p style={{ fontSize: '0.75rem', color: '#94a3b8', maxWidth: 220 }}>
                                    {isAnomaly ? 'Anomalous behaviour detected. Immediate attention recommended.' : 'DST-fused score across 8 active models.'}
                                </p>
                            </>
                        ) : (
                            <p style={{ color: '#475569', fontSize: '0.8rem' }}>No ML data yet</p>
                        )}
                    </div>
                </div>
```

- [ ] **Step 3: Verify TypeScript**

```bash
cd app/frontend
npx tsc --noEmit --project tsconfig.json 2>&1 | grep "MLIntelligenceTab"
```

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add app/frontend/src/modules/shared/machines/components/MLIntelligenceTab.tsx
git commit -m "feat(ui): embed MachineMini3D in Health Donut card of ML Intelligence tab"
```

---

## Task 9: Smoke Test

- [ ] **Step 1: Start frontend dev server**

```bash
cd app/frontend
pnpm dev
```

Expected: `VITE ready on http://localhost:3000`. No import errors in terminal.

- [ ] **Step 2: Run TypeScript check across whole frontend**

```bash
cd app/frontend
npx tsc --noEmit --project tsconfig.json
```

Expected: 0 errors.

- [ ] **Step 3: Manual test checklist**

Navigate to any machine detail page (e.g. `http://localhost:3000/machines/1`). Verify:

1. **Hero renders** — 280px dark canvas with metallic machine model above the tab bar. No blank space, no console errors.
2. **Hero scroll** — scroll down while the hero is at top of viewport; camera should glide from front view to 3/4 view (slight Y rotation, Z shortens).
3. **3D Vue tab** — click the "3D Vue" tab; spinner/fallback briefly, then full 3D canvas appears. OrbitControls work (drag rotates, scroll zooms). Auto-rotate resumes after releasing mouse.
4. **ML mini** — the Health Donut card shows the mini floating machine model (120×120) to the left of the DonutGauge. Machine floats gently.
5. **Health ring color** — ring at base of machine matches risk_level: red=CRITICAL, orange=HIGH, amber=MEDIUM, green=LOW.
6. **Fresnel rim** — machine body has a visible rim glow effect. At CRITICAL risk the rim pulses red; at LOW it glows green.
7. **Tab switching** — switching between ML and Historique does not accumulate WebGL contexts (check DevTools > Performance > Memory — GPU contexts should not grow unboundedly).
8. **No ML data** — test a machine with no ML prediction: 3D components fall back to `healthScore=50`, `riskLevel='LOW'`. No crashes.
9. **Error fallback** — to test ErrorBoundary: temporarily throw in MachineModel's render, verify the "3D view unavailable" fallback renders at correct height.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat(3d): complete 3D motion UI — hero, 3D tab, ML mini floating model"
```

---

## Self-Review Checklist (completed before writing plan)

- **No placeholders**: All steps contain full code. No TBD, TODO, or "similar to Task N".
- **Type consistency**: `MachineModelProps` interface defined in Task 3 and imported identically in Tasks 4, 5, 6. `riskLevel` cast consistently across Hero, Viewer, and MLIntelligenceTab.
- **Spec coverage**:
  - r3f-geometry: `RoundedBox`, `cylinderGeometry`, `torusGeometry`, `ringGeometry`, `boxGeometry` ✓
  - r3f-materials: `MeshStandardMaterial` metalness/roughness, emissive health ring, `toneMapped: false` ✓
  - r3f-lighting: three-point setup, `Environment`, `AccumulativeShadows`, `SoftShadows`, `ContactShadows` ✓
  - r3f-animation: `useFrame` rotor spin + group auto-rotate; Drei `<Float>` ✓
  - r3f-shaders: Fresnel via `onBeforeCompile`, vertex `vWorldPos` varying, fragment rim injection, `uTime` uniform updated in `useFrame` ✓
  - r3f-loaders: `useEnvironment` via `<Environment preset="warehouse">` ✓
  - gsap-scrolltrigger: `ScrollTrigger.create`, `scrub: 1`, `onUpdate`, trigger = hero wrapper div ✓
  - gsap-performance: `gsap.quickTo` for camera X/Y on scroll (no tween allocation per event); `dpr={[1,1.5]}` on mini canvas ✓
- **Max 2 WebGL contexts**: Hero always visible (1 context). Only one tab content visible at a time (3D Vue tab = 1 context). Mini canvas exists only when ML tab is active. ✓
- **`frameloop="always"` on mini**: Required for Drei `<Float>` which uses `useFrame` without calling `invalidate()`. ✓
- **ErrorBoundary wraps every Canvas**: Hero, Viewer, Mini all wrapped. ✓
- **`MachineViewer3D` is default export**: Required for `React.lazy`. ✓
