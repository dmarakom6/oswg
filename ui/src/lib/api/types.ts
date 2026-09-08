export type JobStatus = 'pending' | 'processing' | 'completed' | 'failed';
export type JobType = 'generate' | 'scrape' | 'mutate';
export type ThemeMode = 'system' | 'light' | 'dark';
export type ActiveTab = 'generate' | 'scrape' | 'mutate';

export interface GenerateRequest {
	url: string;
	urls?: string[];
	sitemap?: boolean;
	allow_subdomains?: boolean;
	include_paths?: string[];
	exclude_patterns?: string[];
	size: number;
	max_pages: number;
	min_length: number;
	max_length: number;
	enable_leet: boolean;
	enable_uppercase?: boolean;
	enable_reverse_leet?: boolean;
	enable_numbers: boolean;
	enable_special: boolean;
	leet_level: 1 | 2;
	deduplicate?: boolean;
	filter_stopwords?: boolean;
	stopword_threshold?: number;
	extra_stopwords?: string[];
	common_years?: number[];
	special_chars?: string[];
	timeout?: number;
	respect_robots?: boolean;
	user_agent?: string;
	rate_limit?: number;
	jitter?: boolean;
	headers?: Record<string, string>;
	cookies?: Record<string, string>;
	proxy?: string;
	merge_words?: string[];
	merge_max?: number;
	merge_builtin?: boolean;
	merge_rockyou?: boolean;
	rule_format?: 'jtr' | 'hashcat';
	enable_random_combine?: boolean;
	random_combine_count?: number;
	random_combine_seed?: number | null;
	ai_enabled?: boolean;
	ai_provider?: 'auto' | 'ollama' | 'openai';
	ai_model?: string;
	ai_base_url?: string;
	ai_max_words?: number;
	ai_words_per_word?: number;
	ai_max_concurrency?: number;
	ai_timeout?: number;
	retention_seconds?: number;
}

export interface ScrapeRequest {
	url: string;
	urls?: string[];
	sitemap?: boolean;
	allow_subdomains?: boolean;
	include_paths?: string[];
	exclude_patterns?: string[];
	max_pages: number;
	timeout?: number;
	respect_robots?: boolean;
	user_agent?: string;
	rate_limit?: number;
	jitter?: boolean;
	headers?: Record<string, string>;
	cookies?: Record<string, string>;
	proxy?: string;
	retention_seconds?: number;
}

export interface MutateRequest {
	words: string[];
	enable_leet: boolean;
	enable_uppercase?: boolean;
	enable_reverse_leet?: boolean;
	enable_common_subs?: boolean;
	enable_numbers: boolean;
	enable_special: boolean;
	leet_level: 1 | 2;
	prepend?: string;
	append?: string;
	enable_case_perms?: boolean;
	case_perm_max?: number;
	enable_random_combine?: boolean;
	random_combine_count?: number;
	random_combine_seed?: number | null;
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
	words_count?: number | null;
	source_keywords?: number | null;
	truncated_count?: number | null;
	rule_format?: 'jtr' | 'hashcat' | null;
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
	mode: 'wordlist';
	total_words: number;
	preview: string[];
	truncated: boolean;
}

export interface JobRulePreview {
	job_id: string;
	mode: 'rules';
	format: 'jtr' | 'hashcat';
	rules: string[];
	rules_total: number;
	rules_truncated: boolean;
	base_words: string[];
	base_total: number;
	base_truncated: boolean;
	rules_path: string;
	base_path: string;
}

export type JobPreviewResult = JobPreview | JobRulePreview;

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
