import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The dashboard runs at http://localhost:5173 and calls the FastAPI backend at
// http://localhost:8000 (see src/api.ts and .env). The backend's CORS settings
// allow exactly this origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true, // stay on the origin the backend allows
    open: true, // `npm run dev` opens the desk in the browser
  },
})
