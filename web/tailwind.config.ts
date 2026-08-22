import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        base: {
          950: '#08090b',
          900: '#0c0e11',
          850: '#111318',
          800: '#161920',
          700: '#1f232c',
          600: '#2a2f3a',
          500: '#3a4150',
        },
        amber: {
          400: '#f5a623',
          500: '#e8930f',
          600: '#c77a08',
        },
        cyan: {
          300: '#7dd3e8',
          400: '#4fc3dc',
          500: '#2ea8c4',
        },
        ok: '#3ecf6e',
        caution: '#e8c547',
        risk: '#e0503a',
        unknown: '#5a6070',
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', '"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        panel: '0 0 0 1px rgba(255,255,255,0.04), 0 8px 24px -8px rgba(0,0,0,0.6)',
      },
    },
  },
  plugins: [],
}

export default config
