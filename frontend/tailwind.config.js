/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        lumen: {
          primary:        '#3B5BDB',
          'primary-hover':'#324CC4',
          'primary-soft': '#EEF2FF',
          'primary-ring': '#C7D2FE',
          bg:             '#F8FAFC',
          surface:        '#FFFFFF',
          'surface-2':    '#F1F5F9',
          border:         '#E2E8F0',
          'border-strong':'#CBD5E1',
          text:           '#0F172A',
          body:           '#334155',
          muted:          '#64748B',
          faint:          '#94A3B8',
          up:             '#16A34A',
          'up-soft':      '#DCFCE7',
          down:           '#DC2626',
          'down-soft':    '#FEE2E2',
          live:           '#16A34A',
          paused:         '#D97706',
          error:          '#DC2626',
        },
      },
      fontFamily: {
        display: ['Sohne', 'Inter', 'sans-serif'],
        body:    ['Inter', 'sans-serif'],
        mono:    ['JetBrains Mono', 'SF Mono', 'monospace'],
      },
      borderRadius: {
        lumen:    '10px',
        'lumen-sm': '6px',
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
}

