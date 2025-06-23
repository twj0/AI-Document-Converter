// frontend/src/main.jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
// We will create App.jsx in the next step
import App from './App.jsx' 
// This imports the CSS file we just created
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)