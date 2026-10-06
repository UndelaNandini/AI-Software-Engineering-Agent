import React, { useEffect, useRef } from 'react';
import { Terminal, Trash2, Radio } from 'lucide-react';

export default function LiveTerminal({ logs, isConnected, onClear }) {
  const terminalRef = useRef(null);

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs]);

  const getBadgeStyle = (type) => {
    switch (type) {
      case 'THINKING':
        return 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20';
      case 'TOOL_CALL':
      case 'TOOL_RESULT':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'TEST_OUTPUT':
        return 'bg-sky-500/10 text-sky-400 border-sky-500/20';
      case 'REPAIR_ATTEMPT':
        return 'bg-orange-500/10 text-orange-400 border-orange-500/20';
      case 'REVIEW':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
      case 'COMPLETE':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'ERROR':
        return 'bg-rose-500/10 text-rose-400 border-rose-500/20';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  const getTextColor = (type) => {
    switch (type) {
      case 'THINKING': return 'text-indigo-300';
      case 'TOOL_CALL':
      case 'TOOL_RESULT': return 'text-amber-300';
      case 'TEST_OUTPUT': return 'text-sky-300';
      case 'REPAIR_ATTEMPT': return 'text-orange-300';
      case 'REVIEW': return 'text-purple-300';
      case 'COMPLETE': return 'text-emerald-300';
      case 'ERROR': return 'text-rose-400';
      default: return 'text-slate-300';
    }
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl shadow-xl flex flex-col h-[460px] overflow-hidden backdrop-blur">
      {/* Terminal Bar */}
      <div className="bg-slate-950 px-4 py-3 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="flex items-center space-x-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-rose-500/80"></div>
            <div className="w-2.5 h-2.5 rounded-full bg-amber-500/80"></div>
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/80"></div>
          </div>
          <span className="text-xs font-mono text-slate-400 ml-2 flex items-center">
            <Terminal className="w-3.5 h-3.5 mr-1.5 text-indigo-400" />
            agent-telemetry.stream
          </span>
        </div>

        <div className="flex items-center space-x-3">
          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border ${
            isConnected
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
              : 'bg-slate-800 text-slate-400 border-slate-700'
          }`}>
            <Radio className={`w-2.5 h-2.5 mr-1 ${isConnected ? 'animate-pulse' : ''}`} />
            {isConnected ? 'WebSocket Live' : 'Idle'}
          </span>

          <button
            onClick={onClear}
            className="text-slate-500 hover:text-slate-300 transition text-xs flex items-center cursor-pointer"
          >
            <Trash2 className="w-3 h-3 mr-1" /> Clear
          </button>
        </div>
      </div>

      {/* Terminal Screen */}
      <div
        ref={terminalRef}
        className="flex-1 p-4 font-mono text-[11px] overflow-y-auto space-y-2 bg-slate-950 text-slate-300 leading-relaxed"
      >
        {logs.length === 0 ? (
          <div className="text-slate-600 select-none">// Ready. Enter an issue and click "Run Agent" to stream telemetry in real time.</div>
        ) : (
          logs.map((log, index) => (
            <div key={index} className="flex items-start space-x-2.5">
              <span className="text-slate-600 select-none shrink-0 text-[10px]">
                {new Date(log.timestamp).toLocaleTimeString()}
              </span>
              <span className={`px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase tracking-wider shrink-0 border ${getBadgeStyle(log.event_type)}`}>
                {log.event_type}
              </span>
              <span className={`${getTextColor(log.event_type)} flex-1 break-words`}>
                {log.message}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
