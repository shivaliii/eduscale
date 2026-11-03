import React, { useState, useEffect, useCallback } from 'react';
import {
  Cloud,
  Activity,
  Cpu,
  MemoryStick,
  DollarSign,
  ShieldCheck,
  ShieldAlert,
  FlaskConical,
  Play,
  History,
  BarChart3,
  GitCompareArrows,
  ChevronDown,
  ChevronUp,
  Download,
  FileJson,
  FileSpreadsheet,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Zap,
  Clock,
  Server,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Loader2,
  Settings2,
  Gauge,
  Eye,
  Shuffle,
} from 'lucide-react';
import {
  LineChart,
  AreaChart,
  BarChart,
  ComposedChart,
  ResponsiveContainer,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Line,
  Area,
  Bar,
  ReferenceLine,
} from 'recharts';
import StatCard from '@/components/StatCard';
import LoadingSpinner from '@/components/LoadingSpinner';
import {
  runExperiment,
  listExperiments,
  getExperiment,
  getExperimentMetrics,
  compareExperiments,
  getCloudOverview,
  getExportCsvUrl,
  getExportJsonUrl,
} from '@/api/experiments';
import type {
  ExperimentConfig,
  ExperimentSummary,
  ExperimentMetrics,
  ExperimentComparison,
  CloudOverview,
} from '@/types';

// ─── Tab definitions ────────────────────────────────────────────────────────
const TABS = [
  { id: 'overview', label: 'Cloud Overview', icon: Cloud },
  { id: 'run', label: 'Run Experiment', icon: Play },
  { id: 'history', label: 'Experiment History', icon: History },
  { id: 'metrics', label: 'Experiment Metrics', icon: BarChart3 },
  { id: 'compare', label: 'Compare Experiments', icon: GitCompareArrows },
] as const;

type TabId = (typeof TABS)[number]['id'];

// ─── Scenario metadata ─────────────────────────────────────────────────────
const SCENARIOS: {
  value: ExperimentConfig['scenario'];
  label: string;
  description: string;
  icon: React.ReactNode;
  color: string;
}[] = [
  {
    value: 'normal',
    label: 'Normal',
    description: 'Steady-state traffic with minor fluctuations',
    icon: <Activity className="w-5 h-5" />,
    color: 'border-blue-500 bg-blue-500/10 text-blue-400',
  },
  {
    value: 'increasing',
    label: 'Increasing',
    description: 'Gradually rising request rate over time',
    icon: <TrendingUp className="w-5 h-5" />,
    color: 'border-green-500 bg-green-500/10 text-green-400',
  },
  {
    value: 'burst',
    label: 'Burst',
    description: 'Sudden traffic spikes with rapid scale demands',
    icon: <Zap className="w-5 h-5" />,
    color: 'border-amber-500 bg-amber-500/10 text-amber-400',
  },
  {
    value: 'deadline',
    label: 'Deadline',
    description: 'Assignment deadline pattern — exponential ramp',
    icon: <Clock className="w-5 h-5" />,
    color: 'border-red-500 bg-red-500/10 text-red-400',
  },
  {
    value: 'low',
    label: 'Low',
    description: 'Off-peak minimal traffic for cost optimization',
    icon: <TrendingDown className="w-5 h-5" />,
    color: 'border-cyan-500 bg-cyan-500/10 text-cyan-400',
  },
  {
    value: 'mixed',
    label: 'Mixed',
    description: 'Combination of patterns simulating a real day',
    icon: <Shuffle className="w-5 h-5" />,
    color: 'border-purple-500 bg-purple-500/10 text-purple-400',
  },
];

// ─── Helpers ────────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { cls: string; icon: React.ReactNode }> = {
    completed: {
      cls: 'bg-green-500/20 text-green-400 border-green-500/30',
      icon: <CheckCircle2 className="w-3.5 h-3.5" />,
    },
    running: {
      cls: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      icon: <Loader2 className="w-3.5 h-3.5 animate-spin" />,
    },
    failed: {
      cls: 'bg-red-500/20 text-red-400 border-red-500/30',
      icon: <XCircle className="w-3.5 h-3.5" />,
    },
    pending: {
      cls: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
      icon: <Clock className="w-3.5 h-3.5" />,
    },
  };
  const s = map[status] ?? map['pending'];
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${s.cls}`}
    >
      {s.icon}
      {status}
    </span>
  );
}

function SectionHeader({
  icon: Icon,
  title,
  subtitle,
  action,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between mb-6">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-blue-500/10">
          <Icon className="w-5 h-5 text-blue-400" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">{title}</h2>
          {subtitle && (
            <p className="text-sm text-slate-400 mt-0.5">{subtitle}</p>
          )}
        </div>
      </div>
      {action}
    </div>
  );
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
}

function formatTimestamp(ts: string): string {
  return ts ? new Date(ts).toLocaleString() : '—';
}

// ─── Default experiment config ──────────────────────────────────────────────
const DEFAULT_CONFIG: ExperimentConfig = {
  name: '',
  scenario: 'normal',
  scaling_policy: 'reactive',
  duration_seconds: 300,
  base_request_rate: 50,
  burst_multiplier: 3.0,
  forecast_horizon_seconds: 30,
  min_instances: 1,
  max_instances: 10,
  sla_latency_ms: 200,
  scaling_cooldown_seconds: 30,
  random_seed: 42,
};

// ─── Chart theme constants ──────────────────────────────────────────────────
const CHART_COLORS = {
  reactive: '#3b82f6',
  predictive: '#8b5cf6',
  good: '#22c55e',
  warning: '#f59e0b',
  danger: '#ef4444',
  cyan: '#06b6d4',
  area1: '#3b82f6',
  area2: '#8b5cf6',
};

const CHART_MARGIN = { top: 5, right: 20, left: 0, bottom: 5 };

// ═══════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════
export default function CloudDashboard() {
  // ── navigation state ──
  const [activeTab, setActiveTab] = useState<TabId>('overview');

  // ── overview ──
  const [overview, setOverview] = useState<CloudOverview | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(false);

  // ── run experiment ──
  const [config, setConfig] = useState<ExperimentConfig>({ ...DEFAULT_CONFIG });
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [runLoading, setRunLoading] = useState(false);
  const [runResult, setRunResult] = useState<{
    experiment_id: string;
    status: string;
    results_summary: any;
    message: string;
  } | null>(null);

  // ── history ──
  const [experiments, setExperiments] = useState<ExperimentSummary[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // ── metrics ──
  const [selectedExperiment, setSelectedExperiment] =
    useState<ExperimentSummary | null>(null);
  const [metrics, setMetrics] = useState<ExperimentMetrics | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(false);

  // ── compare ──
  const [reactiveId, setReactiveId] = useState('');
  const [predictiveId, setPredictiveId] = useState('');
  const [comparison, setComparison] = useState<ExperimentComparison | null>(
    null,
  );
  const [compareLoading, setCompareLoading] = useState(false);

  // ── data fetchers ──
  const fetchOverview = useCallback(async () => {
    setOverviewLoading(true);
    try {
      const data = await getCloudOverview();
      setOverview(data);
    } catch (err) {
      console.error('Failed to fetch cloud overview:', err);
    } finally {
      setOverviewLoading(false);
    }
  }, []);

  const fetchExperiments = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const data = await listExperiments();
      setExperiments(data);
    } catch (err) {
      console.error('Failed to fetch experiments:', err);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  const fetchMetrics = useCallback(async (id: string) => {
    setMetricsLoading(true);
    try {
      const [exp, met] = await Promise.all([
        getExperiment(id),
        getExperimentMetrics(id),
      ]);
      setSelectedExperiment(exp);
      setMetrics(met);
      setActiveTab('metrics');
    } catch (err) {
      console.error('Failed to fetch experiment metrics:', err);
    } finally {
      setMetricsLoading(false);
    }
  }, []);

  // ── mount ──
  useEffect(() => {
    fetchOverview();
    fetchExperiments();
  }, [fetchOverview, fetchExperiments]);

  // ── handlers ──
  const handleRunExperiment = async () => {
    if (!config.name.trim()) return;
    setRunLoading(true);
    setRunResult(null);
    try {
      const res = await runExperiment(config);
      setRunResult(res);
      fetchExperiments();
    } catch (err) {
      console.error('Experiment failed:', err);
    } finally {
      setRunLoading(false);
    }
  };

  const handleCompare = async () => {
    if (!reactiveId || !predictiveId) return;
    setCompareLoading(true);
    setComparison(null);
    try {
      const res = await compareExperiments(reactiveId, predictiveId);
      setComparison(res);
    } catch (err) {
      console.error('Comparison failed:', err);
    } finally {
      setCompareLoading(false);
    }
  };

  const updateConfig = <K extends keyof ExperimentConfig>(
    key: K,
    value: ExperimentConfig[K],
  ) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  };

  // ── build time-series data for Recharts ──
  const buildTimeSeriesData = (m: ExperimentMetrics) =>
    m.timestamps.map((t, i) => ({
      time: i,
      timestamp: t,
      requests: m.request_counts[i] ?? 0,
      predicted: m.predicted_requests[i] ?? 0,
      avgLatency: m.avg_latencies[i] ?? 0,
      p95Latency: m.p95_latencies[i] ?? 0,
      p99Latency: m.p99_latencies[i] ?? 0,
      cpu: m.cpu_utilizations[i] ?? 0,
      memory: m.memory_utilizations[i] ?? 0,
      instances: m.active_instances[i] ?? 0,
      scalingActions: m.scaling_actions[i] ?? 0,
      slaViolations: m.sla_violations[i] ?? 0,
      cost: m.costs[i] ?? 0,
    }));

  // ═════════════════════════════════════════════════════════════════════════
  // RENDER SECTIONS
  // ═════════════════════════════════════════════════════════════════════════

  // ── Section 1: Cloud Overview ─────────────────────────────────────────
  const renderOverview = () => {
    if (overviewLoading) {
      return (
        <div className="flex justify-center py-20">
          <LoadingSpinner size="lg" text="Loading cloud overview…" />
        </div>
      );
    }
    if (!overview) {
      return (
        <div className="text-center py-20 text-slate-400">
          <Cloud className="w-12 h-12 mx-auto mb-4 opacity-40" />
          <p>Unable to load cloud overview.</p>
          <button
            onClick={fetchOverview}
            className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition-colors"
          >
            Retry
          </button>
        </div>
      );
    }
    return (
      <div>
        <SectionHeader
          icon={Cloud}
          title="Cloud Overview"
          subtitle="Real-time platform health and resource utilization"
          action={
            <button
              onClick={fetchOverview}
              className="flex items-center gap-2 px-3 py-1.5 text-sm bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors text-slate-300"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          }
        />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            icon={Activity}
            label="Request Rate"
            value={`${overview.current_request_rate} req/s`}
            subtitle={`Predicted: ${overview.predicted_request_rate} req/s`}
            color="blue"
          />
          <StatCard
            icon={Gauge}
            label="Avg Latency"
            value={`${overview.avg_latency_ms.toFixed(1)} ms`}
            subtitle={`P95: ${overview.p95_latency_ms.toFixed(1)} ms`}
            color="green"
          />
          <StatCard
            icon={Cpu}
            label="CPU Utilization"
            value={`${overview.cpu_utilization.toFixed(1)}%`}
            color="purple"
          />
          <StatCard
            icon={MemoryStick}
            label="Memory Utilization"
            value={`${overview.memory_utilization.toFixed(1)}%`}
            color="cyan"
          />
          <StatCard
            icon={DollarSign}
            label="Estimated Cost"
            value={`$${overview.estimated_cost_usd.toFixed(2)}`}
            subtitle="Current billing period"
            color="orange"
          />
          <StatCard
            icon={
              overview.sla_status === 'healthy' ? ShieldCheck : ShieldAlert
            }
            label="SLA Status"
            value={overview.sla_status === 'healthy' ? 'Healthy' : 'At Risk'}
            color={overview.sla_status === 'healthy' ? 'green' : 'red'}
          />
          <StatCard
            icon={FlaskConical}
            label="Active Experiments"
            value={overview.active_experiments}
            color="blue"
          />
          <StatCard
            icon={FlaskConical}
            label="Total Experiments"
            value={overview.total_experiments}
            color="purple"
          />
        </div>
      </div>
    );
  };

  // ── Section 2: Run Experiment ─────────────────────────────────────────
  const renderRunExperiment = () => (
    <div>
      <SectionHeader
        icon={Play}
        title="Run Experiment"
        subtitle="Configure and launch a cloud scaling experiment"
      />

      <div className="space-y-6">
        {/* Experiment name */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Experiment Name
          </label>
          <input
            type="text"
            value={config.name}
            onChange={(e) => updateConfig('name', e.target.value)}
            placeholder="e.g. Burst-Predictive-v2"
            className="w-full px-4 py-2.5 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Scenario selector */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-3">
            Traffic Scenario
          </label>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {SCENARIOS.map((s) => (
              <button
                key={s.value}
                onClick={() => updateConfig('scenario', s.value)}
                className={`relative p-4 rounded-xl border-2 text-left transition-all ${
                  config.scenario === s.value
                    ? `${s.color} ring-1 ring-offset-0`
                    : 'border-slate-700 bg-slate-800/50 text-slate-400 hover:border-slate-500'
                }`}
              >
                <div className="flex items-center gap-2 mb-1.5">
                  {s.icon}
                  <span className="font-semibold text-sm">{s.label}</span>
                </div>
                <p className="text-xs opacity-75 leading-relaxed">
                  {s.description}
                </p>
              </button>
            ))}
          </div>
        </div>

        {/* Policy selector */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-3">
            Scaling Policy
          </label>
          <div className="grid grid-cols-2 gap-4">
            {(
              [
                {
                  value: 'reactive' as const,
                  label: 'Reactive',
                  desc: 'Scale based on current metrics and thresholds',
                  color: 'blue',
                },
                {
                  value: 'predictive' as const,
                  label: 'Predictive',
                  desc: 'ML-based forecasting with proactive scaling',
                  color: 'purple',
                },
              ] as const
            ).map((p) => (
              <button
                key={p.value}
                onClick={() => updateConfig('scaling_policy', p.value)}
                className={`p-4 rounded-xl border-2 text-left transition-all ${
                  config.scaling_policy === p.value
                    ? p.color === 'blue'
                      ? 'border-blue-500 bg-blue-500/10 text-blue-400'
                      : 'border-purple-500 bg-purple-500/10 text-purple-400'
                    : 'border-slate-700 bg-slate-800/50 text-slate-400 hover:border-slate-500'
                }`}
              >
                <span className="font-semibold">{p.label}</span>
                <p className="text-xs opacity-75 mt-1">{p.desc}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Advanced settings */}
        <div className="border border-slate-700 rounded-xl overflow-hidden">
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="w-full flex items-center justify-between px-5 py-3 bg-slate-800/50 hover:bg-slate-700/50 transition-colors"
          >
            <span className="flex items-center gap-2 text-sm font-medium text-slate-300">
              <Settings2 className="w-4 h-4" />
              Advanced Settings
            </span>
            {showAdvanced ? (
              <ChevronUp className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            )}
          </button>
          {showAdvanced && (
            <div className="p-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 border-t border-slate-700">
              {(
                [
                  {
                    key: 'duration_seconds',
                    label: 'Duration (s)',
                    type: 'number',
                  },
                  {
                    key: 'base_request_rate',
                    label: 'Base Request Rate',
                    type: 'number',
                  },
                  {
                    key: 'burst_multiplier',
                    label: 'Burst Multiplier',
                    type: 'number',
                    step: 0.1,
                  },
                  {
                    key: 'forecast_horizon_seconds',
                    label: 'Forecast Horizon (s)',
                    type: 'number',
                  },
                  {
                    key: 'min_instances',
                    label: 'Min Instances',
                    type: 'number',
                  },
                  {
                    key: 'max_instances',
                    label: 'Max Instances',
                    type: 'number',
                  },
                  {
                    key: 'sla_latency_ms',
                    label: 'SLA Threshold (ms)',
                    type: 'number',
                  },
                  {
                    key: 'scaling_cooldown_seconds',
                    label: 'Cooldown (s)',
                    type: 'number',
                  },
                  {
                    key: 'random_seed',
                    label: 'Random Seed',
                    type: 'number',
                  },
                ] as const
              ).map(({ key, label, type, step }: any) => (
                <div key={key}>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">
                    {label}
                  </label>
                  <input
                    type={type}
                    step={step}
                    value={(config as any)[key]}
                    onChange={(e) =>
                      updateConfig(
                        key as keyof ExperimentConfig,
                        type === 'number'
                          ? parseFloat(e.target.value) || 0
                          : e.target.value,
                      )
                    }
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Run button */}
        <button
          onClick={handleRunExperiment}
          disabled={runLoading || !config.name.trim()}
          className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:text-slate-500 rounded-xl font-semibold transition-colors"
        >
          {runLoading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Running Experiment…
            </>
          ) : (
            <>
              <Play className="w-5 h-5" />
              Run Experiment
            </>
          )}
        </button>

        {/* Results summary */}
        {runResult && (
          <div className="p-5 bg-green-500/10 border border-green-500/30 rounded-xl space-y-3">
            <div className="flex items-center gap-2 text-green-400 font-semibold">
              <CheckCircle2 className="w-5 h-5" />
              Experiment Complete
            </div>
            <p className="text-sm text-slate-300">{runResult.message}</p>
            <div className="flex items-center gap-3 text-sm">
              <span className="text-slate-400">
                ID: <code className="text-slate-200">{runResult.experiment_id}</code>
              </span>
              <StatusBadge status={runResult.status} />
            </div>
            {runResult.results_summary && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3">
                {Object.entries(runResult.results_summary).map(([k, v]) => (
                  <div key={k} className="p-3 bg-slate-800/60 rounded-lg">
                    <div className="text-xs text-slate-400 capitalize">
                      {k.replace(/_/g, ' ')}
                    </div>
                    <div className="text-sm font-semibold text-white mt-0.5">
                      {typeof v === 'number' ? v.toFixed(2) : String(v)}
                    </div>
                  </div>
                ))}
              </div>
            )}
            <button
              onClick={() => fetchMetrics(runResult.experiment_id)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition-colors mt-2"
            >
              <Eye className="w-4 h-4" />
              View Metrics
            </button>
          </div>
        )}
      </div>
    </div>
  );

  // ── Section 3: Experiment History ─────────────────────────────────────
  const renderHistory = () => (
    <div>
      <SectionHeader
        icon={History}
        title="Experiment History"
        subtitle="Browse and manage past experiments"
        action={
          <button
            onClick={fetchExperiments}
            className="flex items-center gap-2 px-3 py-1.5 text-sm bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors text-slate-300"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        }
      />

      {historyLoading ? (
        <div className="flex justify-center py-16">
          <LoadingSpinner size="md" text="Loading experiments…" />
        </div>
      ) : experiments.length === 0 ? (
        <div className="text-center py-16 text-slate-400">
          <FlaskConical className="w-12 h-12 mx-auto mb-4 opacity-40" />
          <p className="font-medium">No experiments yet</p>
          <p className="text-sm mt-1">
            Run your first experiment to see it here.
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-700">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-800/80 text-slate-400 text-left">
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Scenario</th>
                <th className="px-4 py-3 font-medium">Policy</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium text-right">Duration</th>
                <th className="px-4 py-3 font-medium text-right">
                  Avg Latency
                </th>
                <th className="px-4 py-3 font-medium text-right">
                  SLA Violations
                </th>
                <th className="px-4 py-3 font-medium text-right">Cost</th>
                <th className="px-4 py-3 font-medium text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {experiments.map((exp) => (
                <tr
                  key={exp.id}
                  className="hover:bg-slate-800/40 transition-colors"
                >
                  <td className="px-4 py-3 font-medium text-white">
                    {exp.name}
                  </td>
                  <td className="px-4 py-3 capitalize text-slate-300">
                    {exp.scenario}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                        exp.scaling_policy === 'predictive'
                          ? 'bg-purple-500/20 text-purple-400'
                          : 'bg-blue-500/20 text-blue-400'
                      }`}
                    >
                      {exp.scaling_policy}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={exp.status} />
                  </td>
                  <td className="px-4 py-3 text-right text-slate-300">
                    {formatDuration(exp.duration_seconds ?? 0)}
                  </td>
                  <td className="px-4 py-3 text-right text-slate-300">
                    {exp.results_summary?.avg_latency_ms != null
                      ? `${exp.results_summary.avg_latency_ms.toFixed(1)} ms`
                      : '—'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span
                      className={
                        (exp.results_summary?.sla_violations ?? 0) > 0
                          ? 'text-red-400'
                          : 'text-green-400'
                      }
                    >
                      {exp.results_summary?.sla_violations ?? '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-slate-300">
                    {exp.results_summary?.total_cost != null
                      ? `$${exp.results_summary.total_cost.toFixed(2)}`
                      : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-center gap-1">
                      <button
                        title="View metrics"
                        onClick={() => fetchMetrics(exp.id)}
                        className="p-1.5 hover:bg-slate-700 rounded-lg transition-colors text-slate-400 hover:text-white"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <a
                        href={getExportCsvUrl(exp.id)}
                        title="Export CSV"
                        className="p-1.5 hover:bg-slate-700 rounded-lg transition-colors text-slate-400 hover:text-white"
                      >
                        <FileSpreadsheet className="w-4 h-4" />
                      </a>
                      <a
                        href={getExportJsonUrl(exp.id)}
                        title="Export JSON"
                        className="p-1.5 hover:bg-slate-700 rounded-lg transition-colors text-slate-400 hover:text-white"
                      >
                        <FileJson className="w-4 h-4" />
                      </a>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );

  // ── Section 4: Experiment Metrics ─────────────────────────────────────
  const renderMetrics = () => {
    if (metricsLoading) {
      return (
        <div className="flex justify-center py-20">
          <LoadingSpinner size="lg" text="Loading experiment metrics…" />
        </div>
      );
    }
    if (!selectedExperiment || !metrics) {
      return (
        <div className="text-center py-20 text-slate-400">
          <BarChart3 className="w-12 h-12 mx-auto mb-4 opacity-40" />
          <p className="font-medium">No experiment selected</p>
          <p className="text-sm mt-1">
            Select an experiment from History to view its metrics.
          </p>
        </div>
      );
    }

    const data = buildTimeSeriesData(metrics);
    const rs = selectedExperiment.results_summary ?? ({} as any);
    const slaThreshold = selectedExperiment.configuration?.sla_latency_ms ?? 200;
    const isPredictive = selectedExperiment.scaling_policy === 'predictive';
    const mainColor = isPredictive ? CHART_COLORS.predictive : CHART_COLORS.reactive;

    return (
      <div className="space-y-8">
        <SectionHeader
          icon={BarChart3}
          title={`Metrics — ${selectedExperiment.name}`}
          subtitle={`${selectedExperiment.scenario} scenario · ${selectedExperiment.scaling_policy} policy · ${formatDuration(selectedExperiment.duration_seconds ?? 0)}`}
        />

        {/* Summary stat cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            icon={Activity}
            label="Total Requests"
            value={rs.total_requests ?? '—'}
            color="blue"
          />
          <StatCard
            icon={Gauge}
            label="Avg Latency"
            value={
              rs.avg_latency_ms != null
                ? `${rs.avg_latency_ms.toFixed(1)} ms`
                : '—'
            }
            color="green"
          />
          <StatCard
            icon={Gauge}
            label="P95 Latency"
            value={
              rs.p95_latency_ms != null
                ? `${rs.p95_latency_ms.toFixed(1)} ms`
                : '—'
            }
            color="purple"
          />
          <StatCard
            icon={Gauge}
            label="P99 Latency"
            value={
              rs.p99_latency_ms != null
                ? `${rs.p99_latency_ms.toFixed(1)} ms`
                : '—'
            }
            color="cyan"
          />
          <StatCard
            icon={ShieldAlert}
            label="SLA Violations"
            value={rs.sla_violations ?? '—'}
            color={(rs.sla_violations ?? 0) > 0 ? 'red' : 'green'}
          />
          <StatCard
            icon={DollarSign}
            label="Total Cost"
            value={
              rs.total_cost != null ? `$${rs.total_cost.toFixed(2)}` : '—'
            }
            color="orange"
          />
          <StatCard
            icon={Server}
            label="Scaling Actions"
            value={rs.scaling_actions ?? '—'}
            color="blue"
          />
          <StatCard
            icon={TrendingUp}
            label="Prediction MAE"
            value={
              rs.prediction_mae != null
                ? rs.prediction_mae.toFixed(2)
                : '—'
            }
            subtitle={
              rs.prediction_rmse != null
                ? `RMSE: ${rs.prediction_rmse.toFixed(2)}`
                : undefined
            }
            color="purple"
          />
        </div>

        {/* Charts grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Actual vs Predicted Workload */}
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-200 mb-4">
              Actual vs Predicted Workload
            </h3>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={data} margin={CHART_MARGIN}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis
                  dataKey="time"
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                  label={{
                    value: 'Time (s)',
                    position: 'insideBottom',
                    offset: -2,
                    fill: '#64748b',
                    fontSize: 11,
                  }}
                />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Line
                  type="monotone"
                  dataKey="requests"
                  name="Actual Requests"
                  stroke={CHART_COLORS.reactive}
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="predicted"
                  name="Predicted Requests"
                  stroke={CHART_COLORS.predictive}
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Inference Latency */}
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-200 mb-4">
              Inference Latency
            </h3>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={data} margin={CHART_MARGIN}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis
                  dataKey="time"
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                />
                <YAxis
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                  label={{
                    value: 'ms',
                    angle: -90,
                    position: 'insideLeft',
                    fill: '#64748b',
                    fontSize: 11,
                  }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <ReferenceLine
                  y={slaThreshold}
                  stroke={CHART_COLORS.danger}
                  strokeDasharray="4 4"
                  label={{
                    value: 'SLA',
                    fill: CHART_COLORS.danger,
                    fontSize: 11,
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="avgLatency"
                  name="Avg Latency"
                  stroke={CHART_COLORS.good}
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="p95Latency"
                  name="P95"
                  stroke={CHART_COLORS.warning}
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="p99Latency"
                  name="P99"
                  stroke={CHART_COLORS.danger}
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* CPU & Memory Utilization */}
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-200 mb-4">
              CPU & Memory Utilization
            </h3>
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={data} margin={CHART_MARGIN}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis
                  dataKey="time"
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                />
                <YAxis
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                  domain={[0, 100]}
                  label={{
                    value: '%',
                    angle: -90,
                    position: 'insideLeft',
                    fill: '#64748b',
                    fontSize: 11,
                  }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Area
                  type="monotone"
                  dataKey="cpu"
                  name="CPU %"
                  stroke={CHART_COLORS.reactive}
                  fill={CHART_COLORS.reactive}
                  fillOpacity={0.15}
                  strokeWidth={2}
                />
                <Area
                  type="monotone"
                  dataKey="memory"
                  name="Memory %"
                  stroke={CHART_COLORS.predictive}
                  fill={CHART_COLORS.predictive}
                  fillOpacity={0.15}
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Active Instances & Scaling Actions */}
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-200 mb-4">
              Active Instances & Scaling Actions
            </h3>
            <ResponsiveContainer width="100%" height={280}>
              <ComposedChart data={data} margin={CHART_MARGIN}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis
                  dataKey="time"
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                />
                <YAxis
                  yAxisId="left"
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar
                  yAxisId="right"
                  dataKey="scalingActions"
                  name="Scaling Actions"
                  fill={CHART_COLORS.warning}
                  fillOpacity={0.6}
                  barSize={6}
                />
                <Line
                  yAxisId="left"
                  type="stepAfter"
                  dataKey="instances"
                  name="Active Instances"
                  stroke={CHART_COLORS.cyan}
                  strokeWidth={2}
                  dot={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {/* Estimated Cost over Time */}
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-200 mb-4">
              Estimated Cost Over Time
            </h3>
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={data} margin={CHART_MARGIN}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis
                  dataKey="time"
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                />
                <YAxis
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                  label={{
                    value: 'USD',
                    angle: -90,
                    position: 'insideLeft',
                    fill: '#64748b',
                    fontSize: 11,
                  }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                  formatter={(value: any) => [
                    `$${Number(value).toFixed(4)}`,
                    'Cost',
                  ]}
                />
                <Area
                  type="monotone"
                  dataKey="cost"
                  name="Cost (USD)"
                  stroke={CHART_COLORS.warning}
                  fill={CHART_COLORS.warning}
                  fillOpacity={0.15}
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* SLA Violations */}
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-200 mb-4">
              SLA Violations
            </h3>
            <ResponsiveContainer width="100%" height={280}>
              <ComposedChart data={data} margin={CHART_MARGIN}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis
                  dataKey="time"
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                />
                <YAxis
                  yAxisId="left"
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                  label={{
                    value: 'ms',
                    angle: -90,
                    position: 'insideLeft',
                    fill: '#64748b',
                    fontSize: 11,
                  }}
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <ReferenceLine
                  yAxisId="left"
                  y={slaThreshold}
                  stroke={CHART_COLORS.danger}
                  strokeDasharray="4 4"
                  label={{
                    value: `SLA ${slaThreshold}ms`,
                    fill: CHART_COLORS.danger,
                    fontSize: 11,
                  }}
                />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="p95Latency"
                  name="P95 Latency"
                  stroke={CHART_COLORS.warning}
                  strokeWidth={2}
                  dot={false}
                />
                <Bar
                  yAxisId="right"
                  dataKey="slaViolations"
                  name="Violations"
                  fill={CHART_COLORS.danger}
                  fillOpacity={0.7}
                  barSize={4}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    );
  };

  // ── Section 5: Compare Experiments ────────────────────────────────────
  const renderCompare = () => {
    const reactiveExps = experiments.filter(
      (e) => e.scaling_policy === 'reactive' && e.status === 'completed',
    );
    const predictiveExps = experiments.filter(
      (e) => e.scaling_policy === 'predictive' && e.status === 'completed',
    );

    return (
      <div className="space-y-8">
        <SectionHeader
          icon={GitCompareArrows}
          title="Compare Experiments"
          subtitle="Side-by-side comparison of reactive vs predictive scaling"
        />

        {/* Selection row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-blue-400 mb-2">
              Reactive Experiment
            </label>
            <select
              value={reactiveId}
              onChange={(e) => setReactiveId(e.target.value)}
              className="w-full px-4 py-2.5 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select a reactive experiment…</option>
              {reactiveExps.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.name} — {e.scenario}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-purple-400 mb-2">
              Predictive Experiment
            </label>
            <select
              value={predictiveId}
              onChange={(e) => setPredictiveId(e.target.value)}
              className="w-full px-4 py-2.5 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              <option value="">Select a predictive experiment…</option>
              {predictiveExps.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.name} — {e.scenario}
                </option>
              ))}
            </select>
          </div>
        </div>

        <button
          onClick={handleCompare}
          disabled={compareLoading || !reactiveId || !predictiveId}
          className="flex items-center gap-2 px-6 py-2.5 bg-purple-600 hover:bg-purple-700 disabled:bg-slate-700 disabled:text-slate-500 rounded-xl font-semibold transition-colors"
        >
          {compareLoading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Comparing…
            </>
          ) : (
            <>
              <GitCompareArrows className="w-5 h-5" />
              Compare
            </>
          )}
        </button>

        {/* Comparison results */}
        {comparison && (
          <div className="space-y-8">
            {/* Improvement metrics */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              <div className="p-4 bg-slate-800/50 border border-slate-700 rounded-xl text-center">
                <div className="text-xs text-slate-400 mb-1">
                  Latency Improvement
                </div>
                <div
                  className={`text-2xl font-bold ${comparison.comparison.latency_improvement_pct > 0 ? 'text-green-400' : 'text-red-400'}`}
                >
                  {comparison.comparison.latency_improvement_pct > 0 ? '↓' : '↑'}{' '}
                  {Math.abs(comparison.comparison.latency_improvement_pct).toFixed(
                    1,
                  )}
                  %
                </div>
              </div>
              <div className="p-4 bg-slate-800/50 border border-slate-700 rounded-xl text-center">
                <div className="text-xs text-slate-400 mb-1">
                  P95 Improvement
                </div>
                <div
                  className={`text-2xl font-bold ${comparison.comparison.p95_improvement_pct > 0 ? 'text-green-400' : 'text-red-400'}`}
                >
                  {comparison.comparison.p95_improvement_pct > 0 ? '↓' : '↑'}{' '}
                  {Math.abs(comparison.comparison.p95_improvement_pct).toFixed(
                    1,
                  )}
                  %
                </div>
              </div>
              <div className="p-4 bg-slate-800/50 border border-slate-700 rounded-xl text-center">
                <div className="text-xs text-slate-400 mb-1">
                  SLA Violation Diff
                </div>
                <div
                  className={`text-2xl font-bold ${comparison.comparison.sla_violation_diff <= 0 ? 'text-green-400' : 'text-red-400'}`}
                >
                  {comparison.comparison.sla_violation_diff > 0 ? '+' : ''}
                  {comparison.comparison.sla_violation_diff}
                </div>
              </div>
              <div className="p-4 bg-slate-800/50 border border-slate-700 rounded-xl text-center">
                <div className="text-xs text-slate-400 mb-1">Cost Diff</div>
                <div
                  className={`text-2xl font-bold ${comparison.comparison.cost_diff_usd <= 0 ? 'text-green-400' : 'text-amber-400'}`}
                >
                  {comparison.comparison.cost_diff_usd > 0 ? '+' : ''}$
                  {comparison.comparison.cost_diff_usd.toFixed(2)}
                </div>
              </div>
              <div className="p-4 bg-slate-800/50 border border-slate-700 rounded-xl text-center">
                <div className="text-xs text-slate-400 mb-1">
                  Scaling Actions Diff
                </div>
                <div
                  className={`text-2xl font-bold ${comparison.comparison.scaling_actions_diff <= 0 ? 'text-green-400' : 'text-amber-400'}`}
                >
                  {comparison.comparison.scaling_actions_diff > 0 ? '+' : ''}
                  {comparison.comparison.scaling_actions_diff}
                </div>
              </div>
            </div>

            {/* Side-by-side summary table */}
            <div className="overflow-x-auto rounded-xl border border-slate-700">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-slate-800/80 text-slate-400">
                    <th className="px-5 py-3 text-left font-medium">Metric</th>
                    <th className="px-5 py-3 text-right font-medium text-blue-400">
                      Reactive
                    </th>
                    <th className="px-5 py-3 text-right font-medium text-purple-400">
                      Predictive
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/50">
                  {[
                    {
                      label: 'Avg Latency (ms)',
                      r: comparison.reactive.experiment.results_summary
                        ?.avg_latency_ms,
                      p: comparison.predictive.experiment.results_summary
                        ?.avg_latency_ms,
                    },
                    {
                      label: 'P95 Latency (ms)',
                      r: comparison.reactive.experiment.results_summary
                        ?.p95_latency_ms,
                      p: comparison.predictive.experiment.results_summary
                        ?.p95_latency_ms,
                    },
                    {
                      label: 'P99 Latency (ms)',
                      r: comparison.reactive.experiment.results_summary
                        ?.p99_latency_ms,
                      p: comparison.predictive.experiment.results_summary
                        ?.p99_latency_ms,
                    },
                    {
                      label: 'SLA Violations',
                      r: comparison.reactive.experiment.results_summary
                        ?.sla_violations,
                      p: comparison.predictive.experiment.results_summary
                        ?.sla_violations,
                    },
                    {
                      label: 'Total Cost (USD)',
                      r: comparison.reactive.experiment.results_summary
                        ?.total_cost,
                      p: comparison.predictive.experiment.results_summary
                        ?.total_cost,
                      fmt: '$',
                    },
                    {
                      label: 'Scaling Actions',
                      r: comparison.reactive.experiment.results_summary
                        ?.scaling_actions,
                      p: comparison.predictive.experiment.results_summary
                        ?.scaling_actions,
                    },
                    {
                      label: 'Total Requests',
                      r: comparison.reactive.experiment.results_summary
                        ?.total_requests,
                      p: comparison.predictive.experiment.results_summary
                        ?.total_requests,
                    },
                  ].map((row) => (
                    <tr
                      key={row.label}
                      className="hover:bg-slate-800/40 transition-colors"
                    >
                      <td className="px-5 py-3 text-slate-300">{row.label}</td>
                      <td className="px-5 py-3 text-right text-blue-300 font-mono">
                        {row.r != null
                          ? `${row.fmt ?? ''}${typeof row.r === 'number' ? row.r.toFixed(2) : row.r}`
                          : '—'}
                      </td>
                      <td className="px-5 py-3 text-right text-purple-300 font-mono">
                        {row.p != null
                          ? `${row.fmt ?? ''}${typeof row.p === 'number' ? row.p.toFixed(2) : row.p}`
                          : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Overlay charts */}
            {comparison.reactive.metrics && comparison.predictive.metrics && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Workload overlay */}
                {(() => {
                  const rData = buildTimeSeriesData(
                    comparison.reactive.metrics,
                  );
                  const pData = buildTimeSeriesData(
                    comparison.predictive.metrics,
                  );
                  const maxLen = Math.max(rData.length, pData.length);
                  const merged = Array.from({ length: maxLen }, (_, i) => ({
                    time: i,
                    reactiveRequests: rData[i]?.requests ?? null,
                    predictiveRequests: pData[i]?.requests ?? null,
                    reactivePredicted: rData[i]?.predicted ?? null,
                    predictivePredicted: pData[i]?.predicted ?? null,
                  }));
                  return (
                    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-5">
                      <h3 className="text-sm font-semibold text-slate-200 mb-4">
                        Workload — Overlay
                      </h3>
                      <ResponsiveContainer width="100%" height={280}>
                        <LineChart data={merged} margin={CHART_MARGIN}>
                          <CartesianGrid
                            strokeDasharray="3 3"
                            stroke="#334155"
                          />
                          <XAxis
                            dataKey="time"
                            tick={{ fill: '#94a3b8', fontSize: 11 }}
                          />
                          <YAxis
                            tick={{ fill: '#94a3b8', fontSize: 11 }}
                          />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: '#1e293b',
                              border: '1px solid #334155',
                              borderRadius: 8,
                              fontSize: 12,
                            }}
                          />
                          <Legend wrapperStyle={{ fontSize: 12 }} />
                          <Line
                            type="monotone"
                            dataKey="reactiveRequests"
                            name="Reactive — Actual"
                            stroke={CHART_COLORS.reactive}
                            strokeWidth={2}
                            dot={false}
                          />
                          <Line
                            type="monotone"
                            dataKey="predictiveRequests"
                            name="Predictive — Actual"
                            stroke={CHART_COLORS.predictive}
                            strokeWidth={2}
                            dot={false}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  );
                })()}

                {/* Latency overlay */}
                {(() => {
                  const rData = buildTimeSeriesData(
                    comparison.reactive.metrics,
                  );
                  const pData = buildTimeSeriesData(
                    comparison.predictive.metrics,
                  );
                  const maxLen = Math.max(rData.length, pData.length);
                  const merged = Array.from({ length: maxLen }, (_, i) => ({
                    time: i,
                    reactiveP95: rData[i]?.p95Latency ?? null,
                    predictiveP95: pData[i]?.p95Latency ?? null,
                    reactiveAvg: rData[i]?.avgLatency ?? null,
                    predictiveAvg: pData[i]?.avgLatency ?? null,
                  }));
                  const sla =
                    comparison.reactive.experiment.configuration
                      ?.sla_latency_ms ?? 200;
                  return (
                    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-5">
                      <h3 className="text-sm font-semibold text-slate-200 mb-4">
                        Latency — Overlay
                      </h3>
                      <ResponsiveContainer width="100%" height={280}>
                        <LineChart data={merged} margin={CHART_MARGIN}>
                          <CartesianGrid
                            strokeDasharray="3 3"
                            stroke="#334155"
                          />
                          <XAxis
                            dataKey="time"
                            tick={{ fill: '#94a3b8', fontSize: 11 }}
                          />
                          <YAxis
                            tick={{ fill: '#94a3b8', fontSize: 11 }}
                            label={{
                              value: 'ms',
                              angle: -90,
                              position: 'insideLeft',
                              fill: '#64748b',
                              fontSize: 11,
                            }}
                          />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: '#1e293b',
                              border: '1px solid #334155',
                              borderRadius: 8,
                              fontSize: 12,
                            }}
                          />
                          <Legend wrapperStyle={{ fontSize: 12 }} />
                          <ReferenceLine
                            y={sla}
                            stroke={CHART_COLORS.danger}
                            strokeDasharray="4 4"
                            label={{
                              value: 'SLA',
                              fill: CHART_COLORS.danger,
                              fontSize: 11,
                            }}
                          />
                          <Line
                            type="monotone"
                            dataKey="reactiveP95"
                            name="Reactive P95"
                            stroke={CHART_COLORS.reactive}
                            strokeWidth={2}
                            dot={false}
                          />
                          <Line
                            type="monotone"
                            dataKey="predictiveP95"
                            name="Predictive P95"
                            stroke={CHART_COLORS.predictive}
                            strokeWidth={2}
                            dot={false}
                          />
                          <Line
                            type="monotone"
                            dataKey="reactiveAvg"
                            name="Reactive Avg"
                            stroke={CHART_COLORS.reactive}
                            strokeWidth={1.5}
                            strokeDasharray="5 5"
                            dot={false}
                          />
                          <Line
                            type="monotone"
                            dataKey="predictiveAvg"
                            name="Predictive Avg"
                            stroke={CHART_COLORS.predictive}
                            strokeWidth={1.5}
                            strokeDasharray="5 5"
                            dot={false}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  );
                })()}

                {/* Instance count overlay */}
                {(() => {
                  const rData = buildTimeSeriesData(
                    comparison.reactive.metrics,
                  );
                  const pData = buildTimeSeriesData(
                    comparison.predictive.metrics,
                  );
                  const maxLen = Math.max(rData.length, pData.length);
                  const merged = Array.from({ length: maxLen }, (_, i) => ({
                    time: i,
                    reactiveInstances: rData[i]?.instances ?? null,
                    predictiveInstances: pData[i]?.instances ?? null,
                  }));
                  return (
                    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-5">
                      <h3 className="text-sm font-semibold text-slate-200 mb-4">
                        Active Instances — Overlay
                      </h3>
                      <ResponsiveContainer width="100%" height={280}>
                        <LineChart data={merged} margin={CHART_MARGIN}>
                          <CartesianGrid
                            strokeDasharray="3 3"
                            stroke="#334155"
                          />
                          <XAxis
                            dataKey="time"
                            tick={{ fill: '#94a3b8', fontSize: 11 }}
                          />
                          <YAxis
                            tick={{ fill: '#94a3b8', fontSize: 11 }}
                          />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: '#1e293b',
                              border: '1px solid #334155',
                              borderRadius: 8,
                              fontSize: 12,
                            }}
                          />
                          <Legend wrapperStyle={{ fontSize: 12 }} />
                          <Line
                            type="stepAfter"
                            dataKey="reactiveInstances"
                            name="Reactive Instances"
                            stroke={CHART_COLORS.reactive}
                            strokeWidth={2}
                            dot={false}
                          />
                          <Line
                            type="stepAfter"
                            dataKey="predictiveInstances"
                            name="Predictive Instances"
                            stroke={CHART_COLORS.predictive}
                            strokeWidth={2}
                            dot={false}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  );
                })()}

                {/* Cost overlay */}
                {(() => {
                  const rData = buildTimeSeriesData(
                    comparison.reactive.metrics,
                  );
                  const pData = buildTimeSeriesData(
                    comparison.predictive.metrics,
                  );
                  const maxLen = Math.max(rData.length, pData.length);
                  const merged = Array.from({ length: maxLen }, (_, i) => ({
                    time: i,
                    reactiveCost: rData[i]?.cost ?? null,
                    predictiveCost: pData[i]?.cost ?? null,
                  }));
                  return (
                    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-5">
                      <h3 className="text-sm font-semibold text-slate-200 mb-4">
                        Cost — Overlay
                      </h3>
                      <ResponsiveContainer width="100%" height={280}>
                        <AreaChart data={merged} margin={CHART_MARGIN}>
                          <CartesianGrid
                            strokeDasharray="3 3"
                            stroke="#334155"
                          />
                          <XAxis
                            dataKey="time"
                            tick={{ fill: '#94a3b8', fontSize: 11 }}
                          />
                          <YAxis
                            tick={{ fill: '#94a3b8', fontSize: 11 }}
                            label={{
                              value: 'USD',
                              angle: -90,
                              position: 'insideLeft',
                              fill: '#64748b',
                              fontSize: 11,
                            }}
                          />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: '#1e293b',
                              border: '1px solid #334155',
                              borderRadius: 8,
                              fontSize: 12,
                            }}
                            formatter={(value: any) => [
                              `$${Number(value).toFixed(4)}`,
                            ]}
                          />
                          <Legend wrapperStyle={{ fontSize: 12 }} />
                          <Area
                            type="monotone"
                            dataKey="reactiveCost"
                            name="Reactive Cost"
                            stroke={CHART_COLORS.reactive}
                            fill={CHART_COLORS.reactive}
                            fillOpacity={0.1}
                            strokeWidth={2}
                          />
                          <Area
                            type="monotone"
                            dataKey="predictiveCost"
                            name="Predictive Cost"
                            stroke={CHART_COLORS.predictive}
                            fill={CHART_COLORS.predictive}
                            fillOpacity={0.1}
                            strokeWidth={2}
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  );
                })()}
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  // ═════════════════════════════════════════════════════════════════════════
  // LAYOUT
  // ═════════════════════════════════════════════════════════════════════════
  return (
    <div className="min-h-screen bg-slate-900 text-white">
      {/* Header */}
      <div className="border-b border-slate-700 bg-slate-900/80 backdrop-blur-sm sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-gradient-to-br from-blue-500/20 to-purple-500/20">
                <Cloud className="w-6 h-6 text-blue-400" />
              </div>
              <div>
                <h1 className="text-lg font-bold">
                  Cloud Research Dashboard
                </h1>
                <p className="text-xs text-slate-400">
                  EduScale — Predictive Auto-Scaling Experiments
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-700 bg-slate-850">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex gap-1 overflow-x-auto -mb-px" aria-label="Tabs">
            {TABS.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
                    isActive
                      ? 'border-blue-500 text-blue-400'
                      : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-500'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'overview' && renderOverview()}
        {activeTab === 'run' && renderRunExperiment()}
        {activeTab === 'history' && renderHistory()}
        {activeTab === 'metrics' && renderMetrics()}
        {activeTab === 'compare' && renderCompare()}
      </main>
    </div>
  );
}
