<script lang="ts">
	import GenerateConfig from '$lib/components/config/GenerateConfig.svelte';
	import ScrapeConfig from '$lib/components/config/ScrapeConfig.svelte';
	import MutateConfig from '$lib/components/config/MutateConfig.svelte';
	import TestConfig from '$lib/components/config/TestConfig.svelte';
	import OutputPanel from '$lib/components/output/OutputPanel.svelte';
	import RecentWordlists from '$lib/components/RecentWordlists.svelte';
	import SegmentedControl from '$lib/components/config/SegmentedControl.svelte';
	import { activeTab } from '$lib/stores/tabs';
	import { jobsStore } from '$lib/stores/jobs';

	let mutateResult = $state<{ words: string[]; count: number; source_count: number } | null>(null);

	const STORAGE_KEY = 'oswg-left-pane-width';
	const MIN_WIDTH = 20;
	const MAX_WIDTH = 60;

	let leftWidth = $state(40);
	let containerRef = $state<HTMLDivElement | null>(null);
	let dragging = $state(false);
	let isDesktop = $state(true);
	let mobileView = $state<'config' | 'results'>('config');

	$effect(() => {
		const mq = window.matchMedia('(min-width: 1024px)');
		isDesktop = mq.matches;
		const onChange = (e: MediaQueryListEvent) => (isDesktop = e.matches);
		mq.addEventListener('change', onChange);
		return () => mq.removeEventListener('change', onChange);
	});

	// On mobile, jump to the Results view when a new job starts.
	$effect(() => {
		const seen = new Set<string>();
		return jobsStore.subscribe((jobs) => {
			for (const job of jobs.values()) {
				if (seen.has(job.job_id)) continue;
				seen.add(job.job_id);
				if (!isDesktop && (job.status === 'pending' || job.status === 'processing')) {
					mobileView = 'results';
				}
			}
		});
	});

	function loadSavedWidth() {
		try {
			const saved = localStorage.getItem(STORAGE_KEY);
			if (saved !== null) {
				leftWidth = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, Number(saved)));
			}
		} catch {
			// localStorage unavailable; keep default
		}
	}

	function startDrag(e: PointerEvent) {
		e.preventDefault();
		dragging = true;
	}

	function onPointerMove(e: PointerEvent) {
		if (!dragging || !containerRef) return;
		const rect = containerRef.getBoundingClientRect();
		const percent = ((e.clientX - rect.left) / rect.width) * 100;
		leftWidth = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, percent));
	}

	function endDrag() {
		if (!dragging) return;
		dragging = false;
		try {
			localStorage.setItem(STORAGE_KEY, String(leftWidth));
		} catch {
			// ignore persistence failures
		}
	}

	loadSavedWidth();
</script>

<div
	bind:this={containerRef}
	class="relative flex flex-1 flex-col overflow-hidden lg:flex-row"
	role="presentation"
	onpointermove={onPointerMove}
	onpointerup={endDrag}
	onpointerleave={endDrag}
>
	<div class="border-b border-border p-2 lg:hidden">
		<SegmentedControl
			value={mobileView}
			onchange={(v) => (mobileView = v as 'config' | 'results')}
			options={[
				{ value: 'config', label: 'Configure' },
				{ value: 'results', label: 'Results' }
			]}
		/>
	</div>

	<section
		class="flex flex-col overflow-hidden lg:border-r lg:border-border"
		class:cursor-col-resize={dragging}
		class:hidden={!isDesktop && mobileView !== 'config'}
		style:width={isDesktop ? `${leftWidth}%` : '100%'}
	>
		<div class="flex-1 overflow-y-auto p-4 lg:p-6" aria-label="Configuration">
			<div class:hidden={$activeTab !== 'generate'}>
				<GenerateConfig />
			</div>
			<div class:hidden={$activeTab !== 'scrape'}>
				<ScrapeConfig />
			</div>
			<div class:hidden={$activeTab !== 'mutate'}>
				<MutateConfig onResult={(r) => (mutateResult = r)} />
			</div>
			<div class:hidden={$activeTab !== 'test'}>
				<TestConfig />
			</div>
		</div>
		<RecentWordlists />
	</section>

	<div
		onpointerdown={startDrag}
		class="group absolute inset-y-0 hidden w-1 cursor-col-resize lg:block"
		style:left={`calc(${leftWidth}% - 2px)`}
		role="separator"
		aria-orientation="vertical"
		aria-label="Resize config pane"
	>
		<div class="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-border transition-colors group-hover:bg-primary group-active:bg-primary"></div>
	</div>

	<section
		class="flex flex-1 flex-col overflow-y-auto p-4 lg:p-6"
		class:hidden={!isDesktop && mobileView !== 'results'}
		aria-label="Output"
	>
		<OutputPanel activeTab={$activeTab} {mutateResult} />
	</section>
</div>