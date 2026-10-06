import React from 'react';
import { CheckCircle2, AlertTriangle, FileCode, ArrowRight, ShieldCheck } from 'lucide-react';

export default function PlanViewer({ plan, onApprove, isExecuting }) {
  if (!plan) return null;

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
            <FileCode className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
              Implementation Plan
            </h3>
            <p className="text-[11px] text-slate-400 font-mono">ID: {plan.plan_id.slice(0, 8)}</p>
          </div>
        </div>

        <span className={`text-[11px] px-2.5 py-1 rounded-full font-medium border ${
          plan.status === 'APPROVED'
            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
            : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
        }`}>
          {plan.status}
        </span>
      </div>

      <p className="text-xs text-slate-300 mb-4 leading-relaxed bg-slate-950 p-3 rounded-xl border border-slate-800/80">
        {plan.summary}
      </p>

      {/* Steps List */}
      <div className="space-y-2 mb-4 max-h-56 overflow-y-auto pr-1">
        {plan.steps.map((step) => (
          <div
            key={step.step_number}
            className="p-3 rounded-xl bg-slate-950 border border-slate-800/80 flex items-start space-x-3 text-xs"
          >
            <span className="w-5 h-5 rounded-full bg-indigo-500/20 text-indigo-400 font-bold flex items-center justify-center shrink-0 text-[10px]">
              {step.step_number}
            </span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold text-amber-400 text-[11px] uppercase tracking-wide">
                  {step.action}
                </span>
                <span className="font-mono text-slate-400 text-[10px] truncate max-w-[180px]">
                  {step.target_file}
                </span>
              </div>
              <p className="text-slate-300 text-[11px]">{step.instruction}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between border-t border-slate-800 pt-3.5">
        <div className="flex items-center text-xs text-slate-400 space-x-1.5">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
          <span className="text-[11px] italic truncate max-w-[260px]">{plan.risk_assessment}</span>
        </div>

        {plan.status !== 'APPROVED' && (
          <button
            onClick={() => onApprove(plan.plan_id)}
            disabled={isExecuting}
            className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-500/20 disabled:opacity-50 transition cursor-pointer"
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Approve & Execute</span>
          </button>
        )}
      </div>
    </div>
  );
}
