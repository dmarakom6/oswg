<script lang="ts">
	import type { CrawlGraph } from '$lib/api/types';

	let { graph }: { graph: CrawlGraph | null } = $props();

	type SegNode = {
		name: string;
		children: Map<string, SegNode>;
		pages: number;
		url?: string;
	};

	type Arc = {
		name: string;
		depth: number;
		pages: number;
		url?: string;
		a0: number;
		a1: number;
	};

	const SIZE = 600;
	const CENTER = SIZE / 2;
	const MAX_R = 270;

	let hovered = $state<Arc | null>(null);
	let selected = $state<string | null>(null);

	function buildTree(nodes: { id: string }[]): SegNode {
		const root: SegNode = { name: '', children: new Map(), pages: 0 };
		for (const n of nodes) {
			let segs: string[];
			try {
				const u = new URL(n.id);
				const path = u.pathname.split('/').filter(Boolean).map((s) => decodeURIComponent(s));
				segs = [u.host, ...path];
			} catch {
				segs = [n.id];
			}
			let node = root;
			node.pages += 1;
			for (const s of segs) {
				if (!node.children.has(s)) {
					node.children.set(s, { name: s, children: new Map(), pages: 0 });
				}
				node = node.children.get(s)!;
				node.pages += 1;
			}
			node.url = n.id;
		}
		return root;
	}

	const layout = $derived.by(() => {
		if (!graph || graph.nodes.length === 0) return { arcs: [] as Arc[], total: 0, ringW: 0 };
		const root = buildTree(graph.nodes);
		const total = root.pages;
		const arcs: Arc[] = [];
		let maxDepth = 0;

		function walk(node: SegNode, depth: number, a0: number, span: number, label: string) {
			const a1 = a0 + span;
			maxDepth = Math.max(maxDepth, depth);
			arcs.push({ name: label, depth, pages: node.pages, url: node.url, a0, a1 });
			let childStart = a0;
			for (const child of node.children.values()) {
				const childSpan = span * (child.pages / node.pages);
				walk(child, depth + 1, childStart, childSpan, label ? `${label}/${child.name}` : child.name);
				childStart += childSpan;
			}
		}

		walk(root, 0, -Math.PI / 2, Math.PI * 2, '');
		const ringW = MAX_R / (maxDepth + 1);
		return { arcs, total, ringW };
	});

	function polar(r: number, a: number): [number, number] {
		return [CENTER + r * Math.cos(a), CENTER + r * Math.sin(a)];
	}

	function arcPath(arc: Arc): string {
		const inner = layout.ringW * arc.depth;
		const outer = layout.ringW * (arc.depth + 1);
		const large = arc.a1 - arc.a0 > Math.PI ? 1 : 0;
		const [x0, y0] = polar(inner, arc.a0);
		const [x1, y1] = polar(outer, arc.a0);
		const [x2, y2] = polar(outer, arc.a1);
		const [x3, y3] = polar(inner, arc.a1);
		return `M ${x0} ${y0} L ${x1} ${y1} A ${outer} ${outer} 0 ${large} 1 ${x2} ${y2} L ${x3} ${y3} A ${inner} ${inner} 0 ${large} 0 ${x0} ${y0} Z`;
	}

	function depthOpacity(depth: number): number {
		return Math.min(0.15 + depth * 0.15, 0.9);
	}

	const info = $derived(
		hovered ? (hovered.depth === 0 ? 'root' : hovered.name) : selected ?? ''
	);
</script>

<div class="space-y-2">
	<div class="flex items-center justify-between">
		<span class="text-xs font-medium text-foreground">Coverage map</span>
		{#if graph}
			<span class="text-xs text-muted-foreground">
				{layout.total} page{layout.total !== 1 ? 's' : ''} · {graph.crawl_strategy?.toUpperCase() ?? ''}
			</span>
		{/if}
	</div>

	{#if layout.arcs.length > 0}
		<div class="overflow-auto rounded-md border border-border bg-muted/20 p-2">
			<svg viewBox={`0 0 ${SIZE} ${SIZE}`} class="mx-auto block h-auto w-full max-w-[600px]">
				<g>
					<circle
						r={layout.ringW}
						fill="var(--primary)"
						fill-opacity="0.2"
						role="img"
						aria-label="root"
						onmouseenter={() => {
							const root = layout.arcs.find((a) => a.depth === 0);
							hovered = root ?? null;
						}}
						onmouseleave={() => (hovered = null)}
					>
						<title>root · {layout.total} pages</title>
					</circle>
					<text
						x={CENTER}
						y={CENTER + 4}
						text-anchor="middle"
						class="font-mono"
						fill="var(--foreground)"
						font-size="12"
					>
						{layout.total}
					</text>
				</g>
				{#each layout.arcs as arc}
					{#if arc.depth > 0}
						<path
							d={arcPath(arc)}
							fill="var(--primary)"
							fill-opacity={depthOpacity(arc.depth)}
							stroke={hovered === arc ? 'var(--primary)' : 'var(--border)'}
							stroke-width={hovered === arc ? 2 : 0.5}
							class="cursor-pointer transition-opacity"
							onmouseenter={() => (hovered = arc)}
							onmouseleave={() => (hovered = null)}
							onclick={() => (selected = arc.url ?? arc.name)}
							role="button"
							tabindex="0"
							onkeydown={(e) => {
								if (e.key === 'Enter' || e.key === ' ') {
									e.preventDefault();
									selected = arc.url ?? arc.name;
								}
							}}
						>
							<title>{arc.name || 'root'} · {arc.pages} page{arc.pages !== 1 ? 's' : ''}</title>
						</path>
					{/if}
				{/each}
			</svg>
		</div>
		{#if info}
			<p class="break-all font-mono text-[11px] text-muted-foreground">{info}</p>
		{/if}
	{:else}
		<p class="text-xs text-muted-foreground">No crawl data to display.</p>
	{/if}
</div>