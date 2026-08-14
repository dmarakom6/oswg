<script lang="ts">
	import GenerateConfig from '$lib/components/config/GenerateConfig.svelte';
	import ScrapeConfig from '$lib/components/config/ScrapeConfig.svelte';
	import MutateConfig from '$lib/components/config/MutateConfig.svelte';
	import OutputPanel from '$lib/components/output/OutputPanel.svelte';
	import RecentWordlists from '$lib/components/RecentWordlists.svelte';
	import { activeTab } from '$lib/stores/tabs';

	let mutateResult = $state<{ words: string[]; count: number; source_count: number } | null>(null);

	const STORAGE_KEY = 'oswg-left-pane-width';
	const MIN_WIDTH = 20;
	const MAX_WIDTH = 60;

	let leftWidth = $state(40);
	let containerRef = $state<HTMLDivElement | null>(null);
	let dragging = $state(false);

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
	class="relative flex flex-1 overflow-hidden"
	role="presentation"
	onpointermove={onPointerMove}
	onpointerup={endDrag}
	onpointerleave={endDrag}
>
	<section
		class="flex flex-col overflow-hidden border-r border-border"
		class:cursor-col-resize={dragging}
		style:width={`${leftWidth}%`}
	>
		<div class="flex-1 overflow-y-auto p-6" aria-label="Configuration">
			<div class:hidden={$activeTab !== 'generate'}>
				<GenerateConfig />
			</div>
			<div class:hidden={$activeTab !== 'scrape'}>
				<ScrapeConfig />
			</div>
			<div class:hidden={$activeTab !== 'mutate'}>
				<MutateConfig onResult={(r) => (mutateResult = r)} />
			</div>
		</div>
		<RecentWordlists />
	</section>

	<div
		onpointerdown={startDrag}
		class="group absolute inset-y-0 w-1 cursor-col-resize"
		style:left={`calc(${leftWidth}% - 2px)`}
		role="separator"
		aria-orientation="vertical"
		aria-label="Resize config pane"
	>
		<div class="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-border transition-colors group-hover:bg-primary group-active:bg-primary"></div>
	</div>

	<section class="flex flex-1 flex-col overflow-y-auto p-6" aria-label="Output">
		<OutputPanel activeTab={$activeTab} {mutateResult} />
	</section>
</div>
