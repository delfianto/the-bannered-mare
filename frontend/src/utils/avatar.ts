// Brand amber for the generated initials-placeholder avatar (was hand-copied,
// with this hex, across ~10 components).
const FALLBACK_BG = "C9922E";

/**
 * URL for a name-initials placeholder avatar, used as the last resort when a
 * character/persona has no stored image. `size` is the requested pixel size
 * (callers pick per surface — 80 for list rows, 400+ for cards/detail).
 */
export function fallbackAvatarUrl(name: string, size = 200): string {
  return `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=${FALLBACK_BG}&color=fff&size=${size}`;
}
