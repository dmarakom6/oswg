<script lang="ts">
	import UrlInput from './UrlInput.svelte';
	import NumberStepper from './NumberStepper.svelte';
	import ToggleSwitch from './ToggleSwitch.svelte';
	import SegmentedControl from './SegmentedControl.svelte';
	import KeyValueList from './KeyValueList.svelte';
	import MergeConfig from './MergeConfig.svelte';
	import { DEFAULTS, LIMITS, RETENTION_OPTIONS } from '$lib/constants';
	import { isValidUrl } from '$lib/utils/validators';
	import { endpoints } from '$lib/api/endpoints';
	import { jobsStore } from '$lib/stores/jobs';
	import { connectJobWs } from '$lib/websocket/job-ws';
	import { notifications } from '$lib/stores/notifications';

	let url = $state('');
	let size = $state(DEFAULTS.wordlistSize);
	let maxPages = $state(DEFAULTS.maxPages);
	let minLength = $state(DEFAULTS.minLength);
	let maxLength = $state(DEFAULTS.maxLength);
	let enableLeet = $state(DEFAULTS.enableLeet);
	let enableUppercase = $state(DEFAULTS.enableUppercase);
	let enableNumbers = $state(DEFAULTS.enableNumbers);
	let enableSpecial = $state(DEFAULTS.enableSpecial);
	let leetLevel = $state<1 | 2>(DEFAULTS.leetLevel);
	let retentionSeconds = $state(DEFAULTS.retentionSeconds);
	let timeout = $state(DEFAULTS.timeoutSeconds);
	let respectRobots = $state(false);
	let userAgent = $state('');
	let rateLimit = $state(DEFAULTS.rateLimit);
	let jitter = $state(false);
	let headers = $state<{ name: string; value: string }[]>([]);
	let cookies = $state<{ name: string; value: string }[]>([]);
	let proxy = $state('');
	let merge = $state({ merge_words: [] as string[], merge_max: DEFAULTS.mergeMax, merge_builtin: false, merge_rockyou: false });
	let useSitemap = $state(false);
	let deduplicate = $state(true);
	let filterStopwords = $state(true);
	let stopwordThreshold = $state(0.5);
	let extraStopwords = $state('');
	let years = $state('');
	let specialChars = $state('!, @, #, $');
	let advancedOpen = $state(false);
	let submitting = $state(false);

	let urlError = $derived(url.length > 0 && !isValidUrl(url) ? 'Enter a valid URL including protocol (https://)' : '');
	let canSubmit = $derived(url.length > 0 && isValidUrl(url) && !submitting);
	let commonYears = $derived(
		years.split(',')
			.map((y) => parseInt(y.trim(), 10))
			.filter((y) => !Number.isNaN(y))
	);
	let parsedSpecialChars = $derived(
		specialChars.split(',').map((c) => c.trim()).filter(Boolean)
	);
	let specialCharsError = $derived(
		parsedSpecialChars.find((c) => c.length !== 1 || /[a-zA-Z0-9]/.test(c) || /\s/.test(c))
			? 'Only single special characters allowed (no letters, numbers or spaces).'
			: ''
	);

	async function handleSubmit() {
		if (!canSubmit) return;
		submitting = true;

		try {
			const response = await endpoints.generate({
				url,
				sitemap: useSitemap,
				size,
				max_pages: maxPages,
				min_length: minLength,
				max_length: maxLength,
				enable_leet: enableLeet,
				enable_uppercase: enableUppercase,
				enable_numbers: enableNumbers,
				enable_special: enableSpecial,
				leet_level: leetLevel,
				deduplicate,
				filter_stopwords: filterStopwords,
				stopword_threshold: stopwordThreshold,
				extra_stopwords: extraStopwords.split(',').map(w => w.trim()).filter(Boolean),
				common_years: commonYears,
				...((enableSpecial && parsedSpecialChars.length > 0 && !specialCharsError) ? { special_chars: parsedSpecialChars } : {}),
				timeout,
				respect_robots: respectRobots,
				...((userAgent.trim().length > 0) ? { user_agent: userAgent.trim() } : {}),
				rate_limit: rateLimit,
				jitter,
				headers: Object.fromEntries(headers.filter(h => h.name.trim()).map(h => [h.name.trim(), h.value])),
				cookies: Object.fromEntries(cookies.filter(c => c.name.trim()).map(c => [c.name.trim(), c.value])),
				...((proxy.trim().length > 0) ? { proxy: proxy.trim() } : {}),
				merge_words: merge.merge_words,
				merge_max: merge.merge_max,
				merge_builtin: merge.merge_builtin,
				merge_rockyou: merge.merge_rockyou,
				retention_seconds: retentionSeconds
			});

			jobsStore.upsert({
				job_id: response.job_id,
				type: 'generate',
				status: 'pending',
				progress: 0,
				created_at: new Date().toISOString(),
				updated_at: new Date().toISOString(),
				completed_at: null,
				error_message: null,
				result_file: null
			});

			jobsStore.setCurrent('generate', response.job_id);

			connectJobWs(response.job_id, (msg) => {
				jobsStore.upsert({
					job_id: msg.job_id,
					status: msg.status,
					progress: msg.progress
				});
			});

			notifications.add('success', 'Wordlist generation started');
		} catch (err) {
			notifications.add('error', err instanceof Error ? err.message : 'Failed to start generation');
		} finally {
			submitting = false;
		}
	}
</script>

<form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }} class="space-y-6">
	<div class="space-y-4">
		<h2 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Target</h2>
		<UrlInput value={url} onchange={(v) => (url = v)} error={urlError} />
	</div>

	<div class="space-y-4">
		<h2 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Scope</h2>
		<div class="grid grid-cols-2 gap-4">
			<NumberStepper value={maxPages} onchange={(v) => (maxPages = v)} label="Pages to scrape" min={LIMITS.maxPages.min} max={LIMITS.maxPages.max} />
			<NumberStepper value={size} onchange={(v) => (size = v)} label="Wordlist size" min={LIMITS.wordlistSize.min} max={LIMITS.wordlistSize.max} step={1000} />
		</div>
		<div class="flex items-center gap-3">
			<ToggleSwitch checked={useSitemap} onchange={(v) => (useSitemap = v)} label="Use sitemap.xml" />
			{#if useSitemap}
				<p class="text-xs text-muted-foreground">Discovers pages from sitemap instead of link following.</p>
			{/if}
		</div>
	</div>

	<div class="space-y-4">
		<h2 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Word Filters</h2>
		<div class="grid grid-cols-2 gap-4">
			<NumberStepper value={minLength} onchange={(v) => (minLength = v)} label="Min length" min={LIMITS.minLength.min} max={LIMITS.minLength.max} />
			<NumberStepper value={maxLength} onchange={(v) => (maxLength = v)} label="Max length" min={LIMITS.maxLength.min} max={LIMITS.maxLength.max} />
		</div>
	</div>

	<div class="space-y-4">
		<h2 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Mutations</h2>
		<div class="space-y-3">
			<ToggleSwitch checked={enableLeet} onchange={(v) => (enableLeet = v)} label="L33t speak" />
			<ToggleSwitch checked={enableUppercase} onchange={(v) => (enableUppercase = v)} label="Uppercase" />
			{#if enableLeet}
				<div class="ml-12 space-y-1.5">
					<SegmentedControl
						value={leetLevel}
						onchange={(v) => (leetLevel = v as 1 | 2)}
						options={[{ value: 1, label: 'Basic' }, { value: 2, label: 'Advanced' }]}
					/>
					{#if leetLevel === 2}
						<p class="text-xs text-muted-foreground">
							Advanced applies multiple l33t substitutions per word (e.g. <span class="font-mono">password</span> → <span class="font-mono">p@$$w0rd</span>, <span class="font-mono">p455w0r!</span>), generating more variations.
						</p>
					{/if}
				</div>
			{/if}
			<ToggleSwitch checked={enableNumbers} onchange={(v) => (enableNumbers = v)} label="Numbers" />
			<ToggleSwitch checked={enableSpecial} onchange={(v) => (enableSpecial = v)} label="Special chars" />
		</div>
	</div>

	<details bind:open={advancedOpen} class="space-y-4">
		<summary class="cursor-pointer text-xs font-semibold uppercase tracking-wider text-muted-foreground select-none hover:text-foreground transition-colors">
			Advanced
		</summary>
		<div class="space-y-3 pl-1">
			<ToggleSwitch checked={deduplicate} onchange={(v) => (deduplicate = v)} label="Deduplicate" />
			<p class="text-xs text-muted-foreground">Remove duplicate words from the output.</p>
			<ToggleSwitch checked={filterStopwords} onchange={(v) => (filterStopwords = v)} label="Filter common words" />
			<p class="text-xs text-muted-foreground">Exclude common English words and web boilerplate (e.g. "page", "in", "the").</p>
			{#if filterStopwords}
				<div class="space-y-1.5 ml-12">
					<label for="stopword-threshold" class="block text-sm font-medium text-foreground">
						Exclude words on &gt;{Math.round(stopwordThreshold * 100)}% of pages
					</label>
					<input
						id="stopword-threshold"
						type="range"
						min="0"
						max="1"
						step="0.05"
						bind:value={stopwordThreshold}
						class="w-full accent-primary"
					/>
					<p class="text-xs text-muted-foreground">Higher = less aggressive filtering. Set to 1.0 to disable frequency filtering.</p>
				</div>
				<div class="space-y-1.5">
					<label for="extra-stopwords" class="block text-sm font-medium text-foreground">Extra stopwords</label>
					<input
						id="extra-stopwords"
						type="text"
						bind:value={extraStopwords}
						placeholder="comma, separated, words"
						class="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
					/>
					<p class="text-xs text-muted-foreground">Comma-separated extra words to exclude.</p>
				</div>
			{/if}
			{#if enableNumbers}
				<div class="space-y-1.5">
					<label for="years" class="block text-sm font-medium text-foreground">Years</label>
					<input
						id="years"
						type="text"
						bind:value={years}
						placeholder="2026, 2025, 2024"
						class="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
					/>
					<p class="text-xs text-muted-foreground">Comma-separated years appended as suffixes. Empty = current year + previous 5.</p>
				</div>
			{/if}
			{#if enableSpecial}
				<div class="space-y-1.5">
					<label for="special-chars" class="block text-sm font-medium text-foreground">Special characters</label>
					<input
						id="special-chars"
						type="text"
						bind:value={specialChars}
						placeholder="!, @, #, $"
						class="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
					/>
					{#if specialCharsError}
						<p class="text-xs text-destructive">{specialCharsError}</p>
					{:else}
						<p class="text-xs text-muted-foreground">Comma-separated special characters appended to words. Empty = ! @ # $.</p>
					{/if}
				</div>
			{/if}
			<NumberStepper
				value={timeout}
				onchange={(v) => (timeout = v)}
				label="Timeout (seconds)"
				min={LIMITS.timeoutSeconds.min}
				max={LIMITS.timeoutSeconds.max}
				step={5}
			/>
			<ToggleSwitch checked={respectRobots} onchange={(v) => (respectRobots = v)} label="Respect robots.txt" />
			<p class="text-xs text-muted-foreground">Skip pages disallowed by the site's robots.txt.</p>
			<div class="space-y-1.5">
				<label for="user-agent" class="block text-sm font-medium text-foreground">User-Agent</label>
				<input
					id="user-agent"
					type="text"
					bind:value={userAgent}
					placeholder="Empty = httpx default"
					class="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
				/>
				<p class="text-xs text-muted-foreground">Custom User-Agent header sent with all requests.</p>
			</div>
			<div class="space-y-1.5">
				<NumberStepper
					value={rateLimit}
					onchange={(v) => (rateLimit = v)}
					label="Delay between requests (s)"
					min={LIMITS.rateLimit.min}
					max={LIMITS.rateLimit.max}
					step={0.5}
				/>
				<div class="flex items-center gap-3">
					<ToggleSwitch checked={jitter} onchange={(v) => (jitter = v)} label="Jitter" />
					{#if jitter}
						<p class="text-xs text-muted-foreground">Randomize delay ±50% (requires a delay &gt; 0).</p>
					{/if}
				</div>
			</div>
			<KeyValueList kind="header" items={headers} onchange={(v) => (headers = v)} />
			<KeyValueList kind="cookie" items={cookies} onchange={(v) => (cookies = v)} />
			<div class="space-y-1.5">
				<label for="proxy" class="block text-sm font-medium text-foreground">Proxy</label>
				<input
					id="proxy"
					type="text"
					bind:value={proxy}
					placeholder="http://127.0.0.1:8080"
					class="w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
				/>
				{#if proxy.trim().length > 0}
					<div class="space-y-1.5 rounded-md border border-border bg-muted/30 px-3 py-2">
						<p class="text-xs font-medium text-foreground">Why route through a proxy?</p>
						<ul class="list-inside list-disc space-y-1 text-xs text-muted-foreground">
							<li><span class="font-mono text-foreground">http://127.0.0.1:8080</span> — intercept and inspect live requests in Burp Suite before they hit the target.</li>
							<li><span class="font-mono text-foreground">socks5://127.0.0.1:9050</span> — route through Tor to hide your origin and IP.</li>
							<li>Bypass IP-based rate limits and geo-restrictions with rotating residential proxies.</li>
							<li>Works with http, https and socks5 schemes.</li>
						</ul>
					</div>
				{/if}
			</div>
			<MergeConfig value={merge} onchange={(v) => (merge = v)} />
			<div class="space-y-1.5">
				<label for="retention" class="block text-sm font-medium text-foreground">Retention</label>
				<select
					id="retention"
					bind:value={retentionSeconds}
					class="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
				>
					{#each RETENTION_OPTIONS as opt}
						<option value={opt.value}>{opt.label}</option>
					{/each}
				</select>
			</div>
		</div>
	</details>

	<button
		type="submit"
		disabled={!canSubmit}
		class="w-full rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
	>
		{#if submitting}
			<span class="flex items-center justify-center gap-2">
				<span class="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent"></span>
				Starting...
			</span>
		{:else}
			Generate Wordlist
		{/if}
	</button>
</form>
