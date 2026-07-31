<script lang="ts">
	let {
		value,
		onchange,
		options
	}: {
		value: number;
		onchange: (val: number) => void;
		options: { value: number; label: string }[];
	} = $props();
</script>

<div class="inline-flex rounded-md border border-border">
	{#each options as opt}
		<button
			type="button"
			class="px-3 py-1.5 text-sm transition-colors first:rounded-l-md last:rounded-r-md
				{value === opt.value
				? 'bg-primary text-primary-foreground'
				: 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'}"
			onclick={() => onchange(opt.value)}
		>
			{opt.label}
		</button>
	{/each}
</div>
