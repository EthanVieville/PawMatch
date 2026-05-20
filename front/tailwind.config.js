module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        olive: {
          50:  '#f4f7f0',
          100: '#e5eede',
          200: '#ccdcbf',
          300: '#a8c295',
          400: '#81a568',
          500: '#6B7A58',
          600: '#536044',
          700: '#3D4A2E',
          800: '#2d3823',
          900: '#1e2616',
        },
        sand: {
          50:  '#FAF6EE',
          100: '#F0EAD6',
          200: '#E2D5BB',
          300: '#C8B99A',
          400: '#B09A7A',
          500: '#9A845F',
        },
        rust: {
          400: '#CC6535',
          500: '#B5501A',
          600: '#9A4218',
        },
      },
      fontFamily: {
        display: ['var(--font-bebas)', 'Impact', 'sans-serif'],
        body:    ['var(--font-barlow)', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
