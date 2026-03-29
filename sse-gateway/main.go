/*
sse-gateway — High-performance SSE fanout server for Neptun.

Architecture:

	Redis Pub/Sub (sse:broadcast) → Go SSE Gateway → 10K+ browser/app clients
	Next.js / Python worker → Redis.publish("sse:broadcast", event)
	Go subscribes, broadcasts to all connected SSE clients via goroutines.

Features:
  - Per-IP connection limit (MAX_PER_IP = 5)
  - Global connection limit (MAX_CLIENTS = 50000)
  - Shared keepalive timer (55s)
  - Debounced marker_new (2s) and online (5s) broadcasts
  - Graceful shutdown
  - /health endpoint for nginx healthcheck
  - /metrics endpoint for monitoring

Replace the Node.js SSE route with this binary:

	nginx: location /api/chat/stream → proxy_pass http://127.0.0.1:4000
	Next.js continues handling all other /api/* routes.
*/
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"sync"
	"sync/atomic"
	"syscall"
	"time"

	"github.com/redis/go-redis/v9"
)

// ── Configuration ────────────────────────────────────────────────────────────

const (
	defaultPort       = "4000"
	defaultRedisURL   = "redis://127.0.0.1:6379/0"
	sseChannel        = "sse:broadcast" // must match Next.js redis.ts
	maxClients        = 50_000
	maxPerIP          = 5
	keepaliveInterval = 55 * time.Second
	markerDebounce    = 2 * time.Second
	onlineDebounce    = 5 * time.Second
	writeBufSize      = 4096
	writeTimeout      = 5 * time.Second
)

// ── SSE Client ───────────────────────────────────────────────────────────────

type sseClient struct {
	ch chan []byte // buffered channel per client
	ip string
}

// ── Hub manages all SSE clients ──────────────────────────────────────────────

type hub struct {
	mu       sync.RWMutex
	clients  map[*sseClient]struct{}
	ipCounts map[string]int
	count    atomic.Int64

	// Debounce state
	markerMu      sync.Mutex
	pendingMarker json.RawMessage
	markerTimer   *time.Timer

	onlineMu    sync.Mutex
	onlineTimer *time.Timer
}

func newHub() *hub {
	return &hub{
		clients:  make(map[*sseClient]struct{}),
		ipCounts: make(map[string]int),
	}
}

func (h *hub) addClient(ip string) (*sseClient, error) {
	h.mu.Lock()
	defer h.mu.Unlock()

	if int(h.count.Load()) >= maxClients {
		return nil, fmt.Errorf("too many connections")
	}
	if h.ipCounts[ip] >= maxPerIP {
		return nil, fmt.Errorf("too many connections from IP %s", ip)
	}

	c := &sseClient{
		ch: make(chan []byte, 64), // buffer up to 64 messages
		ip: ip,
	}
	h.clients[c] = struct{}{}
	h.ipCounts[ip]++
	h.count.Add(1)

	return c, nil
}

func (h *hub) removeClient(c *sseClient) {
	h.mu.Lock()
	defer h.mu.Unlock()

	if _, ok := h.clients[c]; !ok {
		return
	}
	delete(h.clients, c)
	h.count.Add(-1)

	h.ipCounts[c.ip]--
	if h.ipCounts[c.ip] <= 0 {
		delete(h.ipCounts, c.ip)
	}

	close(c.ch)
}

// broadcast sends raw SSE payload to all clients. Non-blocking: drops message
// if a client's buffer is full (slow consumer).
func (h *hub) broadcast(payload []byte) {
	h.mu.RLock()
	defer h.mu.RUnlock()

	for c := range h.clients {
		select {
		case c.ch <- payload:
		default:
			// Client too slow — drop this message (they'll get the next one)
		}
	}
}

// broadcastEvent encodes an event object and broadcasts as SSE data frame.
func (h *hub) broadcastEvent(event map[string]interface{}) {
	data, err := json.Marshal(event)
	if err != nil {
		return
	}
	payload := fmt.Sprintf("data: %s\n\n", data)
	h.broadcast([]byte(payload))
}

// debouncedMarker collects marker_new events and only broadcasts the latest
// after a 2-second quiet window.
func (h *hub) debouncedMarker(raw json.RawMessage) {
	h.markerMu.Lock()
	defer h.markerMu.Unlock()

	h.pendingMarker = raw

	if h.markerTimer != nil {
		return // timer already running
	}
	h.markerTimer = time.AfterFunc(markerDebounce, func() {
		h.markerMu.Lock()
		pending := h.pendingMarker
		h.pendingMarker = nil
		h.markerTimer = nil
		h.markerMu.Unlock()

		if pending != nil {
			event := map[string]interface{}{
				"type": "marker_new",
				"data": json.RawMessage(pending),
			}
			h.broadcastEvent(event)
		}
	})
}

// debouncedOnline broadcasts online count at most every 5 seconds.
func (h *hub) debouncedOnline() {
	h.onlineMu.Lock()
	defer h.onlineMu.Unlock()

	if h.onlineTimer != nil {
		return
	}
	h.onlineTimer = time.AfterFunc(onlineDebounce, func() {
		h.onlineMu.Lock()
		h.onlineTimer = nil
		h.onlineMu.Unlock()

		event := map[string]interface{}{
			"type": "online",
			"data": map[string]interface{}{
				"online": h.count.Load(),
			},
		}
		h.broadcastEvent(event)
	})
}

// keepalive sends SSE comment to all clients every 55s to keep connections alive.
func (h *hub) keepalive(ctx context.Context) {
	ticker := time.NewTicker(keepaliveInterval)
	defer ticker.Stop()

	payload := []byte(": keepalive\n\n")

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			if h.count.Load() > 0 {
				h.broadcast(payload)
			}
		}
	}
}

// logStats periodically logs connection counts.
func (h *hub) logStats(ctx context.Context) {
	ticker := time.NewTicker(60 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			n := h.count.Load()
			if n > 0 {
				h.mu.RLock()
				ips := len(h.ipCounts)
				h.mu.RUnlock()
				log.Printf("[SSE] %d connections from %d unique IPs", n, ips)
			}
		}
	}
}

// ── Redis subscriber ─────────────────────────────────────────────────────────

func subscribeRedis(ctx context.Context, h *hub, redisURL string) {
	opts, err := redis.ParseURL(redisURL)
	if err != nil {
		log.Fatalf("Invalid REDIS_URL: %v", err)
	}

	rdb := redis.NewClient(opts)
	defer rdb.Close()

	// Verify connectivity
	if err := rdb.Ping(ctx).Err(); err != nil {
		log.Fatalf("Redis connection failed: %v", err)
	}
	log.Printf("[REDIS] Connected to %s", redisURL)

	pubsub := rdb.Subscribe(ctx, sseChannel)
	defer pubsub.Close()

	ch := pubsub.Channel(
		redis.WithChannelSize(256),
	)

	log.Printf("[REDIS] Subscribed to '%s'", sseChannel)

	for {
		select {
		case <-ctx.Done():
			return
		case msg, ok := <-ch:
			if !ok {
				log.Println("[REDIS] Channel closed, reconnecting...")
				time.Sleep(time.Second)
				return // will be restarted by caller
			}
			handleRedisMessage(h, msg.Payload)
		}
	}
}

func handleRedisMessage(h *hub, payload string) {
	var event struct {
		Type string          `json:"type"`
		Data json.RawMessage `json:"data"`
	}
	if err := json.Unmarshal([]byte(payload), &event); err != nil {
		log.Printf("[REDIS] Malformed message: %v", err)
		return
	}

	switch event.Type {
	case "marker_new":
		h.debouncedMarker(event.Data)

	case "marker_update":
		// Follow-up position update — broadcast immediately (no debounce)
		full := map[string]interface{}{
			"type": "marker_update",
			"data": event.Data,
		}
		h.broadcastEvent(full)

	case "track_update":
		// Track-based position update — broadcast immediately (no debounce)
		full := map[string]interface{}{
			"type": "track_update",
			"data": event.Data,
		}
		h.broadcastEvent(full)

	case "online":
		// Ignore Next.js online counts — Go service tracks its own
		h.debouncedOnline()

	default:
		// alarm_update, new_message, delete_message, reaction, typing — immediate
		full := map[string]interface{}{
			"type": event.Type,
			"data": event.Data,
		}
		h.broadcastEvent(full)
	}
}

// ── HTTP Handlers ────────────────────────────────────────────────────────────

func sseHandler(h *hub) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// Get client IP from nginx headers
		ip := r.Header.Get("X-Real-IP")
		if ip == "" {
			fwd := r.Header.Get("X-Forwarded-For")
			if fwd != "" {
				ip = strings.Split(fwd, ",")[0]
				ip = strings.TrimSpace(ip)
			}
		}
		if ip == "" {
			ip = strings.Split(r.RemoteAddr, ":")[0]
		}

		client, err := h.addClient(ip)
		if err != nil {
			if strings.Contains(err.Error(), "too many connections from IP") {
				http.Error(w, `{"error":"Too many connections from this IP"}`, http.StatusTooManyRequests)
			} else {
				http.Error(w, `{"error":"Too many connections"}`, http.StatusServiceUnavailable)
			}
			return
		}

		// SSE headers
		w.Header().Set("Content-Type", "text/event-stream")
		w.Header().Set("Cache-Control", "no-cache, no-transform")
		w.Header().Set("Connection", "keep-alive")
		w.Header().Set("X-Accel-Buffering", "no")
		w.WriteHeader(http.StatusOK)

		flusher, ok := w.(http.Flusher)
		if !ok {
			h.removeClient(client)
			http.Error(w, "Streaming not supported", http.StatusInternalServerError)
			return
		}

		// Send initial connected event
		connected := fmt.Sprintf("data: {\"type\":\"connected\",\"data\":{\"online\":%d,\"server\":\"go-sse\"}}\n\n",
			h.count.Load())
		w.Write([]byte(connected))
		flusher.Flush()

		// Broadcast updated online count
		h.debouncedOnline()

		// Stream events until client disconnects
		ctx := r.Context()
		for {
			select {
			case <-ctx.Done():
				h.removeClient(client)
				h.debouncedOnline()
				return
			case msg, ok := <-client.ch:
				if !ok {
					return // channel closed
				}
				_, err := w.Write(msg)
				if err != nil {
					h.removeClient(client)
					h.debouncedOnline()
					return
				}
				flusher.Flush()
			}
		}
	}
}

func healthHandler(h *hub) http.HandlerFunc {
	startTime := time.Now()
	return func(w http.ResponseWriter, r *http.Request) {
		h.mu.RLock()
		ips := len(h.ipCounts)
		h.mu.RUnlock()

		resp := map[string]interface{}{
			"status":     "ok",
			"server":     "go-sse-gateway",
			"clients":    h.count.Load(),
			"unique_ips": ips,
			"uptime_s":   int(time.Since(startTime).Seconds()),
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
	}
}

// ── Main ─────────────────────────────────────────────────────────────────────

func main() {
	port := os.Getenv("SSE_PORT")
	if port == "" {
		port = defaultPort
	}

	redisURL := os.Getenv("REDIS_URL")
	if redisURL == "" {
		redisURL = defaultRedisURL
	}

	h := newHub()
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Graceful shutdown
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	// Start background goroutines
	go h.keepalive(ctx)
	go h.logStats(ctx)

	// Redis subscriber with automatic reconnection
	go func() {
		for {
			select {
			case <-ctx.Done():
				return
			default:
				subscribeRedis(ctx, h, redisURL)
				log.Println("[REDIS] Reconnecting in 2s...")
				time.Sleep(2 * time.Second)
			}
		}
	}()

	// HTTP server
	mux := http.NewServeMux()
	mux.HandleFunc("/api/chat/stream", sseHandler(h))
	mux.HandleFunc("/health", healthHandler(h))

	server := &http.Server{
		Addr:         ":" + port,
		Handler:      mux,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 0, // No write timeout for SSE
		IdleTimeout:  120 * time.Second,
	}

	go func() {
		log.Printf("[SSE-GATEWAY] Listening on :%s", port)
		log.Printf("[SSE-GATEWAY] Redis: %s", redisURL)
		log.Printf("[SSE-GATEWAY] Max clients: %d, per-IP: %d", maxClients, maxPerIP)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Server error: %v", err)
		}
	}()

	// Wait for shutdown signal
	sig := <-sigCh
	log.Printf("[SSE-GATEWAY] Received %v, shutting down...", sig)

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer shutdownCancel()

	cancel() // stop background goroutines

	if err := server.Shutdown(shutdownCtx); err != nil {
		log.Printf("[SSE-GATEWAY] Shutdown error: %v", err)
	}

	log.Println("[SSE-GATEWAY] Stopped")
}
