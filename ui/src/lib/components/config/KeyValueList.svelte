<script lang="ts">
	let {
		kind,
		items,
		onchange
	}: {
		kind: 'header' | 'cookie';
		items: { name: string; value: string }[];
		onchange: (items: { name: string; value: string }[]) => void;
	} = $props();

	let addText = $state('');
	let addError = $state('');

	const separator = $derived(kind === 'header' ? ':' : '=');
	const expected = $derived(kind === 'header' ? 'Name: value' : 'name=value');

	function addFromLine(line: string) {
		const trimmed = line.trim();
		if (!trimmed) return;
		const idx = trimmed.indexOf(separator);
		if (idx <= 0) {
			addError = `Expected ${expected} (e.g. ${kind === 'header' ? 'X-Foo: bar' : 'session=abc'})`;
			return;
		}
		const name = trimmed.slice(0, idx).trim();
		const entryValue = trimmed.slice(idx + 1).trim();
		if (!name) {
			addError = `Name cannot be empty`;
			return;
		}

		// Headers: names are case-insensitive per HTTP spec; cookies: case-sensitive.
		const matches = (i: { name: string; value: string }) =>
			kind === 'header'
				? i.name.trim().toLowerCase() === name.toLowerCase()
				: i.name.trim() === name;

		const existing = items.find(matches);
		if (existing) {
			existing.name = name;
			existing.value = entryValue;
			onchange([...items]);
		} else {
			onchange([...items, { name, value: entryValue }]);
		}

		addText = '';
		addError = '';
	}

	function updateItem(index: number, field: 'name' | 'value', newValue: string) {
		items[index][field] = newValue;
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
	<label for={`${kind}-add`} class="block text-sm font-medium text-foreground">
		{kind === 'header' ? 'Headers' : 'Cookies'}
	</label>
	{#if items.length > 0}
		<div class="space-y-2">
			{#each items as item, i (i)}
				<div class="flex items-center gap-2">
					<input
						type="text"
						value={item.name}
						oninput={(e) => updateItem(i, 'name', e.currentTarget.value)}
						placeholder={kind === 'header' ? 'Name' : 'name'}
						class="w-2/5 min-w-0 rounded-md border border-border bg-background px-2 py-1.5 font-mono text-xs text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
					/>
					<span class="shrink-0 text-xs text-muted-foreground">{separator}</span>
					<input
						type="text"
						value={item.value}
						oninput={(e) => updateItem(i, 'value', e.currentTarget.value)}
						placeholder="value"
						class="w-2/5 min-w-0 rounded-md border border-border bg-background px-2 py-1.5 font-mono text-xs text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
					/>
					<button
						type="button"
						onclick={() => removeItem(i)}
						class="shrink-0 rounded-md p-1 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
						aria-label="Remove {item.name}"
						title="Remove"
					>
						✕
					</button>
				</div>
			{/each}
		</div>
	{/if}
	<input
		id={`${kind}-add`}
		type="text"
		bind:value={addText}
		onkeydown={handleAddKeydown}
		placeholder={kind === 'header' ? 'X-Foo: bar — press Enter to add' : 'session=abc — press Enter to add'}
		class="w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
	/>
	{#if addError}
		<p class="text-xs text-destructive">{addError}</p>
	{:else}
		<p class="text-xs text-muted-foreground">Press Enter to add. One {expected} per entry.</p>
	{/if}
</div>