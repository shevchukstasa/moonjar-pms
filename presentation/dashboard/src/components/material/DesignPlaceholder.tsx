/**
 * Warm stone-like placeholder shown when a design has no photo.
 * Brand DNA: lava stone, earth tones, craftsmanship. Never corporate/sterile.
 *
 * Palette rotates by design code hash so different designs are visually
 * distinct even without photos. Subtle grain pattern adds hand-crafted feel.
 */

const PALETTES = [
  // Terracotta / rust
  ['#8b4513', '#a0522d', '#cd853f'],
  // Volcanic / charcoal
  ['#1f1f1f', '#3d2817', '#6b4423'],
  // Golden sand
  ['#8b6914', '#b8860b', '#daa520'],
  // Deep clay
  ['#5c3317', '#8b4726', '#b56b3a'],
  // Moss stone
  ['#3d4a1f', '#5a6b2f', '#8b9543'],
  // Ash grey
  ['#2f2f2f', '#555555', '#7d7d7d'],
];

function hashCode(str: string): number {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = ((h << 5) - h + str.charCodeAt(i)) | 0;
  return Math.abs(h);
}

interface Props {
  code: string;
  name: string;
  size?: 'sm' | 'md' | 'lg';
}

export function DesignPlaceholder({ code, name, size = 'md' }: Props) {
  const palette = PALETTES[hashCode(code) % PALETTES.length];
  const [c1, c2, c3] = palette;

  const sizeClass =
    size === 'sm' ? 'text-2xl' : size === 'lg' ? 'text-5xl' : 'text-4xl';

  // Use first character of name as the large glyph
  const glyph = (name?.trim()?.[0] || '◆').toUpperCase();

  return (
    <div
      className="relative w-full h-full overflow-hidden flex items-center justify-center"
      style={{
        background: `radial-gradient(ellipse at 30% 20%, ${c3} 0%, ${c2} 45%, ${c1} 100%)`,
      }}
    >
      {/* Grain overlay for hand-crafted texture */}
      <div
        className="absolute inset-0 opacity-30 mix-blend-overlay"
        style={{
          backgroundImage:
            'radial-gradient(circle at 20% 30%, rgba(255,255,255,0.15) 0%, transparent 40%), ' +
            'radial-gradient(circle at 70% 70%, rgba(0,0,0,0.2) 0%, transparent 50%)',
        }}
      />
      {/* Noise pattern */}
      <svg className="absolute inset-0 w-full h-full opacity-15" xmlns="http://www.w3.org/2000/svg">
        <filter id={`noise-${code}`}>
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" />
        </filter>
        <rect width="100%" height="100%" filter={`url(#noise-${code})`} />
      </svg>
      {/* Glyph */}
      <span
        className={`relative ${sizeClass} font-serif italic text-white/70 select-none tracking-tight`}
        style={{ textShadow: '0 2px 8px rgba(0,0,0,0.4)' }}
      >
        {glyph}
      </span>
    </div>
  );
}
