/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          DEFAULT: 'var(--app-bg)',
          card: 'var(--app-card)',
          input: 'var(--app-input)',
        },
        gold: {
          DEFAULT: 'var(--app-accent)',
          title: 'var(--app-accent)',
          price: 'var(--app-accent-hover)',
          muted: 'var(--app-accent-dim)',
        },
        border: {
          main: 'var(--app-border)',
          inner: 'var(--app-border-light)',
        },
      },
      fontFamily: {
        serif: ['Georgia', 'serif'],
        sans: ['Segoe UI', 'Microsoft YaHei', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
