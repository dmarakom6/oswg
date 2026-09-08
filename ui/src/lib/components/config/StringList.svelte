<script lang="ts">
	let {
		label,
		items,
		onchange,
		placeholder,
		hint
	}: {
		label: string;
		items: string[];
		onchange: (items: string[]) => void;
		placeholder?: string;
		hint?: string;
	} = $props();

	let addText = $state('');
	const addId = `strlist-${Math.random().toString(36).slice(2, 8)}`;

	function addFromLine(line: string) {
		const trimmed = line.trim();
		if (!trimmed) return;
		if (items.includes(trimmed)) {
			addText = '';
			return;
		}
		onchange([...items, trimmed]);
		addText = '';
	}

	function updateItem(index: number, newValue: string) {
		items[index] = newValue;
		onchange([...items]);
	}

	function removeItem(index: number) {
		items.splice(index, 1);
		onchange([...items]);
	}

	function handleAddKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			addFromLine(addText);
		}
	}
</script>

<div class="space-y-1.5">
	<label for={addId} class="block text-sm font-medium text-foreground">{label}</label>
	{#if items.length > 0}
		<div class="space-y-2">
			{#each items as item, i (i)}
				<div class="flex items-center gap-2">
					<input
						type="text"
						value={item}
						oninput={(e) => updateItem(i, e.currentTarget.value)}
						class="w-full rounded-md border border-border bg-background px-2 py-1.5 font-mono text-xs text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
					/>
					<button
						type="button"
						onclick={() => removeItem(i)}
						class="shrink-0 rounded-md p-1 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
						aria-label="Remove {item}"
						title="Remove"
					>✕</button>
				</div>
			{/each}
		</div>
	{/if}
	<input
		id={addId}
		type="text"
		bind:value={addText}
		onkeydown={handleAddKeydown}
		placeholder={placeholder}
		class="w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
	/>
	{#if hint}
		<p class="text-xs text-muted-foreground">{hint}</p>
	{/if}
</div>