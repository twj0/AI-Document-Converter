// frontend/src/App.jsx

import React from 'react';

// A simple component for the page header
function Header() {
  return (
    <header className="bg-slate-800/50 shadow-md">
      <div className="container mx-auto px-4 py-3">
        <h1 className="text-2xl font-bold text-slate-100">
          <span className="text-sky-400">AI</span> Document Converter Pro
        </h1>
        <p className="text-sm text-slate-400">
          Powered by FastAPI, Celery, and Modern AI
        </p>
      </div>
    </header>
  );
}

// The main App component
function App() {
  return (
    <div className="min-h-screen w-full bg-slate-900 font-sans">
      <Header />
      <main className="container mx-auto p-4 md:p-8">
        <div className="grid grid-cols-1 gap-8">
          
          {/* Section 1: File Uploader */}
          <div className="bg-slate-800/50 rounded-lg p-6 shadow-lg">
            <h2 className="text-xl font-semibold mb-4 text-slate-200">
              1. Upload Your Files
            </h2>
            {/* We will replace this placeholder with our FilePond component */}
            <div className="h-48 w-full bg-slate-700/50 rounded-md flex items-center justify-center">
              <p className="text-slate-400">File Uploader Component will go here.</p>
            </div>
          </div>

          {/* Section 2: Task Progress */}
          <div className="bg-slate-800/50 rounded-lg p-6 shadow-lg">
            <h2 className="text-xl font-semibold mb-4 text-slate-200">
              2. Conversion Progress
            </h2>
            {/* We will replace this placeholder with our TaskList component */}
            <div className="h-64 w-full bg-slate-700/50 rounded-md flex items-center justify-center">
              <p className="text-slate-400">Task List Component will go here.</p>
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}

export default App;