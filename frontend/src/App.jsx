import React, { useState, useEffect, useRef } from 'react';
import { Bot, BookOpen, GitBranch, Cpu, Activity, Code2 } from 'lucide-react';

import TaskInput from './components/TaskInput';
import PlanViewer from './components/PlanViewer';
import LiveTerminal from './components/LiveTerminal';
import ReviewCard from './components/ReviewCard';
import DiffViewer from './components/DiffViewer';

export default function App() {
  const [plan, setPlan] = useState(null);
  const [logs, setLogs] = useState([]);
  const [reviewReport, setReviewReport] = useState(null);
  const [gitDiff, setGitDiff] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [taskId, setTaskId] = useState(null);
  const wsRef = useRef(null);

  const connectWebSocket = (id) => {
    if (wsRef.current) wsRef.current.close();

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Use window.location.host or default to 8000 in dev
    const host = window.location.port === '5173' ? 'localhost:8000' : window.location.host;
    const wsUrl = `${protocol}//${host}/api/v1/tasks/${id}/stream`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => setIsConnected(false);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setLogs((prev) => [...prev, data]);
      } catch (err) {
        console.error('Failed to parse WebSocket message', err);
      }
    };
  };

  const handlePlan = async ({ repoPath, title, desc }) => {
    setIsLoading(true);
    setLogs((prev) => [
      ...prev,
      {
        event_type: 'THINKING',
        message: `Analyzing codebase and formulating plan for: "${title}"...`,
        timestamp: new Date().toISOString(),
      },
    ]);

    try {
      const res = await fetch('/api/v1/issues/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_path: repoPath,
          issue_title: title,
          issue_description: desc || title,
        }),
      });

      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setPlan(data);
      setLogs((prev) => [
        ...prev,
        {
          event_type: 'COMPLETE',
          message: `Plan formulated successfully with ${data.steps.length} sequential steps.`,
          timestamp: new Date().toISOString(),
        },
      ]);
    } catch (err) {
      setLogs((prev) => [
        ...prev,
        {
          event_type: 'ERROR',
          message: `Plan generation failed: ${err.message}`,
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRun = async ({ repoPath, title, desc }) => {
    setIsLoading(true);
    setPlan(null);
    setReviewReport(null);
    setGitDiff(null);

    setLogs([
      {
        event_type: 'SYSTEM',
        message: `Initializing autonomous agent on task: "${title}"`,
        timestamp: new Date().toISOString(),
      },
    ]);

    try {
      const res = await fetch('/api/v1/tasks/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_path: repoPath,
          issue_title: title,
          issue_description: desc || title,
          auto_approve_plan: true,
        }),
      });

      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();

      setTaskId(data.task_id);
      connectWebSocket(data.task_id);

      setPlan(data.plan);
      setReviewReport(data.review_report);
      setGitDiff(data.git_diff);
    } catch (err) {
      setLogs((prev) => [
        ...prev,
        {
          event_type: 'ERROR',
          message: `Agent execution error: ${err.message}`,
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleApprove = async (planId) => {
    setIsLoading(true);
    try {
      const res = await fetch(`/api/v1/issues/plans/${planId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'APPROVED' }),
      });
      if (!res.ok) throw new Error(await res.text());
      const updated = await res.json();
      setPlan(updated);
    } catch (err) {
      alert(`Approval failed: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#030712] text-slate-100 flex flex-col font-sans">
      {/* Top Navbar */}
      <header className="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur sticky top-0 z-50 px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20 text-white">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-300 via-purple-300 to-pink-300">
              AI Software Engineering Agent
            </h1>
            <p className="text-[11px] text-slate-400">Autonomous AST Intelligence, Self-Repair & Code Review</p>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 text-xs text-slate-400 bg-slate-950 px-3 py-1.5 rounded-full border border-slate-800">
            <Activity className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
            <span className="text-[11px]">Core Engine Active</span>
          </div>

          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="flex items-center text-xs text-slate-400 hover:text-indigo-400 transition"
          >
            <BookOpen className="w-3.5 h-3.5 mr-1" />
            <span>API Docs</span>
          </a>

          <a
            href="https://github.com/UndelaNandini/AI-Software-Engineering-Agent"
            target="_blank"
            rel="noreferrer"
            className="flex items-center text-xs text-slate-400 hover:text-indigo-400 transition"
          >
            <GitBranch className="w-3.5 h-3.5 mr-1" />
            <span>GitHub</span>
          </a>

        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 max-w-7xl mx-auto w-full">
        {/* Left Column (5 Cols) */}
        <div className="lg:col-span-5 space-y-6">
          <TaskInput onPlan={handlePlan} onRun={handleRun} isLoading={isLoading} />
          {plan && <PlanViewer plan={plan} onApprove={handleApprove} isExecuting={isLoading} />}
          {reviewReport && <ReviewCard report={reviewReport} />}
        </div>

        {/* Right Column (7 Cols) */}
        <div className="lg:col-span-7 space-y-6">
          <LiveTerminal
            logs={logs}
            isConnected={isConnected}
            onClear={() => setLogs([])}
          />
          {gitDiff && <DiffViewer diff={gitDiff} />}
        </div>
      </main>
    </div>
  );
}
