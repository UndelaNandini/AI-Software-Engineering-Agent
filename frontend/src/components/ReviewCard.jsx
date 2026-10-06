import React from 'react';
import { ShieldCheck, Zap, Award, CheckCircle, AlertTriangle, XCircle } from 'lucide-react';

export default function ReviewCard({ report }) {
  if (!report) return null;

  const getVerdictBadge = (verdict) => {
    switch (verdict) {
      case 'PASS':
      case 'GOOD':
        return {
          icon: <CheckCircle className="w-4 h-4 text-emerald-400" />,
          style: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
        };
      case 'WARNING':
      case 'ACCEPTABLE':
        return {
          icon: <AlertTriangle className="w-4 h-4 text-amber-400" />,
          style: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
        };
      default:
        return {
          icon: <XCircle className="w-4 h-4 text-rose-400" />,
          style: 'text-rose-400 bg-rose-500/10 border-rose-500/20',
        };
    }
  };

  const security = getVerdictBadge(report.security_verdict);
  const performance = getVerdictBadge(report.performance_verdict);
  const quality = getVerdictBadge(report.quality_verdict);

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur">
      <div className="flex items-center space-x-2.5 mb-4">
        <div className="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
          <ShieldCheck className="w-4 h-4" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
            Senior Code Review Audit
          </h3>
          <p className="text-xs text-slate-400">Automated security, performance & quality checks</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-4">
        {/* Security */}
        <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800/80 text-center">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider block mb-1">Security</span>
          <div className="flex items-center justify-center space-x-1.5">
            {security.icon}
            <span className={`text-xs font-bold ${security.style} px-2 py-0.5 rounded-full border`}>
              {report.security_verdict}
            </span>
          </div>
        </div>

        {/* Performance */}
        <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800/80 text-center">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider block mb-1">Performance</span>
          <div className="flex items-center justify-center space-x-1.5">
            {performance.icon}
            <span className={`text-xs font-bold ${performance.style} px-2 py-0.5 rounded-full border`}>
              {report.performance_verdict}
            </span>
          </div>
        </div>

        {/* Quality */}
        <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800/80 text-center">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider block mb-1">Quality</span>
          <div className="flex items-center justify-center space-x-1.5">
            {quality.icon}
            <span className={`text-xs font-bold ${quality.style} px-2 py-0.5 rounded-full border`}>
              {report.quality_verdict}
            </span>
          </div>
        </div>
      </div>

      <p className="text-xs text-slate-300 bg-slate-950 p-3.5 rounded-xl border border-slate-800/80 leading-relaxed">
        {report.summary}
      </p>
    </div>
  );
}
