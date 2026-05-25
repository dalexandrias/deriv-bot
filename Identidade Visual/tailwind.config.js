/** @type {import('tailwindcss').Config} */
// LUMEN — Tailwind config
// Cole o conteúdo de `theme.extend` no seu tailwind.config.js
// (ou use como base, se for um projeto novo).

module.exports = {
  content: ['./src/**/*.{js,jsx,ts,tsx,html}'],
  theme: {
    extend: {
      colors: {
        lumen: {
          // brand / neutral primary
          primary:      '#3B5BDB',
          'primary-hover': '#324CC4',
          'primary-soft':  '#EEF2FF',
          'primary-ring':  '#C7D2FE',
          // surfaces
          bg:          '#F8FAFC',
          surface:     '#FFFFFF',
          'surface-2': '#F1F5F9',
          border:      '#E2E8F0',
          'border-strong': '#CBD5E1',
          // text
          text:       '#0F172A',
          body:       '#334155',
          muted:      '#64748B',
          faint:      '#94A3B8',
          // market semantics
          up:        '#16A34A',
          'up-soft': '#DCFCE7',
          down:      '#DC2626',
          'down-soft': '#FEE2E2',
          // bot status
          live:    '#16A34A',
          paused:  '#D97706',
          error:   '#DC2626',
        },
      },
      fontFamily: {
        display: ['Sohne', 'Inter', 'sans-serif'],
        body:    ['Inter', 'sans-serif'],
        mono:    ['JetBrains Mono', 'SF Mono', 'monospace'],
      },
      borderRadius: {
        lumen:    '10px',
        'lumen-lg': '16px',
      },
      boxShadow: {
        'lumen-sm': '0 1px 2px rgba(15, 23, 42, 0.04)',
        'lumen':    '0 1px 3px rgba(15, 23, 42, 0.06), 0 1px 2px rgba(15, 23, 42, 0.04)',
        'lumen-lg': '0 10px 30px rgba(15, 23, 42, 0.08)',
      },
    },
  },
  plugins: [],
};
