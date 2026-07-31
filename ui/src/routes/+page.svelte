<script lang="ts">
	import GenerateConfig from '$lib/components/config/GenerateConfig.svelte';
	import ScrapeConfig from '$lib/components/config/ScrapeConfig.svelte';
	import MutateConfig from '$lib/components/config/MutateConfig.svelte';
	import OutputPanel from '$lib/components/output/OutputPanel.svelte';
	import RecentWordlists from '$lib/components/RecentWordlists.svelte';
	import { activeTab } from '$lib/stores/tabs';

	let mutateResult = $state<{ words: string[]; count: number; source_count: number } | null>(null);
</script>

<div class="flex flex-1 overflow-hidden">
	<section class="flex w-2/5 flex-col overflow-hidden border-r border-border">
		<div class="flex-1 overflow-y-auto p-6" aria-label="Configuration">
			{#if $activeTab === 'generate'}
				<GenerateConfig />
			{:else if $activeTab === 'scrape'}
				<ScrapeConfig />
			{:else}
				<MutateConfig onResult={(r) => (mutateResult = r)} />
			{/if}
		</div>
		<RecentWordlists />
	</section>

	<section class="flex flex-1 flex-col overflow-y-auto p-6" aria-label="Output">
		<OutputPanel activeTab={$activeTab} {mutateResult} />
	</section>
</div>
