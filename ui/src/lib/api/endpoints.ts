import { api } from './client';
import type {
	GenerateRequest,
	ScrapeRequest,
	MutateRequest,
	JobResponse,
	Job,
	MutateResponse,
	JobListItem,
	JobPreviewResult,
	CrawlGraph,
	WordCounts,
	MutationTree,
	AppInfo,
	DownloadFormat
} from './types';

export const endpoints = {
	generate: (req: GenerateRequest) => api.post<JobResponse>('/api/v1/generate', req),
	scrape: (req: ScrapeRequest) => api.post<JobResponse>('/api/v1/scrape', req),
	mutate: (req: MutateRequest) => api.post<MutateResponse>('/api/v1/mutate', req),
	getInfo: () => api.get<AppInfo>('/api/v1/info'),
	getJobStatus: (jobId: string) => api.get<Job>(`/api/v1/jobs/${jobId}`),
	listJobs: () => api.get<JobListItem[]>('/api/v1/jobs'),
	clearJobs: () => api.post<{ cleared: number }>('/api/v1/jobs/clear', {}),
	previewJob: (jobId: string, limit = 200) => api.get<JobPreviewResult>(`/api/v1/jobs/${jobId}/preview?limit=${limit}`),
	getGraph: (jobId: string) => api.get<CrawlGraph>(`/api/v1/jobs/${jobId}/graph`),
	getWordCounts: (jobId: string, limit = 200) =>
		api.get<WordCounts>(`/api/v1/jobs/${jobId}/word-counts?limit=${limit}`),
	getMutationTree: (jobId: string, limit = 200) =>
		api.get<MutationTree>(`/api/v1/jobs/${jobId}/mutation-tree?limit=${limit}`),
	getScreenshot: (jobId: string, page: number) =>
		api.download(`/api/v1/jobs/${jobId}/screenshot?page=${page}`),
	downloadJob: (
		jobId: string,
		target: 'rules' | 'base' | 'wordlist' | 'usernames' = 'rules',
		format: DownloadFormat = 'txt',
		gzip = false
	) => api.download(`/api/v1/jobs/${jobId}/download?target=${target}&format=${format}&gzip=${gzip}`)
};
