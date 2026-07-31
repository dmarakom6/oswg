<script lang="ts">
	import type { ActiveTab } from '$lib/api/types';
	import { TABS } from '$lib/constants';

	let { activeTab, onchange }: { activeTab: ActiveTab; onchange: (tab: ActiveTab) => void } = $props();
</script>

<div class="flex border-b border-border bg-card" role="tablist">
	{#each TABS as tab}
		<button
			role="tab"
			aria-selected={activeTab === tab.id}
			class="relative px-6 py-3 text-sm font-medium transition-colors
				{activeTab === tab.id
				? 'text-primary'
				: 'text-muted-foreground hover:text-foreground'}"
			onclick={() => onchange(tab.id)}
		>
			{tab.label}
			{#if activeTab === tab.id}
				<span
					class="absolute bottom-0 left-0 right-0 h-0.5 bg-primary"
					style="transition: transform 150ms ease"
				></span>
			{/if}
		</button>
	{/each}
</div>
