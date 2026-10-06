import React, { useState } from 'react';
import { Play, ListChecks, Loader2, Sparkles, FolderGit2 } from 'lucide-react';

export default function TaskInput({ onPlan, onRun, isLoading }) {
  const [repoPath, setRepoPath] = useState('.');
  const [title, setTitle] = useState('');
  const [desc, setDesc] = useState('');

  const handlePlan = (e) => {
    e.preventDefault();
    if (!title.trim()) return;
    onPlan({ repoPath, title, desc });
  };

  const handleRun = (e) => {
    e.preventDefault();
    if (!title.trim()) return;
    onRun({ repoPath, title, desc });
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur">
      <div className="flex items-center space-x-2.5 mb-5">
        <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
          <FolderGit2 className="w-4 h-4" />
        </div>
        <div>
          <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
            Issue & Workspace Setup
          </h2>
          <p className="text-xs text-slate-400">Target codebase path and task requirements</p>
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">
            Target Repository Directory
          </label>
          <input
            type="text"
            value={repoPath}
            onChange={(e) => setRepoPath(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition"
            placeholder="e.g. . or /path/to/repo"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">
            GitHub Issue / Feature Title <span className="text-rose-400">*</span>
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition"
            placeholder="e.g. Add pagination query limits to get_users endpoint"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">
            Detailed Requirements / Reproduction Steps
          </label>
          <textarea
            rows={3}
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition resize-none"
            placeholder="Describe edge cases, test requirements, or expected behaviors..."
          />
        </div>

        <div className="grid grid-cols-2 gap-3 pt-2">
          <button
            type="button"
            onClick={handlePlan}
            disabled={isLoading || !title.trim()}
            className="flex items-center justify-center space-x-2 py-2.5 px-4 rounded-xl text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 disabled:opacity-50 transition cursor-pointer"
          >
            <ListChecks className="w-3.5 h-3.5 text-indigo-400" />
            <span>Plan Issue</span>
          </button>

          <button
            type="button"
            onClick={handleRun}
            disabled={isLoading || !title.trim()}
            className="flex items-center justify-center space-x-2 py-2.5 px-4 rounded-xl text-xs font-semibold bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white shadow-lg shadow-indigo-500/20 disabled:opacity-50 transition cursor-pointer"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Running...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Run Autonomous Agent</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
