<script lang="ts">
	import { currentJobForTab, jobsStore } from '$lib/stores/jobs';
	import { endpoints } from '$lib/api/endpoints';
	import VisualizeModal from './VisualizeModal.svelte';
	import SegmentedControl from '../config/SegmentedControl.svelte';
	import ToggleSwitch from '../config/ToggleSwitch.svelte';
	import type { ActiveTab, DownloadFormat, JobPreviewResult } from '$lib/api/types';

	let {
		activeTab,
		mutateResult = null
	}: {
		activeTab: ActiveTab;
		mutateResult?: { words: string[]; count: number; source_count: number } | null;
	} = $props();

	const POLL_INTERVAL_MS = 2000;

	let currentJob = $derived($currentJobForTab(activeTab));

	let pollTimer: ReturnType<typeof setInterval> | null = null;
	let pollJobId: string | null = null;
	let preview = $state<JobPreviewResult | null>(null);
	let viewingScreenshot = $state<number | null>(null);
	let visualizeOpen = $state(false);
	let downloadFormat = $state<DownloadFormat>('txt');
	let downloadGzip = $state(false);
	const screenshotUrl = (jobId: string, page: number) => `/api/v1/jobs/${jobId}/screenshot?page=${page}`;

	function startPolling(jobId: string) {
		if (pollJobId === jobId && pollTimer) return;
		stopPolling();
		pollJobId = jobId;
		preview = null;
		pollTimer = setInterval(async () => {
			try {
				const job = await endpoints.getJobStatus(jobId);
				jobsStore.upsert({
					job_id: job.job_id,
					status: job.status,
					progress: job.progress,
					error_message: job.error_message,
					result_file: job.result_file,
					completed_at: job.completed_at,
					words_count: job.words_count,
					source_keywords: job.source_keywords,
					truncated_count: job.truncated_count,
					rule_format: job.rule_format,
					crawl_strategy: job.crawl_strategy,
					screenshot_count: job.screenshot_count,
					email_count: job.email_count,
					username_count: job.username_count
				});
				if (job.status === 'completed') {
					stopPolling();
					preview = await endpoints.previewJob(jobId);
				} else if (job.status === 'failed') {
					stopPolling();
				}
			} catch {
				stopPolling();
			}
		}, POLL_INTERVAL_MS);
	}

	function stopPolling() {
		if (pollTimer) {
			clearInterval(pollTimer);
			pollTimer = null;
			pollJobId = null;
		}
	}

	$effect(() => {
		if (currentJob && (currentJob.status === 'pending' || currentJob.status === 'processing')) {
			startPolling(currentJob.job_id);
		} else if (!currentJob) {
			stopPolling();
			preview = null;
		}
	});

	const steps = {
		generate: ['Connecting', 'Scraping website', 'Generating mutations', 'Saving wordlist', 'Finalizing'],
		scrape: ['Connecting', 'Scraping website', 'Processing keywords', 'Saving results', 'Finalizing'],
		test: ['Preparing inputs', 'Running tool', 'Saving results', 'Finalizing']
	};

	function getStepIndex(progress: number, type: string): number {
		const total = steps[type as keyof typeof steps]?.length ?? 5;
		return Math.min(Math.floor((progress / 100) * total), total - 1);
	}

	async function downloadJob(
		jobId: string,
		target: 'rules' | 'base' | 'wordlist' | 'usernames' = 'wordlist',
		format: DownloadFormat = 'txt',
		gzip = false
	) {
		try {
			const { blob, filename } = await endpoints.downloadJob(jobId, target, format, gzip);
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = filename;
			a.click();
			URL.revokeObjectURL(url);
		} catch {
		}
	}

	function downloadMutateResult(format: DownloadFormat) {
		if (!mutateResult) return;
		let payload: string;
		const metadata = {
			generator: 'oswg',
			created_at: new Date().toISOString(),
			stats: { mutations_count: mutateResult.count, source_count: mutateResult.source_count }
		};
		if (format === 'json') {
			payload = JSON.stringify({ metadata, words: mutateResult.words }, null, 2) + '\n';
		} else if (format === 'csv') {
			const escape = (value: string) =>
				/[",\n\r]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value;
			payload = ['word', ...mutateResult.words.map(escape)].join('\n') + '\n';
		} else {
			payload = mutateResult.words.join('\n') + '\n';
		}
		const blob = new Blob([payload], { type: 'text/plain' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `oswg_mutations.${format}`;
		a.click();
		URL.revokeObjectURL(url);
	}

	function copyToClipboard(text: string) {
		navigator.clipboard.writeText(text);
	}
</script>

{#if activeTab === 'mutate'}
	{#if mutateResult}
		<div class="flex flex-1 flex-col gap-4" style="animation: fade-in 200ms ease">
			<div class="flex items-baseline gap-2">
				<span class="text-2xl font-semibold text-foreground">{mutateResult.count}</span>
				<span class="text-sm text-muted-foreground">mutations from {mutateResult.source_count} words</span>
			</div>

			<div class="flex items-center gap-2 text-xs text-muted-foreground">
				<span>Expansion:</span>
				<span class="font-mono font-medium text-foreground">
					{(mutateResult.count / mutateResult.source_count).toFixed(1)}x
				</span>
			</div>

			<div class="max-h-80 overflow-y-auto rounded-md border border-border bg-muted/30 p-3">
				<div class="font-mono text-xs leading-relaxed text-foreground">
					{#each mutateResult.words.slice(0, 200) as word}
						<div>{word}</div>
					{/each}
					{#if mutateResult.words.length > 200}
						<div class="pt-2 text-muted-foreground">...{mutateResult.words.length - 200} more</div>
					{/if}
				</div>
			</div>

			<div class="flex gap-2">
				<button
					onclick={() => copyToClipboard(mutateResult.words.join('\n'))}
					class="flex-1 rounded-md border border-border px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
				>
					Copy All
				</button>
				<button
					onclick={() => downloadMutateResult('txt')}
					class="flex-1 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:opacity-90"
				>
					Download .txt
				</button>
				<button
					onclick={() => downloadMutateResult('json')}
					class="rounded-md border border-border px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
				>
					.json
				</button>
				<button
					onclick={() => downloadMutateResult('csv')}
					class="rounded-md border border-border px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
				>
					.csv
				</button>
			</div>
		</div>
	{:else}
		<div class="flex flex-1 items-center justify-center">
			<div class="text-center text-muted-foreground">
				<p class="text-lg">◇</p>
				<p class="mt-2 text-sm">Enter words and click Mutate to see results.</p>
			</div>
		</div>
	{/if}
{:else if currentJob}
	{@const jobSteps = steps[currentJob.type as keyof typeof steps] ?? steps.generate}
	{@const stepIndex = getStepIndex(currentJob.progress, currentJob.type)}
	{@const isDone = currentJob.status === 'completed' || currentJob.status === 'failed'}

	<div class="flex flex-1 flex-col gap-6" style="animation: fade-in 200ms ease">
		<div>
			<div class="mb-2 flex items-center justify-between">
				<span class="text-sm font-medium text-foreground">
					{isDone ? (currentJob.status === 'completed' ? 'Complete' : 'Failed') : 'Processing'}
				</span>
				<div class="flex items-center gap-3">
					{#if currentJob.status === 'completed' && (currentJob.type === 'generate' || currentJob.type === 'scrape')}
						<button
							type="button"
							onclick={() => (visualizeOpen = true)}
							class="rounded-md border border-border px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:bg-accent"
						>
							Visualize
						</button>
					{/if}
					<span class="font-mono text-sm text-muted-foreground">{Math.round(currentJob.progress)}%</span>
				</div>
			</div>

			<div class="h-2 overflow-hidden rounded-full bg-muted">
				<div
					class="h-full rounded-full transition-all duration-700 ease-out
						{currentJob.status === 'completed' ? 'bg-success' : currentJob.status === 'failed' ? 'bg-destructive' : 'bg-primary'}"
					style="width: {currentJob.progress}%"
				></div>
			</div>
		</div>

		<div class="space-y-2">
			{#each jobSteps as step, i}
				<div class="flex items-center gap-3">
					{#if i < stepIndex || isDone}
						<span class="text-success">✓</span>
					{:else if i === stepIndex}
						<span class="text-primary animate-pulse">●</span>
					{:else}
						<span class="text-muted-foreground">○</span>
					{/if}
					<span class="text-sm {i <= stepIndex ? 'text-foreground' : 'text-muted-foreground'}">
						{step}
					</span>
				</div>
			{/each}
		</div>

		{#if currentJob.status === 'completed'}
			{#if currentJob.type === 'test'}
				{#if preview && preview.mode === 'test'}
					<div class="flex flex-col gap-3" style="animation: fade-in 300ms ease">
						<div class="flex items-baseline justify-between">
							<span class="text-sm font-medium text-foreground">
								{preview.tool} result
							</span>
							<span class="font-mono text-xs text-muted-foreground">
								{preview.found} found
							</span>
						</div>
						{#if preview.entries.length > 0}
							<div class="max-h-72 overflow-y-auto rounded-md border border-border bg-muted/30 p-2">
								{#each preview.entries as entry (entry.hash ?? entry.user ?? entry.path ?? entry.key)}
									<div class="flex items-center justify-between gap-2 py-0.5 font-mono text-xs">
										<span class="truncate text-muted-foreground">
											{entry.hash ?? entry.user ?? entry.path ?? 'key'}
										</span>
										<span class="shrink-0 text-primary">
											{entry.password ?? entry.status ?? entry.key}
										</span>
									</div>
								{/each}
							</div>
						{:else}
							<p class="text-xs text-muted-foreground">No results found.</p>
						{/if}
					</div>
				{/if}
			{:else}
			{#if currentJob.screenshot_count && currentJob.screenshot_count > 0}
				<div class="space-y-2">
					<div class="flex items-center justify-between">
						<span class="text-xs font-medium text-foreground">Rendered pages</span>
						<span class="text-xs text-muted-foreground">{currentJob.screenshot_count} screenshot{currentJob.screenshot_count !== 1 ? 's' : ''}</span>
					</div>
					<div class="flex gap-2 overflow-x-auto pb-1">
						{#each Array(currentJob.screenshot_count) as _, i}
							<button
								type="button"
								onclick={() => (viewingScreenshot = i)}
								class="shrink-0 rounded-md border border-border p-0.5 transition-colors hover:border-primary"
								aria-label="View screenshot {i + 1}"
							>
								<img
									src={screenshotUrl(currentJob.job_id, i)}
									alt="Rendered page {i + 1}"
									class="h-16 w-24 object-cover rounded"
									loading="lazy"
								/>
							</button>
						{/each}
					</div>
				</div>
			{/if}
			{#if preview?.mode === 'rules'}
				<div class="flex flex-col gap-3" style="animation: fade-in 300ms ease">
					<div class="flex items-baseline justify-between">
						<span class="text-sm font-medium text-foreground">
							{preview.format === 'hashcat' ? 'Hashcat' : 'JtR'} rules
						</span>
						<span class="font-mono text-xs text-muted-foreground">
							{preview.rules_total} rules
						</span>
					</div>
					<div class="max-h-48 overflow-y-auto rounded-md border border-border bg-muted/30 p-2 font-mono text-xs leading-relaxed text-primary">
						{#each preview.rules as rule}
							<div>{rule}</div>
						{/each}
						{#if preview.rules_truncated}
							<div class="pt-1 text-muted-foreground">...{preview.rules_total - preview.rules.length} more rules</div>
						{/if}
					</div>
					<div class="flex items-baseline justify-between">
						<span class="text-sm font-medium text-foreground">Base words</span>
						<span class="font-mono text-xs text-muted-foreground">
							{preview.base_total} words
						</span>
					</div>
					<div class="max-h-32 overflow-y-auto rounded-md border border-border bg-muted/30 p-2 font-mono text-xs leading-relaxed text-foreground">
						{#each preview.base_words as word}
							<div>{word}</div>
						{/each}
						{#if preview.base_truncated}
							<div class="pt-1 text-muted-foreground">...{preview.base_total - preview.base_words.length} more</div>
						{/if}
					</div>
					<div class="rounded-md border border-border bg-muted/20 px-3 py-2 font-mono text-[11px] leading-relaxed text-muted-foreground">
						<p class="text-foreground">Saved files</p>
						<p>rules: {preview.rules_path}</p>
						<p>base: {preview.base_path}</p>
					</div>
					<div class="flex items-center justify-between gap-2">
						<ToggleSwitch checked={downloadGzip} onchange={(v) => (downloadGzip = v)} label="gzip" />
						<div class="flex gap-2">
							<button
								onclick={() => downloadJob(currentJob.job_id, 'rules', 'txt', downloadGzip)}
								class="rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:opacity-90"
							>
								Download Rules
							</button>
							<button
								onclick={() => downloadJob(currentJob.job_id, 'base', 'txt', downloadGzip)}
								class="rounded-md border border-border px-4 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-accent"
							>
								Download Base Words
							</button>
						</div>
					</div>
				</div>
			{:else if preview && preview.mode === 'wordlist'}
				<div class="mt-auto flex flex-col gap-3 border-t border-border pt-4" style="animation: fade-in 300ms ease">
					<div>
						<div class="mb-2 flex items-center justify-between">
							<span class="text-xs font-medium text-foreground">Preview</span>
							<span class="text-xs text-muted-foreground">
								{preview.preview.length} of {preview.total_words} words
								{#if preview.truncated}
									<span class="text-muted-foreground/60"> · showing first 200</span>
								{/if}
							</span>
						</div>
						<div class="max-h-48 overflow-y-auto rounded-md border border-border bg-muted/30 p-2">
							<div class="font-mono text-xs leading-relaxed text-foreground">
								{#each preview.preview as word}
									<div>{word}</div>
								{/each}
							</div>
						</div>
					</div>
					{#if currentJob.truncated_count && currentJob.truncated_count > 0}
						<div class="rounded-md border border-amber-500/30 bg-amber-500/10 p-3">
							<p class="text-xs text-amber-700 dark:text-amber-400">
								⚠ Truncated {currentJob.truncated_count.toLocaleString()} mutations to reach the target size.
							</p>
						</div>
					{/if}
					{#if currentJob.email_count && currentJob.email_count > 0}
						<p class="text-xs text-muted-foreground">
							{currentJob.email_count} email address{currentJob.email_count !== 1 ? 'es' : ''} found and included in the wordlist.
						</p>
					{/if}
					{#if currentJob.username_count && currentJob.username_count > 0}
						<div class="space-y-2">
							<div class="flex items-center justify-between">
								<span class="text-xs font-medium text-foreground">Usernames</span>
								<span class="text-xs text-muted-foreground">
									{currentJob.username_count} username{currentJob.username_count !== 1 ? 's' : ''} · separate list
								</span>
							</div>
							{#if preview?.usernames?.length}
								<div class="max-h-28 overflow-y-auto rounded-md border border-border bg-muted/30 p-2 font-mono text-xs leading-relaxed text-foreground">
									{#each preview.usernames as user}
										<div>{user}</div>
									{/each}
								</div>
							{/if}
							<button
								onclick={() => downloadJob(currentJob.job_id, 'usernames', 'txt', downloadGzip)}
								class="w-full rounded-md border border-border px-4 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-accent"
							>
								Download Usernames
							</button>
						</div>
					{/if}
					<div class="flex items-center justify-between gap-2">
						<SegmentedControl
							value={downloadFormat}
							onchange={(v) => (downloadFormat = v as DownloadFormat)}
							options={[
								{ value: 'txt', label: 'TXT' },
								{ value: 'json', label: 'JSON' },
								{ value: 'csv', label: 'CSV' }
							]}
						/>
						<ToggleSwitch checked={downloadGzip} onchange={(v) => (downloadGzip = v)} label="gzip" />
					</div>
					<button
						onclick={() => downloadJob(currentJob.job_id, 'wordlist', downloadFormat, downloadGzip)}
						class="w-full rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:opacity-90"
					>
						Download Wordlist
					</button>
				</div>
			{/if}
			{/if}
		{:else if currentJob.status === 'failed'}
			<div class="mt-auto flex flex-col gap-3 border-t border-border pt-4" style="animation: fade-in 300ms ease">
				<div class="rounded-md border border-destructive/30 bg-destructive/10 p-3">
					<p class="text-sm text-destructive">{currentJob.error_message ?? 'Job failed'}</p>
				</div>
			</div>
		{/if}
	</div>
{:else}
	<div class="flex flex-1 items-center justify-center">
		<div class="text-center text-muted-foreground">
			<p class="text-lg">◇</p>
			<p class="mt-2 text-sm">
				Configure options and click {activeTab === 'generate' ? 'Generate' : 'Scrape'} to start.
			</p>
		</div>
	</div>
{/if}

{#if viewingScreenshot !== null && currentJob}
	{@const page = viewingScreenshot}
	{@const total = currentJob.screenshot_count ?? 0}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-6"
		role="presentation"
		onclick={() => (viewingScreenshot = null)}
		onkeydown={(e) => {
			if (e.key === 'Escape') viewingScreenshot = null;
		}}
	>
		<div
			class="flex max-h-full flex-col gap-3 rounded-lg border border-border bg-background p-4"
			role="presentation"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
		>
			<div class="flex items-center justify-between gap-6">
				<span class="text-xs font-medium text-foreground">Rendered page {page + 1} of {total}</span>
				<button
					type="button"
					onclick={() => (viewingScreenshot = null)}
					class="rounded p-1 text-muted-foreground transition-colors hover:text-foreground"
					aria-label="Close screenshot"
				>✕</button>
			</div>
			<img
				src={screenshotUrl(currentJob.job_id, page)}
				alt="Rendered page {page + 1}"
				class="max-h-[70vh] max-w-[80vw] rounded"
			/>
			<div class="flex items-center justify-center gap-2">
				<button
					type="button"
					disabled={page === 0}
					onclick={() => (viewingScreenshot = page - 1)}
					class="rounded border border-border px-3 py-1 text-xs text-foreground transition-colors hover:bg-accent disabled:opacity-40"
				>← Prev</button>
				<button
					type="button"
					disabled={page >= total - 1}
					onclick={() => (viewingScreenshot = page + 1)}
					class="rounded border border-border px-3 py-1 text-xs text-foreground transition-colors hover:bg-accent disabled:opacity-40"
				>Next →</button>
			</div>
		</div>
	</div>
{/if}

{#if visualizeOpen && currentJob}
	<VisualizeModal jobId={currentJob.job_id} onclose={() => (visualizeOpen = false)} />
{/if}

<style>
	@keyframes fade-in {
		from { opacity: 0; transform: translateY(4px); }
		to { opacity: 1; transform: translateY(0); }
	}
</style>
