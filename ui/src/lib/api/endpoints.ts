import { api } from './client';
import type {
	GenerateRequest,
	ScrapeRequest,
	MutateRequest,
	TestRequest,
	JobResponse,
	Job,
	MutateResponse,
	JobListItem,
	JobPreviewResult,
	CrawlGraph,
	WordCounts,
	MutationTree,
	UrlHistory,
	TemplatesResponse,
	TemplateRecord,
	PresetsResponse,
	AppInfo,
	DownloadFormat
} from './types';

export const endpoints = {
	generate: (req: GenerateRequest) => api.post<JobResponse>('/api/v1/generate', req),
	scrape: (req: ScrapeRequest) => api.post<JobResponse>('/api/v1/scrape', req),
	mutate: (req: MutateRequest) => api.post<MutateResponse>('/api/v1/mutate', req),
	test: (req: TestRequest) => api.post<JobResponse>('/api/v1/test', req),
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
	getUrlHistory: (q = '', limit = 10) =>
		api.get<UrlHistory>(`/api/v1/jobs/url-history?q=${encodeURIComponent(q)}&limit=${limit}`),
	listTemplates: () => api.get<TemplatesResponse>('/api/v1/templates'),
	getTemplate: (name: string) =>
		api.get<TemplateRecord>(`/api/v1/templates/${encodeURIComponent(name)}`),
	saveTemplate: (body: { name: string; type?: string; config?: Record<string, unknown>; from_job?: string }) =>
		api.post<{ name: string; type: string; created_at: string }>('/api/v1/templates', body),
	deleteTemplate: (name: string) =>
		api.delete<{ deleted: boolean }>(`/api/v1/templates/${encodeURIComponent(name)}`),
	getPresets: () => api.get<PresetsResponse>('/api/v1/presets'),
	getScreenshot: (jobId: string, page: number) =>
		api.download(`/api/v1/jobs/${jobId}/screenshot?page=${page}`),
	downloadJob: (
		jobId: string,
		target: 'rules' | 'base' | 'wordlist' | 'usernames' = 'rules',
		format: DownloadFormat = 'txt',
		gzip = false
	) => api.download(`/api/v1/jobs/${jobId}/download?target=${target}&format=${format}&gzip=${gzip}`)
};
