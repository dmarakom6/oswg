<script lang="ts">
	import UrlInput from './UrlInput.svelte';
	import NumberStepper from './NumberStepper.svelte';
	import ToggleSwitch from './ToggleSwitch.svelte';
	import SegmentedControl from './SegmentedControl.svelte';
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
	let enableNumbers = $state(DEFAULTS.enableNumbers);
	let enableSpecial = $state(DEFAULTS.enableSpecial);
	let leetLevel = $state<1 | 2>(DEFAULTS.leetLevel);
	let retentionSeconds = $state(DEFAULTS.retentionSeconds);
	let useSitemap = $state(false);
	let deduplicate = $state(true);
	let advancedOpen = $state(false);
	let submitting = $state(false);

	let urlError = $derived(url.length > 0 && !isValidUrl(url) ? 'Enter a valid URL including protocol (https://)' : '');
	let canSubmit = $derived(url.length > 0 && isValidUrl(url) && !submitting);

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
				enable_numbers: enableNumbers,
				enable_special: enableSpecial,
				leet_level: leetLevel,
				deduplicate,
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
