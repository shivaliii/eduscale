import api from './client';
import type {
  ExperimentConfig, ExperimentSummary, ExperimentMetrics,
  ExperimentComparison, CloudOverview,
} from '@/types';

export async function runExperiment(config: ExperimentConfig): Promise<{
  experiment_id: string;
  status: string;
  results_summary: Record<string, any>;
  message: string;
}> {
  const { data } = await api.post('/experiments/run', config);
  return data;
}

export async function listExperiments(filters?: {
  status?: string;
  scenario?: string;
  policy?: string;
  limit?: number;
}): Promise<ExperimentSummary[]> {
  const params = new URLSearchParams();
  if (filters?.status) params.set('status', filters.status);
  if (filters?.scenario) params.set('scenario', filters.scenario);
  if (filters?.policy) params.set('policy', filters.policy);
  if (filters?.limit) params.set('limit', String(filters.limit));
  const { data } = await api.get(`/experiments?${params}`);
  return data;
}

export async function getExperiment(id: string): Promise<ExperimentSummary> {
  const { data } = await api.get(`/experiments/${id}`);
  return data;
}

export async function getExperimentMetrics(id: string): Promise<ExperimentMetrics> {
  const { data } = await api.get(`/experiments/${id}/metrics`);
  return data;
}

export async function compareExperiments(
  reactiveId: string,
  predictiveId: string,
): Promise<ExperimentComparison> {
  const { data } = await api.get(`/experiments/compare/${reactiveId}/${predictiveId}`);
  return data;
}

export async function getCloudOverview(): Promise<CloudOverview> {
  const { data } = await api.get('/experiments/cloud/overview');
  return data;
}

export function getExportCsvUrl(id: string): string {
  return `/api/v1/experiments/${id}/export/csv`;
}

export function getExportJsonUrl(id: string): string {
  return `/api/v1/experiments/${id}/export/json`;
}

