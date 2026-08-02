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
          DEFAULT: 'rgb(var(--app-bg-rgb) / <alpha-value>)',
          card: 'rgb(var(--app-card-rgb) / <alpha-value>)',
          input: 'rgb(var(--app-input-rgb) / <alpha-value>)',
        },
        gold: {
          DEFAULT: 'rgb(var(--app-accent-rgb) / <alpha-value>)',
          title: 'rgb(var(--app-accent-rgb) / <alpha-value>)',
          price: 'rgb(var(--app-accent-hover-rgb) / <alpha-value>)',
          muted: 'rgb(var(--app-accent-dim-rgb) / <alpha-value>)',
        },
        border: {
          main: 'rgb(var(--app-border-rgb) / <alpha-value>)',
          inner: 'rgb(var(--app-border-light-rgb) / <alpha-value>)',
        },
        success: 'rgb(var(--c-success-rgb) / <alpha-value>)',
        danger: 'rgb(var(--c-danger-rgb) / <alpha-value>)',
        warning: 'rgb(var(--c-warning-rgb) / <alpha-value>)',
        info: 'rgb(var(--c-info-rgb) / <alpha-value>)',
      },
      fontFamily: {
        serif: ['Georgia', 'serif'],
        sans: ['Segoe UI', 'Microsoft YaHei', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
