<script lang="ts">
	import UrlInput from './UrlInput.svelte';
	import NumberStepper from './NumberStepper.svelte';
	import ToggleSwitch from './ToggleSwitch.svelte';
	import SegmentedControl from './SegmentedControl.svelte';
	import KeyValueList from './KeyValueList.svelte';
	import AuthField from './AuthField.svelte';
	import HttpAuthField from './HttpAuthField.svelte';
	import StringList from './StringList.svelte';
	import MergeConfig from './MergeConfig.svelte';
	import { DEFAULTS, LIMITS, RETENTION_OPTIONS } from '$lib/constants';
	import { isValidUrl } from '$lib/utils/validators';
	import { endpoints } from '$lib/api/endpoints';
	import { jobsStore } from '$lib/stores/jobs';
	import { connectJobWs } from '$lib/websocket/job-ws';
	import { jsAvailable } from '$lib/stores/capabilities';
	import { activeTab } from '$lib/stores/tabs';
	import { focusUrlSignal, runSignal } from '$lib/stores/shortcuts';
	import { modLabel } from '$lib/shortcuts';

	let url = $state('');
	let size = $state(DEFAULTS.wordlistSize);
	let maxPages = $state(DEFAULTS.maxPages);
	let minLength = $state(DEFAULTS.minLength);
	let maxLength = $state(DEFAULTS.maxLength);
	let enableLeet = $state(DEFAULTS.enableLeet);
	let enableUppercase = $state(DEFAULTS.enableUppercase);
	let enableReverseLeet = $state(DEFAULTS.enableReverseLeet);
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
	let cookieFile = $state('');
	let sessionState = $state('');
	let authType = $state<'' | 'basic' | 'digest' | 'ntlm'>('');
	let authUser = $state('');
	let authPass = $state('');
	let proxy = $state('');
	let merge = $state({ merge_words: [] as string[], merge_max: DEFAULTS.mergeMax, merge_builtin: false, merge_rockyou: false });
	let ruleFormat = $state<'jtr' | 'hashcat' | undefined>(undefined);
	let useSitemap = $state(false);
	let allowSubdomains = $state(false);
	let includePaths = $state<string[]>([]);
	let excludePatterns = $state<string[]>([]);
	let crawlStrategy = $state<'bfs' | 'dfs'>('bfs');
	let jsRender = $state(false);
	let extractEmails = $state(false);
	let extractUsernames = $state(false);
	let deduplicate = $state(true);
	let filterStopwords = $state(true);
	let stopwordThreshold = $state(0.5);
	let extraStopwords = $state('');
	let years = $state('');
	let specialChars = $state('!, @, #, $');
	let enableRandomCombine = $state(DEFAULTS.enableRandomCombine);
	let randomCombineCount = $state(DEFAULTS.randomCombineCount);
	let randomCombineSeed = $state('');
	let aiEnabled = $state(DEFAULTS.aiEnabled);
	let aiProvider = $state<'auto' | 'ollama' | 'openai'>(DEFAULTS.aiProvider);
	let aiModel = $state('');
	let aiBaseUrl = $state('');
	let aiWordsPerWord = $state(DEFAULTS.aiWordsPerWord);
	let aiMaxWords = $state(DEFAULTS.aiMaxWords);
	let aiConcurrency = $state(DEFAULTS.aiConcurrency);
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
	let parsedCombineSeed = $derived(
		randomCombineSeed.trim().length > 0 ? parseInt(randomCombineSeed.trim(), 10) : undefined
	);
	let combineSeedError = $derived(
		randomCombineSeed.trim().length > 0 && Number.isNaN(parsedCombineSeed)
			? 'Enter a valid integer seed or leave empty for random output.'
			: ''
	);

	let lastHandledRun = 0;

	$effect(() => {
		if ($runSignal > 0 && $runSignal !== lastHandledRun && $activeTab === 'generate') {
			lastHandledRun = $runSignal;
			handleSubmit();
		}
	});

	async function handleSubmit() {
		if (!canSubmit) return;
		submitting = true;

		try {
			const response = await endpoints.generate({
				url,
				sitemap: useSitemap,
				allow_subdomains: allowSubdomains,
				include_paths: includePaths,
				exclude_patterns: excludePatterns,
				crawl_strategy: crawlStrategy,
				js_render: jsRender,
				extract_emails: extractEmails,
				extract_usernames: extractUsernames,
				size,
				max_pages: maxPages,
				min_length: minLength,
				max_length: maxLength,
				enable_leet: enableLeet,
				enable_uppercase: enableUppercase,
				enable_reverse_leet: enableReverseLeet,
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
				cookie_file: cookieFile,
				storage_state: sessionState,
				...((proxy.trim().length > 0) ? { proxy: proxy.trim() } : {}),
				...(authType ? { auth_type: authType, auth_user: authUser.trim(), auth_pass: authPass } : {}),
				merge_words: merge.merge_words,
				merge_max: merge.merge_max,
				merge_builtin: merge.merge_builtin,
				merge_rockyou: merge.merge_rockyou,
				rule_format: ruleFormat,
				enable_random_combine: enableRandomCombine,
				...((enableRandomCombine && randomCombineCount > 0) ? { random_combine_count: randomCombineCount } : {}),
				...(enableRandomCombine && !combineSeedError && parsedCombineSeed !== undefined ? { random_combine_seed: parsedCombineSeed } : {}),
				ai_enabled: aiEnabled,
				...(aiEnabled ? {
					ai_provider: aiProvider,
					ai_model: aiModel.trim() || undefined,
					ai_base_url: aiBaseUrl.trim() || undefined,
					ai_max_words: aiMaxWords,
					ai_words_per_word: aiWordsPerWord,
					ai_max_concurrency: aiConcurrency
				} : {}),
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

			} catch {
		} finally {
			submitting = false;
		}
	}
</script>

<form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }} class="space-y-6">
	<div class="space-y-4">
		<h2 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Target</h2>
		<UrlInput value={url} focusSignal={$focusUrlSignal} onchange={(v) => (url = v)} error={urlError} />
	</div>

	<div class="space-y-4">
		<h2 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Scope</h2>
		<div class="grid grid-cols-2 gap-4">
			<NumberStepper value={maxPages} onchange={(v) => (maxPages = v)} label="Pages to scrape" min={LIMITS.maxPages.min} max={LIMITS.maxPages.max} />
			<NumberStepper value={size} onchange={(v) => (size = v)} label="Wordlist size" min={LIMITS.wordlistSize.min} max={LIMITS.wordlistSize.max} step={1000} />
		</div>
		<div class="flex items-center gap-3">
			<ToggleSwitch checked={allowSubdomains} onchange={(v) => (allowSubdomains = v)} label="Allow subdomains" />
			{#if allowSubdomains}
				<p class="text-xs text-muted-foreground">Crawl sibling subdomains (e.g. www → blog, api).</p>
			{:else}
				<p class="text-xs text-muted-foreground">Stay within the exact host.</p>
			{/if}
		</div>
		<div class="space-y-1.5">
			<span class="block text-sm font-medium text-foreground">Discovery order</span>
			<SegmentedControl
				value={crawlStrategy}
				onchange={(v) => (crawlStrategy = v as 'bfs' | 'dfs')}
				options={[
					{ value: 'bfs', label: 'Breadth-first' },
					{ value: 'dfs', label: 'Depth-first' }
				]}
				disabled={useSitemap}
			/>
			{#if useSitemap}
				<p class="text-xs text-muted-foreground">Link discovery is replaced by the sitemap.</p>
			{:else if crawlStrategy === 'dfs'}
				<p class="text-xs text-muted-foreground">DFS goes deep down one branch before siblings — can burn max_pages on a single path.</p>
			{/if}
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
			<ToggleSwitch checked={enableLeet} onchange={(v) => { enableLeet = v; if (v) enableReverseLeet = false; }} label="L33t speak" />
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
			<ToggleSwitch checked={enableUppercase} onchange={(v) => (enableUppercase = v)} label="Uppercase" />
			<ToggleSwitch checked={enableNumbers} onchange={(v) => (enableNumbers = v)} label="Numbers" />
			<ToggleSwitch checked={enableSpecial} onchange={(v) => (enableSpecial = v)} label="Special chars" />
		</div>
	</div>

	<details bind:open={advancedOpen} class="space-y-4">
		<summary class="cursor-pointer text-xs font-semibold uppercase tracking-wider text-muted-foreground select-none hover:text-foreground transition-colors">
			Advanced
		</summary>
		<div class="space-y-3 pl-1">
			<ToggleSwitch checked={jsRender} onchange={(v) => (jsRender = v)} label="JavaScript rendering" disabled={!$jsAvailable} />
			{#if !$jsAvailable}
				<p class="text-xs text-muted-foreground">
					Requires the optional dependency. Install with <span class="font-mono">pip install 'oswg[js]'</span> then <span class="font-mono">playwright install chromium</span>.
				</p>
			{:else}
				<p class="text-xs text-muted-foreground">Render pages in a real browser for JS-driven sites. Saves a screenshot per page.</p>
			{/if}
			<ToggleSwitch checked={extractEmails} onchange={(v) => (extractEmails = v)} label="Extract email addresses" />
			<p class="text-xs text-muted-foreground">Include full email addresses found on the target in the wordlist.</p>
			<ToggleSwitch checked={extractUsernames} onchange={(v) => (extractUsernames = v)} label="Extract usernames" />
			<p class="text-xs text-muted-foreground">Save usernames to a separate sidecar list (not merged into the wordlist).</p>
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
			<ToggleSwitch checked={enableRandomCombine} onchange={(v) => (enableRandomCombine = v)} label="Random combine" />
			{#if enableRandomCombine}
				<div class="ml-12 space-y-1.5">
					<NumberStepper
						value={randomCombineCount}
						onchange={(v) => (randomCombineCount = v)}
						label="Combinations"
						min={1}
						max={1000000}
						step={100}
					/>
					<div class="space-y-1.5">
						<label for="combine-seed" class="block text-sm font-medium text-foreground">Seed</label>
						<input
							id="combine-seed"
							type="text"
							inputmode="numeric"
							bind:value={randomCombineSeed}
							placeholder="Empty = random each run"
							class="w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
						/>
						{#if combineSeedError}
							<p class="text-xs text-destructive">{combineSeedError}</p>
						{:else}
							<p class="text-xs text-muted-foreground">Binds random word pairs in random case/l33t forms (e.g. <span class="font-mono">NutellaCream2024</span>, <span class="font-mono">cr4amnut3ll4</span>). A seed makes the output reproducible.</p>
						{/if}
					</div>
				</div>
			{/if}
			<ToggleSwitch checked={aiEnabled} onchange={(v) => (aiEnabled = v)} label="AI completions" />
			{#if aiEnabled}
				<div class="ml-12 space-y-1.5">
					<p class="text-xs text-muted-foreground">
						⚠️ Scraped base words are sent to an AI provider. OpenAI is a paid online API — words leave your machine. For fully offline generation, use <span class="font-mono">Ollama</span> (recommended, auto-detected).
					</p>
					<fieldset class="space-y-1.5">
						<legend class="block text-sm font-medium text-foreground">Provider</legend>
						<SegmentedControl
							value={aiProvider}
							onchange={(v) => (aiProvider = v as unknown as 'auto' | 'ollama' | 'openai')}
							options={[{ value: 'auto', label: 'Auto' }, { value: 'ollama', label: 'Ollama' }, { value: 'openai', label: 'OpenAI' }]}
						/>
					</fieldset>
					<div class="space-y-1.5">
						<label for="ai-model" class="block text-sm font-medium text-foreground">Model</label>
						<input
							id="ai-model"
							type="text"
							bind:value={aiModel}
							placeholder="Empty = auto-detect (e.g. llama3.2, gpt-4o-mini)"
							class="w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
						/>
					</div>
					<div class="space-y-1.5">
						<label for="ai-base-url" class="block text-sm font-medium text-foreground">Base URL (optional)</label>
						<input
							id="ai-base-url"
							type="text"
							bind:value={aiBaseUrl}
							placeholder="http://localhost:11434/v1"
							class="w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
						/>
						<p class="text-xs text-muted-foreground">OpenAI-compatible endpoint. Defaults: Ollama <span class="font-mono">http://localhost:11434</span> (offline), OpenAI <span class="font-mono">https://api.openai.com/v1</span>.</p>
					</div>
					<div class="grid grid-cols-2 gap-2">
						<NumberStepper
							value={aiWordsPerWord}
							onchange={(v) => (aiWordsPerWord = v)}
							label="Words per word"
							min={LIMITS.aiWordsPerWord.min}
							max={LIMITS.aiWordsPerWord.max}
						/>
						<NumberStepper
							value={aiMaxWords}
							onchange={(v) => (aiMaxWords = v)}
							label="Max words"
							min={LIMITS.aiMaxWords.min}
							max={LIMITS.aiMaxWords.max}
							step={100}
						/>
					</div>
					<NumberStepper
						value={aiConcurrency}
						onchange={(v) => (aiConcurrency = v)}
						label="Concurrency"
						min={LIMITS.aiConcurrency.min}
						max={LIMITS.aiConcurrency.max}
					/>
					<p class="text-xs text-muted-foreground">Related words become extra base words, then go through all mutations. The API key is never stored — set <span class="font-mono">OPENAI_API_KEY</span> in the environment for the OpenAI provider.</p>
				</div>
			{/if}
			<ToggleSwitch checked={enableReverseLeet} onchange={(v) => { enableReverseLeet = v; if (v) enableLeet = false; }} label="Reverse leet" />
			{#if enableReverseLeet}
				<p class="text-xs text-muted-foreground">Reverse leet converts l33t chars back to letters — it undoes L33t speak, so the two are mutually exclusive.</p>
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
			<AuthField
				cookies={cookies}
				cookieFile={cookieFile}
				sessionState={sessionState}
				onchange={(v) => {
					cookies = v.cookies;
					cookieFile = v.cookieFile;
					sessionState = v.sessionState;
				}}
			/>
			<HttpAuthField
				authType={authType}
				authUser={authUser}
				authPass={authPass}
				onchange={(v) => {
					authType = v.authType;
					authUser = v.authUser;
					authPass = v.authPass;
				}}
			/>
			<StringList
				label="Only scrape paths"
				items={includePaths}
				onchange={(v) => (includePaths = v)}
				placeholder="/docs — press Enter to add"
				hint="Crawl only URLs whose path starts with one of these prefixes."
			/>
			<StringList
				label="Exclude patterns"
				items={excludePatterns}
				onchange={(v) => (excludePatterns = v)}
				placeholder="private — press Enter to add"
				hint="Skip URLs whose path contains any of these substrings."
			/>
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
				<span class="block text-sm font-medium text-foreground">Output format</span>
				<SegmentedControl
					value={ruleFormat ?? 'wordlist'}
					onchange={(v) => (ruleFormat = v === 'wordlist' ? undefined : (v as 'jtr' | 'hashcat'))}
					options={[
						{ value: 'wordlist', label: 'Wordlist' },
						{ value: 'jtr', label: 'JtR rules' },
						{ value: 'hashcat', label: 'Hashcat rules' }
					]}
				/>
				<p class="text-xs text-muted-foreground">
					Rules mode writes a .rules file + base words instead of expanding the wordlist — run the rules against your base words in hashcat/john.
				</p>
			</div>
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
		title="{modLabel()} + Enter to run"
		class="w-full rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
	>
		{#if submitting}
			<span class="flex items-center justify-center gap-2">
				<span class="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent"></span>
				Starting...
			</span>
		{:else}
			<span class="flex items-center justify-center gap-2">
				Generate Wordlist
				<kbd class="rounded bg-primary-foreground/15 px-1.5 py-0.5 text-[10px] font-semibold text-primary-foreground/90">
					{modLabel()}↵
				</kbd>
			</span>
		{/if}
	</button>
</form>
