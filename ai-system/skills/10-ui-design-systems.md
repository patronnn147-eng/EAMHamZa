## Application design & UI systems

This section covers every major visual design system, UI style, motion approach, and
tool for building modern web and mobile interfaces. When I ask you to build a UI, if I
mention any of these styles or tools, apply them correctly and explain the techniques
being used, where they came from, and what makes them work.

---

### Visual design languages

**Glassmorphism (Frosted Glass UI)**
Semi-transparent surfaces with a blur effect behind them, creating the illusion of
frosted glass. Gives UIs a sense of depth and layering. Key properties: `backdrop-filter:
blur(16px)`, `background: rgba(255, 255, 255, 0.15)`, a subtle border of `rgba(255,
255,255, 0.3)`, and a shadow. Works best on top of colorful, blurred backgrounds or
gradients. Overusing it (every element is glass) destroys the depth effect — reserve it
for cards and modals that float above the background.

**Neumorphism (Soft UI)**
Elements appear to be extruded from the background using two shadows — a light one in
the top-left and a dark one in the bottom-right, giving a pressed-clay feel. The
background and element must be the same color. Key properties:
`box-shadow: 8px 8px 16px #babecc, -8px -8px 16px #ffffff`. Accessibility problem:
low contrast by design — use with caution and always test with a contrast checker.
Best for dashboards and tools, not content-heavy pages.

**Brutalism**
Anti-design that deliberately uses raw HTML aesthetics: visible borders, primary colors,
heavy typography, asymmetric layouts, stark contrasts. No rounded corners, no shadows,
no gradients. Polarizing — memorable and intentional when used correctly, chaotic when
used accidentally. Suited to artistic/creative portfolios and brands that want to stand out.

**Minimalism / Flat Design**
Remove everything that is not functional. No gradients, no shadows, no decoration.
Color is used for meaning (action, warning, success), not aesthetics. Typography does
most of the visual work. Google's early Material Design and Apple's iOS 7 redefined
mainstream UI with this approach. The risk is sterility — minimalism requires excellent
typography and spacing to avoid feeling empty.

**Material Design (Google)**
Google's design system. Elevation (shadows encode the height of a surface above the
page), color themes with primary/secondary/surface roles, defined motion curves
(standard, decelerate, accelerate), and a complete component library. Material Design 3
(Material You) introduces dynamic color — the UI adapts its palette to the user's
wallpaper on Android. Implementation: `@mui/material` for React, Angular Material for
Angular.

**Cupertino Design (Apple HIG)**
Apple's Human Interface Guidelines. Clean typography (San Francisco font family),
generous whitespace, depth through blur and layering, consistent gesture patterns on
mobile. If building a Flutter app targeting iOS, use Cupertino widgets to respect
platform conventions. If building a web app that feels "Apple-like," focus on
typography, whitespace, and subtle motion.

**Claymorphism**
3D-looking components that appear rounded, soft, and inflated — like clay models.
Achieved with multiple layered box-shadows, bright pastel fills, and strong inner
highlights. Trending in playful consumer products and apps targeting younger audiences.
Heavy use slows rendering; use selectively.

**Cyberpunk / Synthwave / Neon UI**
Dark backgrounds (near-black or deep navy), neon accent colors (electric blue, hot pink,
acid green), glowing effects (`text-shadow`, `box-shadow` in bright colors), grid
overlays, CRT scan-line effects. Used for gaming, crypto, and developer tools brands.
Implementation: CSS glow effects, custom gradients, and fonts like Rajdhani or Orbitron.

**Skeuomorphism**
UI elements that look like their real-world counterparts — a notes app that looks like
lined paper, a calendar that looks like a physical calendar. Largely out of fashion in
web/mobile since flat design took over around 2013, but returning in subtle forms in
premium products (Apple Watch app icons, some game UIs). When used, it must be executed
with high fidelity or it looks dated.

**Dark Mode Design**
Not just inverting colors. True dark mode uses dark surfaces (not pure black — `#121212`
is Google's recommendation for dark surfaces because pure black causes halation on OLED
screens), maintains 4.5:1 contrast ratios on all text, reduces color saturation slightly
(saturated colors look harsh on dark backgrounds), and uses elevation with lighter
surfaces (higher elements are slightly lighter, not shadowed). Always design and test
in both light and dark modes simultaneously, not as an afterthought.

**Glassmorphic Dark (Obsidian UI)**
Dark glassmorphism: very dark, almost black backgrounds with dark-tinted frosted cards.
`background: rgba(0, 0, 0, 0.4)`, `backdrop-filter: blur(20px)`, white text, and very
subtle bright borders. Popular in developer tools, monitoring dashboards, and gaming UIs.

---

### Motion & animation design

**The principles of motion:**
Motion should be purposeful — it communicates state changes, guides attention, and
provides feedback. Bad motion is animation that plays because it looks impressive, not
because it communicates something. Every animation should answer: what does this motion
tell the user?

**Easing functions.** The speed curve of an animation determines whether it feels
natural. `linear` feels mechanical. `ease-in-out` (accelerates then decelerates) feels
physical. `cubic-bezier(0.34, 1.56, 0.64, 1)` creates a spring overshoot — the element
goes slightly past its destination then settles. Use easing functions that match the
physical metaphor: things entering the screen decelerate (ease-out); things leaving
accelerate (ease-in); things moving within the screen use ease-in-out.

**Framer Motion (React)**
The standard animation library for React. Declarative API:
`<motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}`.
`AnimatePresence` handles exit animations (when components are removed from the DOM).
`useSpring`, `useMotion`, and layout animations for physics-based and automatic layout
transitions. When using Framer Motion, explain: what the initial/animate/exit states
represent, what the transition config means (`duration`, `type: 'spring'`, `stiffness`,
`damping`).

**GSAP (GreenSock Animation Platform)**
The most powerful JavaScript animation library. Can animate any CSS property, SVG path,
canvas, or WebGL element. Timeline-based API for complex sequenced animations:
`gsap.timeline().from('.title', { y: -50, opacity: 0 }).to('.button', { scale: 1.1 })`.
ScrollTrigger plugin animates elements as the user scrolls. MorphSVG plugin morphs one
SVG shape into another. Use GSAP when Framer Motion is not powerful enough for the
required animation complexity.

**CSS Animations and Transitions**
For simple, performant animations, CSS is always the first choice — it runs on the
compositor thread and does not block JavaScript. `transition: transform 200ms ease-out`
for hover effects. `@keyframes` for multi-step animations. Always animate `transform`
and `opacity` — they are GPU-accelerated. Never animate `width`, `height`, `top`,
`left` — they trigger layout recalculation (called "reflow") on every frame, which is
slow.

**React Spring**
Physics-based animation library for React. Instead of specifying duration and easing,
you specify mass, tension, and friction — like defining a real spring. The result
feels organic rather than mechanical. Good for interactive animations that respond to
user gestures.

**Lottie**
Renders Adobe After Effects animations as JSON in the browser or native mobile apps.
The workflow: a designer creates an animation in After Effects, exports it with the
Bodymovin plugin as a `.json` file, and the Lottie player renders it at any size with
perfect fidelity. Use for complex logo animations, loading states, empty state
illustrations, and success/error micro-animations. Lighter than a video file.
Libraries: `lottie-web` for the browser, `lottie-react`, `rive` (a Lottie alternative
with interactive state machines).

**Rive**
A next-generation alternative to Lottie. Rive animations can have interactive state
machines — they respond to user input (hover, click, scroll position) without JavaScript.
A button animation that plays a different animation when hovered vs clicked vs pressed
is trivial in Rive. Rive files are smaller than Lottie and render with better
performance.

---

### 3D and immersive UI

**Three.js**
The foundational WebGL library. WebGL is a browser API for rendering 3D graphics using
the GPU — extremely fast but very low-level. Three.js abstracts WebGL into scenes,
cameras, geometries, materials, and lights. Used for 3D product viewers, data
visualizations, interactive backgrounds, and WebGL games. Key concepts to explain every
time: Scene (the 3D world), Camera (the viewpoint — PerspectiveCamera for realistic
depth), Renderer (draws the scene to a canvas), Mesh (a 3D object — geometry + material),
Light (illuminates the scene), and the animation loop (`renderer.setAnimationLoop`).

**React Three Fiber (R3F)**
Three.js as a React component tree. Instead of imperative Three.js code, you write JSX:
`<Canvas><ambientLight /><mesh><boxGeometry /><meshStandardMaterial /></mesh></Canvas>`.
Declarative, composable, and integrates naturally with React state and hooks.
`@react-three/drei` is the companion library of ready-made helpers — orbit controls,
environment maps, text, HTML embedded in 3D space, and much more.
`@react-three/postprocessing` adds post-processing effects (bloom, depth of field,
chromatic aberration). Use R3F for any 3D content in a React application.

**Spline**
A browser-based 3D design tool that exports interactive 3D scenes directly to a React
component or a `<script>` tag. Designers build in Spline; developers embed the result.
No Three.js knowledge required. Good for landing page hero sections, product
presentations, and decorative 3D elements. The trade-off: less control than writing
Three.js directly, and the Spline viewer adds JavaScript bundle weight.

**WebGL Shaders (GLSL)**
GLSL (OpenGL Shading Language) is the language that runs directly on the GPU for custom
visual effects. Vertex shaders control the position of every point in a 3D mesh. Fragment
shaders control the color of every pixel. Together they enable effects impossible in CSS:
procedural noise, particle systems, fluid simulations, ray marching. Very advanced;
use with Three.js's `ShaderMaterial`. Libraries like `glsl-noise` provide reusable
shader functions.

**Particles and procedural effects**
`@tsparticles/react` and `three-mesh-bvh` for particle systems. Particle systems
simulate thousands of individual points moving according to rules — snow, confetti,
galaxy backgrounds, energy fields. `simplex-noise` and `perlin-noise` generate
organic-looking random patterns used in terrain generation, fluid textures, and
animated backgrounds. Explain what noise functions are (smooth, correlated randomness
— unlike `Math.random()` which is chaotic) every time they appear.

**CSS 3D transforms**
Before reaching for Three.js, consider what is achievable with CSS alone. `transform:
perspective(1000px) rotateY(30deg)` creates a 3D card tilt. `transform-style:
preserve-3d` on a container lets children exist in true 3D space. CSS 3D is GPU-
accelerated and requires no JavaScript library. Good for card flip animations, perspective
scroll effects, and carousel tilt effects.

---

### Design systems and component libraries

A design system is a collection of reusable components, standards, and documentation
that ensures visual and behavioral consistency across an entire product. Building from
a mature design system saves months of work and avoids inconsistency bugs.

**Tailwind CSS**
A utility-first CSS framework. Instead of writing custom CSS classes, you compose
utilities directly in HTML: `<button class="px-4 py-2 rounded-lg bg-blue-600 text-white
hover:bg-blue-700">`. The final CSS file contains only the utilities actually used —
usually very small. Tailwind UI is the premium component library built on it. Use
Tailwind for rapid development; explain every class used the first time it appears in
a project.

**shadcn/ui**
Not a traditional component library (you do not install it as a dependency). Instead,
you copy components into your project and own them completely. Built on Radix UI
primitives (accessible, unstyled behaviors — dialogs, dropdowns, tooltips, etc.) and
styled with Tailwind. The components are fully customizable because you own the code.
This is the current best practice for React component libraries.

**Radix UI**
Unstyled, accessible primitives. Dialog, Dropdown, Tooltip, Select, Checkbox — every
complex interactive component, built correctly (keyboard navigation, screen reader
support, focus management) but with zero visual styling. Add your own CSS. Use Radix
when you want full visual control but do not want to rebuild accessibility from scratch.

**Headless UI**
Similar to Radix, from the Tailwind team. Accessible, unstyled components designed to
be used with Tailwind CSS.

**Chakra UI / Mantine**
Styled component libraries for React. Faster to start with than shadcn/ui but less
flexible. Good for internal tools, admin panels, and projects where design
differentiation is not a priority.

**MUI (Material UI)**
React implementation of Google's Material Design. Large, comprehensive, and battle-tested.
The default choice for enterprise React applications. Highly customizable via the
theme system.

**Ant Design**
Comprehensive React component library with a strong enterprise aesthetic. Very popular
for admin dashboards and data-heavy internal tools. `antd` is the React package.

**DaisyUI**
Tailwind plugin that adds semantic component classes. `btn`, `card`, `modal` as CSS
classes, styled in multiple themes. Good for projects that want Tailwind's utility
system but with higher-level component abstractions.

---

### Typography systems

Typography is the single most impactful design decision after color. Every professional
UI should have a deliberate type system.

- **Type scale:** A harmonious set of font sizes derived from a ratio. The major third
  (1.25×) and perfect fourth (1.333×) are common ratios. Example: 12, 14, 16, 20, 24,
  32, 40, 48px. Never pick font sizes arbitrarily.
- **Font pairing:** Display/heading font for titles; text font for body. Common pairs:
  Inter (body) + Syne or Cabinet Grotesk (display); Playfair Display (display) +
  Source Sans (body). Variable fonts (one file, infinite weights and styles) reduce
  page weight.
- **Line height:** Body text: 1.5–1.7× the font size. Headings: 1.1–1.3×. Too tight
  makes text hard to scan; too loose breaks the visual connection between lines.
- **Font loading:** Use `font-display: swap` to prevent invisible text during font load.
  Self-host fonts (use `next/font` in Next.js) to avoid external requests and layout
  shift.
- **Key font sources:** Google Fonts (free), Fontshare (free, high quality), Fonts In
  Use (inspiration), Klim Type Foundry, Grilli Type, and Pangram Pangram (premium).

---

### Color systems

**The 60-30-10 rule.** 60% of the UI uses the dominant color (usually a neutral
background). 30% uses the secondary color (cards, navigation). 10% uses the accent
color (calls to action, highlights). More than three intentional colors creates visual
noise.

**Color tokens.** Do not use raw hex values in components. Define semantic tokens:
`--color-surface-primary`, `--color-text-primary`, `--color-action-default`. This is
what makes dark mode possible without rewriting every component — you change the token
values, not every component that uses them.

**Accessible contrast.** WCAG AA standard requires 4.5:1 contrast ratio for normal text,
3:1 for large text and UI components. WCAG AAA requires 7:1. Use the browser's DevTools
contrast checker or tools like Colour Contrast Analyser. Low contrast is the most
common accessibility failure in professional UIs.

**Tools:** Figma (design and token management), Coolors (palette generation), Realtime
Colors (live preview of palette on a real UI), Radix UI Colors (pre-built accessible
color scales for light and dark mode), Tailwind's color palette.

---

### Responsive and adaptive design

**Mobile-first.** Write the base styles for the smallest screen, then add complexity
for larger screens using min-width breakpoints. This is the correct approach — CSS
works by overriding, and overriding simple styles with complex ones is cleaner than
the reverse. Tailwind's default breakpoints: `sm` (640px), `md` (768px), `lg` (1024px),
`xl` (1280px), `2xl` (1536px).

**Container queries.** The next evolution beyond media queries. Instead of the component
adapting to the viewport width, it adapts to the width of its container. `@container
(min-width: 400px) { ... }`. This makes components truly portable — the same component
renders differently inside a narrow sidebar vs a wide main content area.

**Fluid typography and spacing.** Use `clamp(min, preferred, max)` for font sizes and
spacing that scale smoothly with viewport width:
`font-size: clamp(1rem, 2.5vw, 1.5rem)`. No breakpoint jumps — continuous scaling.

---

### Mobile app design specifics (Flutter / React Native)

**Platform conventions.** iOS uses Cupertino conventions: navigation bars, tab bars at
the bottom, swipe-back gesture. Android uses Material conventions: app bars, navigation
drawers or bottom nav, system back button. Users expect their platform's conventions —
violating them makes an app feel wrong even if users cannot articulate why.

**Safe areas.** On modern phones, the screen has a notch, Dynamic Island, or rounded
corners that overlap content. Always respect safe area insets:
`SafeArea` widget in Flutter, `SafeAreaView` in React Native.

**Touch target sizes.** The minimum touch target for a tappable element is 44×44 points
(Apple HIG) or 48×48dp (Material Design). Smaller targets cause frequent mis-taps.
This is a common beginner mistake — designing tap targets that look right but are too
small to use comfortably.

**Gesture design.** Swipe, long press, pinch, double tap — each carries an expectation.
Swipe right on a list item to reveal actions is a known iOS pattern. Long press to enter
selection mode is familiar from Android. Do not invent novel gestures without a
discoverability mechanism; users will not discover them accidentally.

---

