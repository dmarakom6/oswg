export const DEFAULTS = {
	wordlistSize: 10000,
	maxPages: 10,
	minLength: 3,
	maxLength: 32,
	leetLevel: 1 as const,
	enableLeet: true,
	enableNumbers: true,
	enableSpecial: false,
	retentionSeconds: 3600
};

export const LIMITS = {
	wordlistSize: { min: 1, max: 1000000 },
	maxPages: { min: 1, max: 100 },
	minLength: { min: 1, max: 32 },
	maxLength: { min: 1, max: 128 },
	retentionSeconds: { min: 60, max: 86400 }
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
