<script lang="ts">
	import { SHORTCUTS } from '$lib/shortcuts';
	import { helpOpen } from '$lib/stores/shortcuts';
</script>

{#if $helpOpen}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-6"
		role="presentation"
		onclick={(e) => {
			if (e.target === e.currentTarget) helpOpen.set(false);
		}}
	>
		<div
			class="w-full max-w-md overflow-hidden rounded-lg border border-border bg-background shadow-xl"
			role="dialog"
			tabindex="-1"
			aria-modal="true"
			aria-label="Keyboard shortcuts"
		>
			<div class="flex items-center justify-between border-b border-border px-4 py-3">
				<h2 class="text-sm font-semibold text-foreground">Keyboard shortcuts</h2>
				<button
					type="button"
					onclick={() => helpOpen.set(false)}
					class="rounded p-1 text-muted-foreground transition-colors hover:text-foreground"
					aria-label="Close shortcuts"
					title="Close (Esc)"
				>✕</button>
			</div>
			<ul class="max-h-[70vh] divide-y divide-border overflow-y-auto px-4 py-2">
				{#each SHORTCUTS as shortcut}
					<li class="flex items-center justify-between gap-6 py-2">
						<span class="text-sm text-foreground">{shortcut.description}</span>
						<span class="flex shrink-0 gap-1">
							{#each shortcut.keys as key}
								<kbd class="rounded border border-border bg-muted/40 px-1.5 py-0.5 font-mono text-xs text-foreground">
									{key}
								</kbd>
							{/each}
						</span>
					</li>
				{/each}
			</ul>
			<p class="border-t border-border px-4 py-2 text-xs text-muted-foreground">
				Press <kbd class="rounded border border-border bg-muted/40 px-1 text-[10px]">?</kbd> anywhere or
				<kbd class="rounded border border-border bg-muted/40 px-1 text-[10px]">Esc</kbd> to close.
			</p>
		</div>
	</div>
{/if}