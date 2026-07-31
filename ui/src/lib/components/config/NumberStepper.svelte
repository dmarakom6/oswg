<script lang="ts">
	let {
		value,
		onchange,
		label,
		min = 1,
		max = 100,
		step = 1
	}: {
		value: number;
		onchange: (val: number) => void;
		label: string;
		min?: number;
		max?: number;
		step?: number;
	} = $props();

	function clamp(v: number) {
		return Math.max(min, Math.min(max, v));
	}

	const inputId = `num-${Math.random().toString(36).slice(2, 8)}`;
</script>

<div class="space-y-1.5">
	<label for={inputId} class="block text-sm font-medium text-foreground">{label}</label>
	<div class="flex items-center gap-2">
		<button
			type="button"
			onclick={() => onchange(clamp(value - step))}
			disabled={value <= min}
			class="flex h-8 w-8 items-center justify-center rounded-md border border-border text-sm transition-colors hover:bg-accent disabled:opacity-40 disabled:cursor-not-allowed"
			aria-label="Decrease {label}"
		>
			−
		</button>
		<input
			id={inputId}
			type="number"
			{min}
			{max}
			value={value}
			oninput={(e) => onchange(clamp(Number(e.currentTarget.value)))}
			class="w-24 rounded-md border border-border bg-background px-3 py-1.5 text-center font-mono text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
		/>
		<button
			type="button"
			onclick={() => onchange(clamp(value + step))}
			disabled={value >= max}
			class="flex h-8 w-8 items-center justify-center rounded-md border border-border text-sm transition-colors hover:bg-accent disabled:opacity-40 disabled:cursor-not-allowed"
			aria-label="Increase {label}"
		>
			+
		</button>
	</div>
</div>
