<script lang="ts">
	import { endpoints } from '$lib/api/endpoints';
	import { notifications } from '$lib/stores/notifications';
	import type { JobListItem } from '$lib/api/types';

	let recentJobs = $state<JobListItem[]>([]);
	let loading = $state(false);
	let expanded = $state(false);

	const MAX_VISIBLE = 3;

	async function loadJobs() {
		loading = true;
		try {
			recentJobs = await endpoints.listJobs();
		} catch {
			notifications.add('error', 'Failed to load recent wordlists');
		} finally {
			loading = false;
		}
	}

	async function clearAll() {
		try {
			await endpoints.clearJobs();
			recentJobs = [];
			notifications.add('success', 'Cleared all wordlists');
		} catch {
			notifications.add('error', 'Failed to clear wordlists');
		}
	}

	function formatTtl(seconds: number): string {
		if (seconds < 60) return `${seconds}s`;
		if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
		return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
	}

	function formatFileSize(bytes: number | null): string {
		if (!bytes) return '—';
		if (bytes >= 1_048_576) return `${(bytes / 1_048_576).toFixed(1)} MB`;
		if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${bytes} B`;
	}

	function formatTime(iso: string): string {
		return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
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

	const visibleJobs = $derived(expanded ? recentJobs : recentJobs.slice(0, MAX_VISIBLE));

	loadJobs();
</script>

<div class="border-t border-border bg-card">
	<button
		onclick={() => (expanded = !expanded)}
		class="flex w-full items-center justify-between px-4 py-3 text-left transition-colors hover:bg-muted/50"
	>
		<h3 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
			Recent Wordlists
			<span class="ml-2 font-normal normal-case text-muted-foreground/60">
				({recentJobs.length})
			</span>
		</h3>
		<span class="text-muted-foreground transition-transform {expanded ? 'rotate-180' : ''}">
			▾
		</span>
	</button>

	{#if expanded}
		<div class="border-t border-border">
			<div class="max-h-64 overflow-y-auto px-4 py-3">
				{#if recentJobs.length === 0}
					<p class="text-sm text-muted-foreground">No recent wordlists.</p>
				{:else}
					<div class="space-y-2">
						{#each visibleJobs as job}
							<div
								class="flex items-center justify-between rounded-md border border-border bg-background px-3 py-2 transition-colors hover:bg-muted/50"
							>
								<div class="flex items-center gap-3">
									<span
										class="h-2 w-2 rounded-full
										{job.status === 'completed' ? 'bg-success' : job.status === 'failed' ? 'bg-destructive' : 'bg-primary animate-pulse'}"
									></span>
									<div>
										<p class="font-mono text-xs text-foreground">{job.type}</p>
										<p class="text-xs text-muted-foreground">{formatTime(job.created_at)}</p>
									</div>
								</div>
								<div class="flex items-center gap-4">
									<div class="text-right">
										<p class="font-mono text-xs text-foreground">
											{formatFileSize(job.file_size_bytes)}
										</p>
										<p class="text-xs text-muted-foreground">
											TTL: {formatTtl(job.ttl_seconds)}
										</p>
									</div>
									{#if job.status === 'completed'}
										<button
											onclick={() => downloadJob(job.job_id)}
											class="rounded border border-border px-2 py-1 text-xs text-foreground transition-colors hover:bg-accent"
										>
											Download
										</button>
									{/if}
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>

			<div class="flex items-center justify-between border-t border-border px-4 py-2">
				<span class="text-xs text-muted-foreground">
					{recentJobs.length} job{recentJobs.length !== 1 ? 's' : ''} stored
				</span>
				<div class="flex gap-2">
					<button
						onclick={loadJobs}
						disabled={loading}
						class="text-xs text-muted-foreground transition-colors hover:text-foreground disabled:opacity-40"
					>
						↻ Refresh
					</button>
					<button
						onclick={clearAll}
						disabled={recentJobs.length === 0}
						class="text-xs text-destructive transition-colors hover:text-destructive/80 disabled:opacity-40"
					>
						Clear All
					</button>
				</div>
			</div>
		</div>
	{/if}
</div>
