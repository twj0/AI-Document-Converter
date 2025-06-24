// frontend/src/App.tsx (Final Functional Version)
import React, { useState, useEffect, useCallback } from 'react';
import apiClient from './api/apiClient';
import FileUploader from './components/FileUploader';
import { Toaster, toast } from 'sonner';
import { Download, AlertCircle, RefreshCw } from 'lucide-react';

// --- 类型定义 ---
interface TaskResult {
  output_file_url?: string;
  message?: string;
  warnings?: string[];
  error_message?: string;
}

interface Task {
  id: string;
  status: 'pending' | 'in_progress' | 'success' | 'failed';
  result?: TaskResult;
}

// --- 子组件 ---

function Header() {
  return (
    <header className="bg-slate-800/50 shadow-md backdrop-blur-sm sticky top-0 z-10">
      <div className="container mx-auto px-4 py-3">
        <h1 className="text-2xl font-bold text-slate-100">
          <span className="text-sky-400">AI</span> Document Converter Pro
        </h1>
        <p className="text-sm text-slate-400">Powered by FastAPI, Celery, and Modern AI</p>
      </div>
    </header>
  );
}

function TaskItem({ task }: { task: Task }) {
  const getStatusInfo = (status: Task['status']) => {
    switch (status) {
      case 'success':
        return { icon: <Download size={16} />, classes: 'bg-green-500/20 text-green-400' };
      case 'in_progress':
        return { icon: <RefreshCw size={16} className="animate-spin" />, classes: 'bg-sky-500/20 text-sky-400' };
      case 'failed':
        return { icon: <AlertCircle size={16} />, classes: 'bg-red-500/20 text-red-400' };
      default:
        return { icon: <RefreshCw size={16} className="animate-spin" />, classes: 'bg-slate-600/20 text-slate-400' };
    }
  };

  const { icon, classes } = getStatusInfo(task.status);

  return (
    <div className="flex items-center justify-between p-3 bg-slate-700/50 rounded-md transition-all duration-300">
      <div className="flex flex-col">
        <span className="font-mono text-xs text-slate-400 break-all">{task.id}</span>
        {task.status === 'failed' && task.result?.error_message && (
          <p className="text-xs text-red-400 mt-1">{task.result.error_message}</p>
        )}
      </div>
      <div className="flex items-center gap-4 flex-shrink-0 ml-4">
        {task.status === 'success' && task.result?.output_file_url && (
          <a
            href={`${apiClient.defaults.baseURL}${task.result.output_file_url}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-sm text-indigo-400 hover:underline"
          >
            <Download size={14} /> Download
          </a>
        )}
        <span className={`flex items-center gap-2 px-3 py-1 text-xs font-semibold rounded-full ${classes}`}>
          {icon} {task.status}
        </span>
      </div>
    </div>
  );
}

// --- 主应用组件 ---

function App() {
  const [tasks, setTasks] = useState<Task[]>([]);

  const handleUploadSuccess = (newTask: { id: string }) => {
    toast.success(`Task accepted: ${newTask.id}`);
    setTasks(prevTasks => [{ id: newTask.id, status: 'pending' }, ...prevTasks]);
  };

  const pollTasks = useCallback(async () => {
    if (tasks.length === 0) return;
    const tasksToPoll = tasks.filter(t => t.status === 'pending' || t.status === 'in_progress');
    if (tasksToPoll.length === 0) return;

    const updatedTasks = await Promise.all(
      tasks.map(async (task) => {
        if (task.status === 'pending' || task.status === 'in_progress') {
          try {
            const response = await apiClient.get<Task>(`/api/v1/tasks/status/${task.id}`);
            if(response.data.status !== task.status) {
              if(response.data.status === 'success') toast.success(`Task ${task.id} finished!`);
              if(response.data.status === 'failed') toast.error(`Task ${task.id} failed.`);
            }
            return response.data;
          } catch (error) {
            console.error(`Polling failed for task ${task.id}`, error);
            return { ...task, status: 'failed', result: { error_message: 'Polling failed' } };
          }
        }
        return task;
      })
    );
    setTasks(updatedTasks);
  }, [tasks]);

  useEffect(() => {
    const intervalId = setInterval(pollTasks, 3000);
    return () => clearInterval(intervalId);
  }, [pollTasks]);

  return (
    <div className="min-h-screen w-full bg-slate-900 font-sans">
      <Toaster richColors position="top-right" />
      <Header />
      <main className="container mx-auto p-4 md:p-8">
        <div className="grid grid-cols-1 gap-8">
          <div className="bg-slate-800/50 rounded-lg p-6 shadow-lg">
            <h2 className="text-xl font-semibold mb-4 text-slate-200">1. Upload Your Files</h2>
            <FileUploader onUploadSuccess={handleUploadSuccess} />
          </div>
          <div className="bg-slate-800/50 rounded-lg p-6 shadow-lg">
            <h2 className="text-xl font-semibold mb-4 text-slate-200">2. Conversion Progress</h2>
            <div className="space-y-3 max-h-96 overflow-y-auto pr-2">
              {tasks.length > 0 ? (
                tasks.map(task => <TaskItem key={task.id} task={task} />)
              ) : (
                <div className="text-center py-10 text-slate-500">
                  <p>No tasks yet. Upload a file to get started!</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;