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
			<span class="block text-sm font-medium text-foreground">Session state (storage_state JSON)</span>
		{/if}
		<label class="cursor-pointer rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground">
			Load file…
			<input
				bind:this={fileInput}
				type="file"
				accept=".json,application/json"
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
		placeholder={'{\n  "cookies": [ … ],\n  "origins": [ … ]\n}'}
		class="w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-xs text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
	></textarea>
	<p class="text-xs text-muted-foreground">
		Log in with <span class="font-mono">oswg login &lt;url&gt; --save session.json</span>, then load the file here (or paste its JSON) for authenticated scraping — including localStorage tokens.
	</p>
</div>
