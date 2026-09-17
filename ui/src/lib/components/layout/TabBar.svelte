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
			class="relative flex-1 px-3 py-3 text-sm font-medium transition-colors sm:flex-none sm:px-6
				{activeTab === tab.id
				? 'text-primary'
				: 'text-muted-foreground hover:text-foreground'}"
			onclick={() => onchange(tab.id)}
		>
			{tab.label}
			{#if tab.shortcut}
				<kbd class="ml-2 hidden rounded border border-border bg-muted/40 px-1 text-[10px] text-muted-foreground sm:inline">
					{tab.shortcut}
				</kbd>
			{/if}
			{#if activeTab === tab.id}
				<span
					class="absolute bottom-0 left-0 right-0 h-0.5 bg-primary"
					style="transition: transform 150ms ease"
				></span>
			{/if}
		</button>
	{/each}
</div>
