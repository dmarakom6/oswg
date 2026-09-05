export const DEFAULTS = {
	wordlistSize: 10000,
	maxPages: 10,
	minLength: 3,
	maxLength: 32,
	leetLevel: 1 as const,
	enableLeet: true,
	enableUppercase: true,
	enableReverseLeet: false,
	enableCommonSubs: false,
	enableCasePerms: false,
	casePermMax: 8,
	enableNumbers: true,
	enableSpecial: false,
	retentionSeconds: 3600,
	timeoutSeconds: 30,
	rateLimit: 0,
	mergeMax: 5000,
	enableRandomCombine: false,
	randomCombineCount: 1000,
	aiEnabled: false,
	aiProvider: 'auto' as const,
	aiWordsPerWord: 3,
	aiMaxWords: 1000,
	aiConcurrency: 2
};

export const LIMITS = {
	wordlistSize: { min: 1, max: 1000000 },
	maxPages: { min: 1, max: 100 },
	minLength: { min: 1, max: 32 },
	maxLength: { min: 1, max: 128 },
	retentionSeconds: { min: 60, max: 86400 },
	timeoutSeconds: { min: 1, max: 300 },
	rateLimit: { min: 0, max: 60 },
	mergeMax: { min: 1, max: 1000000 },
	casePermMax: { min: 2, max: 16 },
	aiWordsPerWord: { min: 1, max: 20 },
	aiMaxWords: { min: 1, max: 100000 },
	aiConcurrency: { min: 1, max: 16 }
};

export const RETENTION_OPTIONS = [
	{ label: '5 minutes', value: 300 },
	{ label: '15 minutes', value: 900 },
	{ label: '1 hour', value: 3600 },
	{ label: '6 hours', value: 21600 },
	{ label: '24 hours', value: 86400 }
];

export const TABS = [
	{ id: 'generate' as const, label: 'Generate', shortcut: '1' },
	{ id: 'scrape' as const, label: 'Scrape', shortcut: '2' },
	{ id: 'mutate' as const, label: 'Mutate', shortcut: '3' }
];
