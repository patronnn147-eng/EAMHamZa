/**
 * Global scroll indicator.
 *
 * Tags any element that is being scrolled by the user with `.is-scrolling`,
 * then removes the class ~900ms after the last scroll event on that element.
 *
 * Only USER-INITIATED scrolls count. Programmatic scrolls — route changes,
 * `scrollIntoView`, framer-motion layout animations, focus changes, etc. —
 * are ignored, so the scrollbar never flashes on its own.
 *
 * Paired with the CSS rules in `index.css`, this gives the whole app
 * iOS-style scrollbars: invisible at rest, thin thumb visible only while
 * the user is actively scrolling.
 *
 * Imported once from `main.tsx` for its side effects.
 */

const HIDE_DELAY_MS = 900;
const INTENT_WINDOW_MS = 250;
const TIMER_KEY = '__scrollIndicatorTimer';

type TimerHolder = { [TIMER_KEY]?: number };

let lastUserIntentAt = 0;

function markUserIntent() {
  lastUserIntentAt = performance.now();
}

function hasRecentUserIntent(): boolean {
  return performance.now() - lastUserIntentAt < INTENT_WINDOW_MS;
}

function markScrolling(target: EventTarget | null) {
  let el: Element | null = null;
  if (target instanceof Element) {
    el = target;
  } else if (target === document || target === globalThis) {
    el = document.documentElement;
  }
  if (!el) return;

  el.classList.add('is-scrolling');

  const holder = el as unknown as TimerHolder;
  if (holder[TIMER_KEY] !== undefined) {
    globalThis.clearTimeout(holder[TIMER_KEY]);
  }
  holder[TIMER_KEY] = globalThis.setTimeout(() => {
    el.classList.remove('is-scrolling');
    holder[TIMER_KEY] = undefined;
  }, HIDE_DELAY_MS);
}

// --- User intent detection (only these events count as "the user is scrolling") ---
const SCROLL_KEYS = new Set([
  'ArrowUp',
  'ArrowDown',
  'ArrowLeft',
  'ArrowRight',
  'PageUp',
  'PageDown',
  'Home',
  'End',
  'Space',
  ' ',
]);

document.addEventListener('wheel', markUserIntent, { capture: true, passive: true });
document.addEventListener('touchmove', markUserIntent, { capture: true, passive: true });
document.addEventListener('touchstart', markUserIntent, { capture: true, passive: true });
document.addEventListener(
  'keydown',
  (e) => {
    if (SCROLL_KEYS.has(e.key)) markUserIntent();
  },
  { capture: true }
);
document.addEventListener('pointerdown', (e) => {
  // Dragging a scrollbar thumb = user intent.
  if (e.pointerType === 'mouse') markUserIntent();
}, { capture: true });

// --- Scroll handler: only tags elements when there was recent user intent ---
// While a user-initiated scroll is ongoing (momentum / continuous wheel),
// refresh the intent window so the indicator stays visible through the end.
document.addEventListener(
  'scroll',
  (event) => {
    if (!hasRecentUserIntent()) return;
    markUserIntent();
    markScrolling(event.target);
  },
  { capture: true, passive: true }
);
