<script lang="ts">
	import type { MutationTree } from '$lib/api/types';

	let { tree }: { tree: MutationTree } = $props();

	const MAX_BASES = 50;

	const sorted = $derived(
		Object.entries(tree.tree).sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0])).slice(0, MAX_BASES)
	);
	const totalBases = $derived(Object.keys(tree.tree).length);
	const totalVariants = $derived(Object.values(tree.tree).reduce((n, v) => n + v.length, 0));

	let expanded = $state<Set<string>>(new Set());

	function toggle(base: string) {
		const next = new Set(expanded);
		if (next.has(base)) {
			next.delete(base);
		} else {
			next.add(base);
		}
		expanded = next;
	}
</script>

<div class="space-y-2">
	<div class="flex items-center justify-between">
		<span class="text-xs font-medium text-foreground">Mutation tree</span>
		{#if totalBases}
			<span class="text-xs text-muted-foreground">
				{totalBases} base words · {totalVariants} variants · showing {sorted.length}
			</span>
		{/if}
	</div>

	{#if sorted.length > 0}
		<div class="space-y-1.5 rounded-md border border-border bg-muted/20 p-3">
			{#each sorted as [base, variants] (base)}
				<div class="rounded-md border border-border bg-background">
					<button
						type="button"
						onclick={() => toggle(base)}
						class="flex w-full items-center justify-between gap-2 px-2.5 py-2 text-left transition-colors hover:bg-muted/40"
					>
						<span class="truncate font-mono text-xs font-medium text-foreground">{base}</span>
						<span class="shrink-0 text-xs text-muted-foreground">
							{expanded.has(base) ? '▾' : '▸'} {variants.length} variant{variants.length !== 1 ? 's' : ''}
						</span>
					</button>
					{#if expanded.has(base)}
						<div class="flex flex-wrap gap-1 px-2.5 pb-2">
							{#each variants as variant}
								<span class="rounded bg-muted/40 px-1.5 py-0.5 font-mono text-[11px] text-foreground">
									{variant}
								</span>
							{/each}
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{:else}
		<p class="text-xs text-muted-foreground">No mutation data to display.</p>
	{/if}
</div>