<script lang="ts">
	import { currentJobForTab, jobsStore } from '$lib/stores/jobs';
	import { endpoints } from '$lib/api/endpoints';
	import { notifications } from '$lib/stores/notifications';
	import type { ActiveTab } from '$lib/api/types';

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
	let preview = $state<{ words: string[]; total: number; truncated: boolean } | null>(null);

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
					completed_at: job.completed_at
				});
				if (job.status === 'completed') {
					stopPolling();
					const result = await endpoints.previewJob(jobId);
					preview = { words: result.preview, total: result.total_words, truncated: result.truncated };
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
		scrape: ['Connecting', 'Scraping website', 'Processing keywords', 'Saving results', 'Finalizing']
	};

	function getStepIndex(progress: number, type: string): number {
		const total = steps[type as keyof typeof steps]?.length ?? 5;
		return Math.min(Math.floor((progress / 100) * total), total - 1);
	}

	async function downloadJob(jobId: string) {
		try {
			const { blob, filename } = await endpoints.downloadJob(jobId);
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = filename;
			a.click();
			URL.revokeObjectURL(url);
		} catch {
			notifications.add('error', 'Download failed');
		}
	}

	function copyToClipboard(text: string) {
		navigator.clipboard.writeText(text).then(() => {
			notifications.add('success', 'Copied to clipboard');
		});
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
					onclick={() => {
						const blob = new Blob([mutateResult.words.join('\n')], { type: 'text/plain' });
						const url = URL.createObjectURL(blob);
						const a = document.createElement('a');
						a.href = url;
						a.download = 'oswg_mutations.txt';
						a.click();
						URL.revokeObjectURL(url);
					}}
					class="flex-1 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:opacity-90"
				>
					Download .txt
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
				<span class="font-mono text-sm text-muted-foreground">{Math.round(currentJob.progress)}%</span>
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
			<div class="mt-auto flex flex-col gap-3 border-t border-border pt-4" style="animation: fade-in 300ms ease">
				{#if preview}
					<div>
						<div class="mb-2 flex items-center justify-between">
							<span class="text-xs font-medium text-foreground">Preview</span>
							<span class="text-xs text-muted-foreground">
								{preview.words.length} of {preview.total} words
								{#if preview.truncated}
									<span class="text-muted-foreground/60"> · showing first 200</span>
								{/if}
							</span>
						</div>
						<div class="max-h-48 overflow-y-auto rounded-md border border-border bg-muted/30 p-2">
							<div class="font-mono text-xs leading-relaxed text-foreground">
								{#each preview.words as word}
									<div>{word}</div>
								{/each}
							</div>
						</div>
					</div>
				{/if}
				<button
					onclick={() => downloadJob(currentJob.job_id)}
					class="w-full rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:opacity-90"
				>
					Download Wordlist
				</button>
			</div>
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

<style>
	@keyframes fade-in {
		from { opacity: 0; transform: translateY(4px); }
		to { opacity: 1; transform: translateY(0); }
	}
</style>
