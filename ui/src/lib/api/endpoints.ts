import { api } from './client';
import type {
	GenerateRequest,
	ScrapeRequest,
	MutateRequest,
	JobResponse,
	Job,
	MutateResponse,
	JobListItem,
	JobPreview
} from './types';

export const endpoints = {
	generate: (req: GenerateRequest) => api.post<JobResponse>('/api/v1/generate', req),
	scrape: (req: ScrapeRequest) => api.post<JobResponse>('/api/v1/scrape', req),
	mutate: (req: MutateRequest) => api.post<MutateResponse>('/api/v1/mutate', req),
	getJobStatus: (jobId: string) => api.get<Job>(`/api/v1/jobs/${jobId}`),
	listJobs: () => api.get<JobListItem[]>('/api/v1/jobs'),
	clearJobs: () => api.post<{ cleared: number }>('/api/v1/jobs/clear', {}),
	previewJob: (jobId: string, limit = 200) => api.get<JobPreview>(`/api/v1/jobs/${jobId}/preview?limit=${limit}`),
	downloadJob: (jobId: string) => api.download(`/api/v1/jobs/${jobId}/download`)
};
