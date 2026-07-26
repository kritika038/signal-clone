import { io, type Socket } from "socket.io-client";

class SocketService {
  private socket: Socket | null = null;
  private url =
    process.env.NEXT_PUBLIC_WS_URL ||
    (process.env.NODE_ENV === "production" ? "" : "http://localhost:8000");

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
      transports: ["websocket", "polling"],
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
