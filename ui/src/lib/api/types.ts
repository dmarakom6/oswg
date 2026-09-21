export type JobStatus = 'pending' | 'processing' | 'completed' | 'failed';
export type JobType = 'generate' | 'scrape' | 'mutate' | 'test';
export type ThemeMode = 'system' | 'light' | 'dark';
export type ActiveTab = 'generate' | 'scrape' | 'mutate' | 'test';

export interface GenerateRequest {
	url: string;
	urls?: string[];
	sitemap?: boolean;
	allow_subdomains?: boolean;
	include_paths?: string[];
	exclude_patterns?: string[];
	crawl_strategy?: 'bfs' | 'dfs';
	js_render?: boolean;
	extract_emails?: boolean;
	extract_usernames?: boolean;
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
	cookie_file?: string;
	storage_state?: string;
	proxy?: string;
	auth_type?: 'basic' | 'digest' | 'ntlm';
	auth_user?: string;
	auth_pass?: string;
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
	crawl_strategy?: 'bfs' | 'dfs';
	js_render?: boolean;
	extract_emails?: boolean;
	extract_usernames?: boolean;
	max_pages: number;
	timeout?: number;
	respect_robots?: boolean;
	user_agent?: string;
	rate_limit?: number;
	jitter?: boolean;
	headers?: Record<string, string>;
	cookies?: Record<string, string>;
	cookie_file?: string;
	storage_state?: string;
	proxy?: string;
	auth_type?: 'basic' | 'digest' | 'ntlm';
	auth_user?: string;
	auth_pass?: string;
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
	crawl_strategy?: 'bfs' | 'dfs' | null;
	screenshot_count?: number | null;
	email_count?: number | null;
	username_count?: number | null;
}

export interface AppInfo {
	version: string;
	js_available: boolean;
	test_tools?: Record<string, boolean>;
}

export type DownloadFormat = 'txt' | 'json' | 'csv';

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
	url?: string | null;
}

export interface TemplateInfo {
	name: string;
	type: 'generate' | 'scrape';
	created_at: string;
}

export interface TemplateRecord extends TemplateInfo {
	config: Record<string, unknown>;
}

export interface TemplatesResponse {
	templates: TemplateInfo[];
}

export interface PresetsResponse {
	presets: Record<string, Record<string, unknown>>;
}

export interface TestRequest {
	tool: string;
	wordlist_job_id?: string;
	wordlist_text?: string;
	mode?: number;
	hashes_text?: string;
	users_text?: string;
	rules_text?: string;
	host?: string;
	service?: string;
	url?: string;
	capture_text?: string;
	retention_seconds?: number;
}

export interface TestEntry {
	hash?: string;
	user?: string;
	password?: string;
	path?: string;
	status?: string;
	key?: string;
}

export interface TestPreview {
	job_id: string;
	mode: 'test';
	tool: string;
	kind: string;
	found: number;
	entries: TestEntry[];
}

export interface JobPreview {
	job_id: string;
	mode: 'wordlist';
	total_words: number;
	preview: string[];
	truncated: boolean;
	usernames?: string[];
	usernames_total?: number;
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

export type JobPreviewResult = JobPreview | JobRulePreview | TestPreview;

export interface CrawlGraph {
	job_id: string;
	crawl_strategy: 'bfs' | 'dfs' | null;
	nodes: { id: string }[];
	edges: [string, string][];
}

export interface WordCount {
	word: string;
	count: number;
}

export interface WordCounts {
	job_id: string;
	total: number;
	words: WordCount[];
}

export interface MutationTree {
	job_id: string;
	tree: Record<string, string[]>;
}

export interface UrlHistoryEntry {
	url: string;
	count: number;
}

export interface UrlHistory {
	urls: UrlHistoryEntry[];
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
