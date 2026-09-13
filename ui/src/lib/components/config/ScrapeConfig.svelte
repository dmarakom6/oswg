<script lang="ts">
	import UrlInput from './UrlInput.svelte';
	import NumberStepper from './NumberStepper.svelte';
	import ToggleSwitch from './ToggleSwitch.svelte';
	import SegmentedControl from './SegmentedControl.svelte';
	import KeyValueList from './KeyValueList.svelte';
	import AuthField from './AuthField.svelte';
	import HttpAuthField from './HttpAuthField.svelte';
	import StringList from './StringList.svelte';
	import { DEFAULTS, LIMITS, RETENTION_OPTIONS } from '$lib/constants';
	import { isValidUrl } from '$lib/utils/validators';
	import { endpoints } from '$lib/api/endpoints';
	import { jobsStore } from '$lib/stores/jobs';
	import { connectJobWs } from '$lib/websocket/job-ws';
	import { notifications } from '$lib/stores/notifications';
	import { jsAvailable } from '$lib/stores/capabilities';
	import { activeTab } from '$lib/stores/tabs';
	import { focusUrlSignal, runSignal } from '$lib/stores/shortcuts';
	import { modLabel } from '$lib/shortcuts';

	let url = $state('');
	let maxPages = $state(DEFAULTS.maxPages);
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
	let useSitemap = $state(false);
	let allowSubdomains = $state(false);
	let includePaths = $state<string[]>([]);
	let excludePatterns = $state<string[]>([]);
	let crawlStrategy = $state<'bfs' | 'dfs'>('bfs');
	let jsRender = $state(false);
	let extractEmails = $state(false);
	let extractUsernames = $state(false);
	let submitting = $state(false);

	let urlError = $derived(url.length > 0 && !isValidUrl(url) ? 'Enter a valid URL including protocol (https://)' : '');
	let canSubmit = $derived(url.length > 0 && isValidUrl(url) && !submitting);

	$effect(() => {
		if ($runSignal > 0 && $activeTab === 'scrape') {
			handleSubmit();
		}
	});

	async function handleSubmit() {
		if (!canSubmit) return;
		submitting = true;

		try {
			const response = await endpoints.scrape({
				url,
				sitemap: useSitemap,
				allow_subdomains: allowSubdomains,
				include_paths: includePaths,
				exclude_patterns: excludePatterns,
				crawl_strategy: crawlStrategy,
				js_render: jsRender,
				extract_emails: extractEmails,
				extract_usernames: extractUsernames,
				max_pages: maxPages,
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
				retention_seconds: retentionSeconds
			});

			jobsStore.upsert({
				job_id: response.job_id,
				type: 'scrape',
				status: 'pending',
				progress: 0,
				created_at: new Date().toISOString(),
				updated_at: new Date().toISOString(),
				completed_at: null,
				error_message: null,
				result_file: null
			});

			jobsStore.setCurrent('scrape', response.job_id);

			connectJobWs(response.job_id, (msg) => {
				jobsStore.upsert({
					job_id: msg.job_id,
					status: msg.status,
					progress: msg.progress
				});
			});

			notifications.add('success', 'Scraping started');
		} catch (err) {
			notifications.add('error', err instanceof Error ? err.message : 'Failed to start scraping');
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
		<NumberStepper value={maxPages} onchange={(v) => (maxPages = v)} label="Pages to scrape" min={LIMITS.maxPages.min} max={LIMITS.maxPages.max} />
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

	<details class="space-y-4">
		<summary class="cursor-pointer text-xs font-semibold uppercase tracking-wider text-muted-foreground select-none hover:text-foreground transition-colors">
			Advanced
		</summary>
		<div class="space-y-1.5 pl-1">
			<ToggleSwitch checked={jsRender} onchange={(v) => (jsRender = v)} label="JavaScript rendering" disabled={!$jsAvailable} />
			{#if !$jsAvailable}
				<p class="text-xs text-muted-foreground">
					Requires the optional dependency. Install with <span class="font-mono">pip install 'oswg[js]'</span> then <span class="font-mono">playwright install chromium</span>.
				</p>
			{:else}
				<p class="text-xs text-muted-foreground">Render pages in a real browser for JS-driven sites. Saves a screenshot per page.</p>
			{/if}
			<ToggleSwitch checked={extractEmails} onchange={(v) => (extractEmails = v)} label="Extract email addresses" />
			<p class="text-xs text-muted-foreground">Include full email addresses found on the target in the output.</p>
			<ToggleSwitch checked={extractUsernames} onchange={(v) => (extractUsernames = v)} label="Extract usernames" />
			<p class="text-xs text-muted-foreground">Save usernames to a separate sidecar list (not merged into the output).</p>
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
				Scrape Keywords
				<kbd class="rounded bg-primary-foreground/15 px-1.5 py-0.5 text-[10px] font-semibold text-primary-foreground/90">
					{modLabel()}↵
				</kbd>
			</span>
		{/if}
	</button>
</form>
