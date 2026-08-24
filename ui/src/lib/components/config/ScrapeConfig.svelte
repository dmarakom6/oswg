<script lang="ts">
	import UrlInput from './UrlInput.svelte';
	import NumberStepper from './NumberStepper.svelte';
	import ToggleSwitch from './ToggleSwitch.svelte';
	import KeyValueList from './KeyValueList.svelte';
	import { DEFAULTS, LIMITS, RETENTION_OPTIONS } from '$lib/constants';
	import { isValidUrl } from '$lib/utils/validators';
	import { endpoints } from '$lib/api/endpoints';
	import { jobsStore } from '$lib/stores/jobs';
	import { connectJobWs } from '$lib/websocket/job-ws';
	import { notifications } from '$lib/stores/notifications';

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
	let proxy = $state('');
	let useSitemap = $state(false);
	let submitting = $state(false);

	let urlError = $derived(url.length > 0 && !isValidUrl(url) ? 'Enter a valid URL including protocol (https://)' : '');
	let canSubmit = $derived(url.length > 0 && isValidUrl(url) && !submitting);

	async function handleSubmit() {
		if (!canSubmit) return;
		submitting = true;

		try {
			const response = await endpoints.scrape({
				url,
				sitemap: useSitemap,
				max_pages: maxPages,
				timeout,
				respect_robots: respectRobots,
				...((userAgent.trim().length > 0) ? { user_agent: userAgent.trim() } : {}),
				rate_limit: rateLimit,
				jitter,
				headers: Object.fromEntries(headers.filter(h => h.name.trim()).map(h => [h.name.trim(), h.value])),
				cookies: Object.fromEntries(cookies.filter(c => c.name.trim()).map(c => [c.name.trim(), c.value])),
				...((proxy.trim().length > 0) ? { proxy: proxy.trim() } : {}),
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
		<UrlInput value={url} onchange={(v) => (url = v)} error={urlError} />
	</div>

	<div class="space-y-4">
		<h2 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Scope</h2>
		<NumberStepper value={maxPages} onchange={(v) => (maxPages = v)} label="Pages to scrape" min={LIMITS.maxPages.min} max={LIMITS.maxPages.max} />
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
		class="w-full rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
	>
		{#if submitting}
			<span class="flex items-center justify-center gap-2">
				<span class="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent"></span>
				Starting...
			</span>
		{:else}
			Scrape Keywords
		{/if}
	</button>
</form>
