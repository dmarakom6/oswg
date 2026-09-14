<script lang="ts">
	import { endpoints } from '$lib/api/endpoints';
	import SegmentedControl from '../config/SegmentedControl.svelte';
	import CrawlGraph from './CrawlGraph.svelte';
	import CoverageMap from './CoverageMap.svelte';
	import type { CrawlGraph as CrawlGraphType } from '$lib/api/types';

	let { jobId, onclose }: { jobId: string; onclose: () => void } = $props();

	let graph = $state<CrawlGraphType | null>(null);
	let error = $state('');
	let loaded = $state(false);
	let view = $state<'coverage' | 'tree'>('coverage');

	$effect(() => {
		let cancelled = false;
		endpoints.getGraph(jobId)
			.then((g) => {
				if (!cancelled) {
					graph = g;
					loaded = true;
				}
			})
			.catch(() => {
				if (!cancelled) {
					error = 'Crawl graph unavailable';
					loaded = true;
				}
			});
		return () => {
			cancelled = true;
		};
	});
</script>

<svelte:window onkeydown={(e) => { if (e.key === 'Escape') onclose(); }} />

<div
	class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
	role="presentation"
	onclick={(e) => {
		if (e.target === e.currentTarget) onclose();
	}}
>
	<div
		class="flex h-[85vh] w-[min(1100px,95vw)] flex-col overflow-hidden rounded-lg border border-border bg-background shadow-xl"
		role="dialog"
		tabindex="-1"
		aria-modal="true"
		aria-label="Visualizations"
	>
		<div class="flex items-center justify-between border-b border-border px-4 py-3">
			<h2 class="text-sm font-semibold text-foreground">Visualizations</h2>
			<button
				type="button"
				onclick={onclose}
				class="rounded p-1 text-muted-foreground transition-colors hover:text-foreground"
				aria-label="Close visualizations"
				title="Close (Esc)"
			>✕</button>
		</div>

		{#if graph}
			<div class="flex justify-center border-b border-border py-2">
				<SegmentedControl
					value={view}
					onchange={(v) => (view = v as 'coverage' | 'tree')}
					options={[
						{ value: 'coverage', label: 'Coverage' },
						{ value: 'tree', label: 'Tree' }
					]}
				/>
			</div>
			<div class="flex-1 overflow-auto p-4">
				{#if view === 'coverage'}
					<CoverageMap {graph} />
				{:else}
					<CrawlGraph {jobId} {graph} />
				{/if}
			</div>
		{:else if error}
			<div class="flex flex-1 items-center justify-center p-4">
				<p class="text-sm text-destructive">{error}</p>
			</div>
		{:else}
			<div class="flex flex-1 items-center justify-center p-4">
				<p class="text-sm text-muted-foreground">Loading crawl graph…</p>
			</div>
		{/if}
	</div>
</div>