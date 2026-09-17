<script lang="ts">
	import type { WordCount } from '$lib/api/types';

	let { words }: { words: WordCount[] } = $props();

	const MAX_ROWS = 20;

	const sorted = $derived(
		[...words].sort((a, b) => b.count - a.count).slice(0, MAX_ROWS)
	);
	const maxCount = $derived(sorted.length ? sorted[0].count : 1);
</script>

<div class="space-y-2">
	<div class="flex items-center justify-between">
		<span class="text-xs font-medium text-foreground">Word frequencies</span>
		{#if words.length}
			<span class="text-xs text-muted-foreground">
				top {sorted.length} of {words.length} · max {maxCount}×
			</span>
		{/if}
	</div>

	{#if sorted.length > 0}
		<div class="space-y-1.5 rounded-md border border-border bg-muted/20 p-3">
			{#each sorted as item (item.word)}
				<div class="flex items-center gap-2" title="{item.word} · {item.count}×">
					<span class="w-20 shrink-0 truncate text-right font-mono text-xs text-foreground sm:w-28">
						{item.word}
					</span>
					<div class="h-4 flex-1 overflow-hidden rounded bg-muted/50">
						<div
							class="h-full rounded bg-primary"
							style="width: {Math.max(2, (item.count / maxCount) * 100)}%"
						></div>
					</div>
					<span class="w-10 shrink-0 text-right font-mono text-xs text-muted-foreground">
						{item.count}
					</span>
				</div>
			{/each}
		</div>
	{:else}
		<p class="text-xs text-muted-foreground">No frequency data to display.</p>
	{/if}
</div>