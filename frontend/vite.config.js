// frontend/vite.config.js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from "path"

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // This allows us to use "@" as a shortcut to the "src" directory
      // in our import paths, which is a common and clean practice.
      "@": path.resolve(__dirname, "./src"),
    },
  },
})