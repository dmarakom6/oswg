<script lang="ts">
	import { endpoints } from '$lib/api/endpoints';
	import SegmentedControl from '../config/SegmentedControl.svelte';
	import CrawlGraph from './CrawlGraph.svelte';
	import CoverageMap from './CoverageMap.svelte';
	import KeywordCloud from './KeywordCloud.svelte';
	import FrequencyChart from './FrequencyChart.svelte';
	import MutationTreeView from './MutationTreeView.svelte';
	import type { CrawlGraph as CrawlGraphType, MutationTree, WordCounts } from '$lib/api/types';

	let { jobId, onclose }: { jobId: string; onclose: () => void } = $props();

	let graph = $state<CrawlGraphType | null>(null);
	let wordCounts = $state<WordCounts | null>(null);
	let mutationTree = $state<MutationTree | null>(null);
	let graphError = $state(false);
	let wordsError = $state(false);
	let view = $state<'coverage' | 'tree' | 'cloud' | 'frequencies' | 'mutations'>('coverage');

	$effect(() => {
		let cancelled = false;
		endpoints
			.getGraph(jobId)
			.then((g) => {
				if (!cancelled) graph = g;
			})
			.catch(() => {
				if (!cancelled) graphError = true;
			});
		endpoints
			.getWordCounts(jobId)
			.then((w) => {
				if (!cancelled) wordCounts = w;
			})
			.catch(() => {
				if (!cancelled) wordsError = true;
			});
		endpoints
			.getMutationTree(jobId)
			.then((t) => {
				if (!cancelled) mutationTree = t;
			})
			.catch(() => {
				// only generate jobs have a mutation tree
			});
		return () => {
			cancelled = true;
		};
	});

	const options = $derived.by(() => {
		const opts: { value: string; label: string }[] = [];
		if (graph) opts.push({ value: 'coverage', label: 'Coverage' }, { value: 'tree', label: 'Tree' });
		if (wordCounts?.words?.length) opts.push({ value: 'cloud', label: 'Cloud' }, { value: 'frequencies', label: 'Frequencies' });
		if (mutationTree && Object.keys(mutationTree.tree).length) opts.push({ value: 'mutations', label: 'Mutations' });
		return opts;
	});

	$effect(() => {
		if (options.length && !options.some((o) => o.value === view)) {
			view = options[0].value as typeof view;
		}
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

		{#if options.length > 1}
			<div class="flex justify-center border-b border-border py-2">
				<SegmentedControl
					value={view}
					onchange={(v) => (view = v as 'coverage' | 'tree' | 'cloud' | 'frequencies' | 'mutations')}
					{options}
				/>
			</div>
		{/if}

		<div class="flex-1 overflow-auto p-4">
			{#if options.length === 0}
				<div class="flex h-full items-center justify-center">
					<p class="text-sm text-muted-foreground">
						{#if graphError && wordsError}
							No visualization data available for this job.
						{:else}
							Loading…
						{/if}
					</p>
				</div>
			{:else if view === 'coverage'}
				<CoverageMap {graph} />
			{:else if view === 'tree'}
				<CrawlGraph {jobId} {graph} />
			{:else if view === 'frequencies'}
				<FrequencyChart words={wordCounts?.words ?? []} />
			{:else if view === 'mutations' && mutationTree}
				<MutationTreeView tree={mutationTree} />
			{:else}
				<KeywordCloud words={wordCounts?.words ?? []} />
			{/if}
		</div>
	</div>
</div>