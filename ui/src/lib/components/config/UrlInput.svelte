<script lang="ts">
	let {
		value,
		onchange,
		error,
		placeholder = 'https://example.com'
	}: {
		value: string;
		onchange: (val: string) => void;
		error?: string;
		placeholder?: string;
	} = $props();
</script>

<div class="space-y-1.5">
	<label for="url-input" class="block text-sm font-medium text-foreground">Target URL</label>
	<input
		id="url-input"
		type="url"
		{placeholder}
		value={value}
		oninput={(e) => onchange(e.currentTarget.value)}
		class="w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-sm text-foreground placeholder:text-muted-foreground transition-colors focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary
			{error ? 'border-destructive' : ''}"
		aria-invalid={!!error}
		aria-describedby={error ? 'url-error' : undefined}
	/>
	{#if error}
		<p id="url-error" class="text-xs text-destructive">{error}</p>
	{/if}
</div>
