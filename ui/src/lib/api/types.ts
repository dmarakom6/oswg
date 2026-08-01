export type JobStatus = 'pending' | 'processing' | 'completed' | 'failed';
export type JobType = 'generate' | 'scrape' | 'mutate';
export type ThemeMode = 'system' | 'light' | 'dark';
export type ActiveTab = 'generate' | 'scrape' | 'mutate';

export interface GenerateRequest {
	url: string;
	urls?: string[];
	sitemap?: boolean;
	size: number;
	max_pages: number;
	min_length: number;
	max_length: number;
	enable_leet: boolean;
	enable_numbers: boolean;
	enable_special: boolean;
	leet_level: 1 | 2;
	deduplicate?: boolean;
	retention_seconds?: number;
}

export interface ScrapeRequest {
	url: string;
	urls?: string[];
	sitemap?: boolean;
	max_pages: number;
	retention_seconds?: number;
}

export interface MutateRequest {
	words: string[];
	enable_leet: boolean;
	enable_numbers: boolean;
	enable_special: boolean;
	leet_level: 1 | 2;
}

export interface JobResponse {
	job_id: string;
	status: JobStatus;
	message: string;
}

export interface Job {
	job_id: string;
	type: JobType;
	status: JobStatus;
	progress: number;
	created_at: string;
	updated_at: string;
	completed_at: string | null;
	error_message: string | null;
	result_file: string | null;
}

export interface MutateResponse {
	words: string[];
	count: number;
	source_count: number;
}

export interface JobListItem {
	job_id: string;
	type: JobType;
	status: JobStatus;
	progress: number;
	created_at: string;
	expires_at: string;
	ttl_seconds: number;
	file_size_bytes: number | null;
}

export interface JobPreview {
	job_id: string;
	total_words: number;
	preview: string[];
	truncated: boolean;
}

export interface WSJobMessage {
	job_id: string;
	status: JobStatus;
	progress: number;
	message?: string;
}

export interface ErrorResponse {
	error: string;
	code: string;
	details?: Record<string, unknown>;
}
