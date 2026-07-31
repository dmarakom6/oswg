import type { WSJobMessage } from '$lib/api/types';

type WSState = 'connecting' | 'connected' | 'disconnected' | 'error';
type Listener = (msg: WSJobMessage) => void;

interface Connection {
	ws: WebSocket;
	state: WSState;
	reconnectTimer: ReturnType<typeof setTimeout> | null;
	reconnectAttempts: number;
	listeners: Set<Listener>;
}

const connections = new Map<string, Connection>();
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 3000;

function getWsUrl(jobId: string): string {
	const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
	return `${proto}//${location.host}/ws/jobs/${jobId}`;
}

export function connectJobWs(jobId: string, onUpdate?: Listener): () => void {
	const existing = connections.get(jobId);
	if (existing) {
		if (onUpdate) existing.listeners.add(onUpdate);
		return () => disconnectJobWs(jobId, onUpdate);
	}

	const ws = new WebSocket(getWsUrl(jobId));
	const conn: Connection = {
		ws,
		state: 'connecting',
		reconnectTimer: null,
		reconnectAttempts: 0,
		listeners: new Set()
	};
	if (onUpdate) conn.listeners.add(onUpdate);
	connections.set(jobId, conn);

	ws.onopen = () => {
		conn.state = 'connected';
		conn.reconnectAttempts = 0;
	};

	ws.onmessage = (event) => {
		try {
			const msg = JSON.parse(event.data) as WSJobMessage;
			conn.listeners.forEach((fn) => fn(msg));
		} catch {
			// ignore malformed messages
		}
	};

	ws.onclose = () => {
		conn.state = 'disconnected';
		if (conn.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
			conn.reconnectTimer = setTimeout(() => {
				connections.delete(jobId);
				conn.reconnectAttempts++;
				connectJobWs(jobId);
			}, RECONNECT_DELAY);
		}
	};

	ws.onerror = () => {
		conn.state = 'error';
	};

	return () => disconnectJobWs(jobId, onUpdate);
}

export function disconnectJobWs(jobId: string, listener?: Listener): void {
	const conn = connections.get(jobId);
	if (!conn) return;
	if (listener) conn.listeners.delete(listener);
	if (conn.listeners.size === 0) {
		if (conn.reconnectTimer) clearTimeout(conn.reconnectTimer);
		conn.ws.close();
		connections.delete(jobId);
	}
}

export function getWsState(jobId: string): WSState | null {
	return connections.get(jobId)?.state ?? null;
}
