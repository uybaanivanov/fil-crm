// Единая точка чтения флага demo-сборки. Включается через VITE_DEMO=1
// при `npm run build:demo`. В обычной сборке/dev — false.
export const DEMO = Boolean(import.meta.env.VITE_DEMO);
