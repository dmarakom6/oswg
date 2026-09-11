<script lang="ts">
	let {
		value,
		onchange,
		showLabel = true
	}: {
		value: string;
		onchange: (val: string) => void;
		showLabel?: boolean;
	} = $props();

	let fileInput: HTMLInputElement | undefined = $state();

	function onFileSelected() {
		const input = fileInput;
		const file = input?.files?.[0];
		if (!file) return;
		const reader = new FileReader();
		reader.onload = () => onchange(String(reader.result ?? ''));
		reader.readAsText(file);
		if (input) input.value = '';
	}
</script>

<div class="space-y-1.5">
	<div class="flex items-center justify-between gap-3">
		{#if showLabel}
			<span class="block text-sm font-medium text-foreground">Cookie file (cookies.txt)</span>
		{/if}
		<label class="cursor-pointer rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground">
			Load file…
			<input
				bind:this={fileInput}
				type="file"
				accept=".txt,text/plain"
				class="hidden"
				onchange={onFileSelected}
			/>
		</label>
	</div>
	<textarea
		value={value}
		oninput={(e) => onchange(e.currentTarget.value)}
		rows={4}
		spellcheck="false"
		placeholder="# Netscape HTTP Cookie File&#10;.example.com&#9;TRUE&#9;/&#9;FALSE&#9;1754518563&#9;session&#9;abc123"
		class="w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-xs text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
	></textarea>
	<p class="text-xs text-muted-foreground">
		Export cookies as Netscape format (e.g. a "Get cookies.txt" browser extension) and load them here for authenticated scraping.
	</p>
</div>