import { io, type Socket } from "socket.io-client";
import { API_URL } from "@/services/api";

class SocketService {
  private socket: Socket | null = null;
  private url = (() => {
    let base = process.env.NEXT_PUBLIC_SOCKET_URL || process.env.NEXT_PUBLIC_WS_URL || API_URL;
    if (base.endsWith("/api/v1")) base = base.slice(0, -7);
    if (base.endsWith("/api/v1/")) base = base.slice(0, -8);
    return base;
  })();

  connect(token?: string) {
    if (this.socket) {
      return this.socket;
    }

    this.socket = io(this.url, {
      autoConnect: false,
      reconnection: true,
      reconnectionAttempts: Infinity,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 8000,
      auth: token ? { token } : undefined,
    });

    this.socket.connect();
    return this.socket;
  }

  getSocket() {
    return this.socket;
  }

  emit(event: string, payload: unknown) {
    this.socket?.emit(event, payload);
  }

  disconnect() {
    this.socket?.disconnect();
    this.socket = null;
  }
}

export const socketService = new SocketService();
