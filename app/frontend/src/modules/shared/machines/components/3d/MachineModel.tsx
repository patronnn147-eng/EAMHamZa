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
