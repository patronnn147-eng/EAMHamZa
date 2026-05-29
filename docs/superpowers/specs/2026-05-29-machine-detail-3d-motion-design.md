# Machine Detail Page — 3D Motion UI Design

**Date:** 2026-05-29
**Status:** Approved
**Scope:** `app/frontend/src/modules/shared/MachineDetailPage.tsx` and related components

---

## Summary

Add immersive 3D motion UI to the machine detail page using React Three Fiber (R3F) and GSAP. Three placements: a full-width hero banner above the tabs, a dedicated "3D Vue" tab with orbit controls, and a mini floating model inside the ML Intelligence card. All components share a single procedural machine mesh built from R3F primitives — no external GLTF files required.

---

## New Packages

```
@react-three/fiber
@react-three/drei
three
gsap
@gsap/react
```

---

## Architecture

### Approach

Shared model component, separate lazy Canvases. One reusable `MachineModel` R3F component consumed by three wrapper components. The 3D tab canvas is lazy-loaded so it only mounts when the tab is clicked. Maximum 2 WebGL contexts visible simultaneously.

### New Files

All under `app/frontend/src/modules/shared/machines/components/3d/`:

| File | Purpose |
|------|---------|
| `MachineModel.tsx` | Procedural R3F mesh — shared by all three views |
| `HealthShaderMaterial.tsx` | Custom Fresnel rim glow shader — health-driven color |
| `MachineHero3D.tsx` | Hero banner Canvas + GSAP ScrollTrigger camera scrub |
| `MachineViewer3D.tsx` | Full 3D tab Canvas + OrbitControls (lazy-loaded) |
| `MachineMini3D.tsx` | Mini float Canvas for ML Intelligence card |

### Modified Files

| File | Change |
|------|--------|
| `MachineDetailPage.tsx` | Add `<MachineHero3D>` between header row and tabs; add "3D Vue" as third tab with `React.lazy` |
| `MLIntelligenceTab.tsx` | First ML card becomes flex row: mini 3D canvas left, ML stats right |

---

## Component Specifications

### `MachineModel.tsx`

**Props:**
```ts
interface MachineModelProps {
  healthScore: number        // 0–100
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  autoRotate?: boolean       // default false
  rotationSpeed?: number     // default 0.4
}
```

**Geometry (all R3F primitives, no GLTF):**
- Body: `<RoundedBox args={[2, 1.4, 1]} radius={0.08} smoothness={4}>`
- Side panels: two `<Box args={[0.15, 1.0, 1.05]}>` offset left/right
- Rotor: `<Cylinder args={[0.25, 0.25, 0.3, 16]}>` on top — spins via `useFrame` (`ref.current.rotation.y += delta * rotationSpeed`)
- Belt loop: `<Torus args={[0.55, 0.06, 8, 32]}>` around mid-section
- Health ring: `<Ring args={[1.1, 1.2, 64]}>` at base — emissive color driven by `riskLevel`
- Exhaust ports: 3× `<Cylinder args={[0.06, 0.06, 0.2, 8]}>` on back face

**Materials:**
- Body + panels: `meshStandardMaterial` `metalness={0.85}` `roughness={0.15}` `color="#78909c"`
- Rotor + belt: `meshStandardMaterial` `metalness={0.9}` `roughness={0.1}` `color="#546e7a"`
- Health ring: `meshStandardMaterial` emissive driven by risk — `CRITICAL=#ef4444`, `HIGH=#f97316`, `MEDIUM=#f59e0b`, `LOW=#22c55e`. `emissiveIntensity={1.5}` `toneMapped={false}`

**All parts:** `castShadow` + `receiveShadow`

---

### `HealthShaderMaterial.tsx`

Custom shader applied to machine body as an additional rim effect via `onBeforeCompile`.

**Uniforms:** `healthScore: float`, `time: float`

**Vertex:** passes `vNormal` and `vWorldPosition` as varyings.

**Fragment (injected after `#include <output_fragment>`):**
```glsl
vec3 viewDir = normalize(cameraPosition - vWorldPosition);
float fresnel = pow(1.0 - dot(viewDir, vNormal), 3.0);
float pulse = sin(time * 2.0) * 0.5 + 0.5;  // only visible at low health
vec3 rimColor = mix(vec3(0.0, 0.83, 1.0), vec3(1.0, 0.0, 0.0), 1.0 - healthScore / 100.0);
gl_FragColor.rgb += rimColor * fresnel * (0.2 + pulse * (1.0 - healthScore / 100.0) * 0.3);
```

Updated every frame via `useFrame`: `materialRef.current.uniforms.time.value = clock.elapsedTime`

---

### `MachineHero3D.tsx`

**Props:** `machine: Machine`, `mlPrediction: MLPrediction | null`

**Canvas:** `height: 280px`, `shadows`, `camera={{ position: [0, 1.5, 5], fov: 45 }}`

**Lighting:**
- `<Environment preset="warehouse" environmentIntensity={0.8}>`
- Key: `<directionalLight position={[5, 5, 5]} intensity={1.2} castShadow shadow-mapSize={[1024, 1024]}>`
- Fill: `<directionalLight position={[-5, 3, 5]} intensity={0.4}>`
- Rim: `<directionalLight position={[0, 5, -5]} intensity={0.25}>`

**Shadows:** `<AccumulativeShadows position={[0, -0.7, 0]} scale={6} frames={40} opacity={0.6}><RandomizedLight amount={4} radius={3} position={[5, 5, -5]}/></AccumulativeShadows>`

**GSAP ScrollTrigger (via `useGSAP`):**
```ts
gsap.registerPlugin(ScrollTrigger)
const cameraRef = useRef()  // camera ref from useThree inside inner component

ScrollTrigger.create({
  trigger: wrapperRef.current,       // internal ref on MachineHero3D's own outer div
  start: 'top top',
  end: '+=200',
  scrub: 1,
  onUpdate: (self) => {
    xTo(self.progress * -0.4)        // quickTo camera rotation Y
    zTo(5 - self.progress * 1.5)     // quickTo camera Z: 5 → 3.5
  }
})
```
`gsap.quickTo` used for camera X/Z updates — no new tweens per scroll event.
Cleanup: `useGSAP` return kills all triggers automatically on unmount.

**Suspense fallback:** dark `div` at same height — no layout shift.

---

### `MachineViewer3D.tsx`

**Lazy-loaded** via `React.lazy(() => import('./MachineViewer3D'))` in `MachineDetailPage`.

**Props:** `machine: Machine`, `mlPrediction: MLPrediction | null`

**Canvas:** `height: min(500px, 60vh)`, `shadows="soft"`

**Controls:** `<OrbitControls enablePan={false} minDistance={2} maxDistance={8} autoRotate autoRotateSpeed={0.5}>`
Auto-rotate stops when user grabs — default OrbitControls behavior.

**Lighting:**
- `<Environment preset="warehouse" background backgroundBlurriness={0.6}>`
- Same three-point setup as hero
- `<SoftShadows size={25} samples={10}>`
- `<ContactShadows position={[0, -0.7, 0]} opacity={0.5} blur={2}>`

**Data overlay:** `<Html position={[1.5, 1.2, 0]} style={{ pointerEvents: 'none' }}>` — renders health score, RUL days, risk badge as HTML on top of the canvas.

---

### `MachineMini3D.tsx`

**Props:** `riskLevel: string`

**Canvas:** `width: 120px`, `height: 120px`, `frameloop="always"`, `dpr={[1, 1.5]}`

`frameloop="always"` required — Drei `<Float>` and `useFrame` rotor spin need continuous frames. The canvas is 120×120px so GPU cost is negligible.

**Scene:**
```tsx
<Float speed={1.4} rotationIntensity={0.4} floatIntensity={0.6} floatingRange={[-0.05, 0.05]}>
  <MachineModel healthScore={50} riskLevel={riskLevel} autoRotate rotationSpeed={0.3} />
</Float>
```

**Lighting:** `<ambientLight intensity={0.6}>` + `<pointLight position={[2, 2, 2]} intensity={0.8}>`

No shadows (too small to matter, saves cost).

---

## Data Flow

```
MachineDetailPage
  ├─ mlPrediction.health_score ──→ MachineHero3D ──→ MachineModel (healthScore)
  ├─ mlPrediction.risk_level   ──→ MachineHero3D ──→ MachineModel (riskLevel)
  ├─ mlPrediction.health_score ──→ MachineViewer3D ──→ MachineModel (healthScore)
  ├─ mlPrediction.risk_level   ──→ MachineViewer3D ──→ MachineModel (riskLevel)
  └─ mlPrediction.risk_level   ──→ MachineMini3D (riskLevel — decorative only)
```

When `mlPrediction` is null: components receive `healthScore={50}` and `riskLevel="LOW"` as safe defaults.

---

## Error Handling

**Per-canvas ErrorBoundary:**
```tsx
<ErrorBoundary fallback={<MachineIconFallback />}>
  <Suspense fallback={<CanvasPlaceholder height={280} />}>
    <MachineHero3D ... />
  </Suspense>
</ErrorBoundary>
```
`MachineIconFallback` — static SVG machine icon at same height. No crash, no blank space.

**Null safety:** All 3D components guard `if (!machine) return null`.

---

## Performance Constraints

| Rule | Rationale |
|------|-----------|
| `dpr={[1, 1.5]}` on MachineMini3D | Cap pixel ratio on small 120×120 canvas |
| `React.lazy` on MachineViewer3D | Bundle only downloaded on tab click |
| `gsap.quickTo` for camera | No tween allocation per scroll event |
| Max 2 simultaneous WebGL contexts | Hero always visible; only one tab content visible at a time |
| AccumulativeShadows `frames={40}` | Bake after 40 frames, stop recalculating |
| `dpr={[1, 1.5]}` on mini canvas | Cap pixel ratio for small canvas |

---

## Skills Coverage

| Skill | Where used |
|-------|-----------|
| r3f-geometry | `MachineModel` — RoundedBox, Cylinder, Torus, Ring, Box primitives |
| r3f-materials | `MachineModel` — meshStandardMaterial, metalness/roughness, emissive health ring |
| r3f-lighting | `MachineHero3D`, `MachineViewer3D` — three-point + Environment + AccumulativeShadows |
| r3f-animation | `MachineModel` — useFrame rotor spin; `MachineMini3D` — Drei Float |
| r3f-shaders | `HealthShaderMaterial` — Fresnel rim glow, onBeforeCompile, time uniform |
| r3f-loaders | `MachineViewer3D` — useEnvironment for warehouse env map |
| gsap-scrolltrigger | `MachineHero3D` — ScrollTrigger.create scrub, trigger, onUpdate |
| gsap-performance | `MachineHero3D` — quickTo camera, useGSAP cleanup; frameloop="demand" on mini |

---

## Manual Test Checklist

1. Hero 3D banner renders on page load — no blank space, no console errors
2. Scrolling past hero shifts camera smoothly (front → 3/4 view)
3. "3D Vue" tab click lazy-loads canvas — spinner shows briefly then machine appears
4. OrbitControls work in 3D tab — drag rotates, scroll zooms, auto-rotate resumes after release
5. ML mini floats in first ML Intelligence card alongside existing stats
6. Health ring color matches current `risk_level` (red for CRITICAL, green for LOW)
7. Rim glow pulses faster at CRITICAL risk
8. Tab switching does not accumulate WebGL contexts (DevTools > Performance)
9. ErrorBoundary fallback renders when WebGL is blocked (test in Firefox with `webgl.disabled=true`)
10. Page works normally when `mlPrediction` is null (machine with no ML data)
