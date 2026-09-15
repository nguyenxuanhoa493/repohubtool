/**
 * RetroHub Netplay Public Lobby API
 * Cloudflare Worker + KV Storage
 *
 * Features:
 * - Ultra-low latency via Cloudflare Edge network (VN datacenters)
 * - Auto-cleanup "ghost rooms" via KV TTL (default: 30 minutes)
 * - Zero subrequest overhead: uses KV Key Metadata so 1 list call gets all rooms
 * - Optional Telegram broadcast when a public room is created
 * - Full CORS support for web dashboard & handheld clients
 */

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
  "Content-Type": "application/json; charset=utf-8",
};

const ROOM_TTL_SECONDS = 1800; // 30 minutes

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: CORS_HEADERS,
  });
}

function errorResponse(message, status = 400) {
  return jsonResponse({ ok: false, error: message }, status);
}

export default {
  async fetch(request, env, ctx) {
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: CORS_HEADERS });
    }

    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, "");

    // 1. Health check & API root
    if (path === "" || path === "/api") {
      return jsonResponse({
        ok: true,
        service: "RetroHub Netplay Public Lobby",
        version: "1.0.0",
        docs: {
          list_rooms: "GET /api/rooms",
          create_room: "POST /api/rooms",
          delete_room: "DELETE /api/rooms/:id",
          heartbeat: "POST /api/rooms/:id/heartbeat",
        },
      });
    }

    // Ensure KV is bound
    if (!env.LOBBY_KV) {
      return errorResponse("KV binding 'LOBBY_KV' is not configured.", 500);
    }

    try {
      // 2. GET /api/rooms: List active rooms
      if (path === "/api/rooms" && request.method === "GET") {
        const sysFilter = url.searchParams.get("sys")?.toUpperCase();

        // KV list retrieves up to 1000 keys with their metadata in ONE single operation!
        const listResult = await env.LOBBY_KV.list({ prefix: "room:" });

        let rooms = [];
        for (const key of listResult.keys) {
          if (key.metadata) {
            rooms.push(key.metadata);
          }
        }

        // Sort newest first
        rooms.sort((a, b) => (b.created_at || 0) - (a.created_at || 0));

        // Optional filter by system (FC, SFC, MD, etc.)
        if (sysFilter) {
          rooms = rooms.filter((r) => r.sys_code?.toUpperCase() === sysFilter);
        }

        return jsonResponse({
          ok: true,
          count: rooms.length,
          rooms: rooms,
        });
      }

      // 3. POST /api/rooms: Register or update a public room
      if (path === "/api/rooms" && request.method === "POST") {
        let body;
        try {
          body = await request.json();
        } catch {
          return errorResponse("Invalid JSON body.");
        }

        const port = String(body.port || body.id || "").trim();
        const gameTitle = String(body.game_title || "").trim();
        const sysCode = String(body.sys_code || "").trim().toUpperCase();
        const host = String(body.host || "a.pinggy.io").trim();
        const core = String(body.core || "").trim();
        const playerNick = String(body.player_nick || "Player1").trim();
        const devModel = String(body.dev_model || "Handheld").trim();

        if (!port || !port.match(/^\d{4,5}$/)) {
          return errorResponse("Port hợp lệ phải có từ 4 đến 5 chữ số.");
        }
        if (!gameTitle) {
          return errorResponse("Thiếu tên game (game_title).");
        }
        if (!sysCode) {
          return errorResponse("Thiếu mã hệ máy (sys_code).");
        }

        const roomId = `room:${port}`;
        const now = Math.floor(Date.now() / 1000);

        const roomData = {
          id: port,
          port: parseInt(port, 10),
          game_title: gameTitle,
          sys_code: sysCode,
          core: core,
          host: host,
          player_nick: playerNick,
          dev_model: devModel,
          status: "waiting",
          created_at: now,
          last_seen: now,
        };

        // Put to KV with 30 minutes TTL and store in metadata for 0-subrequest instant listing
        await env.LOBBY_KV.put(roomId, JSON.stringify(roomData), {
          expirationTtl: ROOM_TTL_SECONDS,
          metadata: roomData,
        });

        // Broadcast to Telegram Channel if configured in environment
        if (env.TELEGRAM_BOT_TOKEN && env.TELEGRAM_CHANNEL_ID) {
          ctx.waitUntil(broadcastToTelegram(env, roomData));
        }

        return jsonResponse({
          ok: true,
          message: "Phòng đã được mở công khai trên Sảnh chờ.",
          room: roomData,
        });
      }

      // Match /api/rooms/:id or /api/rooms/:id/heartbeat
      const roomMatch = path.match(/^\/api\/rooms\/([a-zA-Z0-9]+)(\/heartbeat)?$/);
      if (roomMatch) {
        const port = roomMatch[1];
        const isHeartbeat = Boolean(roomMatch[2]);
        const roomId = `room:${port}`;

        // 4. DELETE /api/rooms/:id: Remove room
        if (request.method === "DELETE" && !isHeartbeat) {
          await env.LOBBY_KV.delete(roomId);
          return jsonResponse({
            ok: true,
            message: `Đã đóng phòng ${port}.`,
          });
        }

        // 5. POST /api/rooms/:id/heartbeat: Refresh TTL
        if (request.method === "POST" && isHeartbeat) {
          const raw = await env.LOBBY_KV.get(roomId);
          if (!raw) {
            return errorResponse("Phòng không tồn tại hoặc đã hết hạn.", 404);
          }

          let data = JSON.parse(raw);
          data.last_seen = Math.floor(Date.now() / 1000);

          await env.LOBBY_KV.put(roomId, JSON.stringify(data), {
            expirationTtl: ROOM_TTL_SECONDS,
            metadata: data,
          });

          return jsonResponse({
            ok: true,
            message: "Đã gia hạn thời gian phòng.",
          });
        }
      }

      return errorResponse("Endpoint không tồn tại.", 404);
    } catch (err) {
      return errorResponse(`Server error: ${err.message}`, 500);
    }
  },
};

/**
 * Optional async broadcast to a public Telegram group or channel
 */
async function broadcastToTelegram(env, room) {
  try {
    const text = [
      "🎮 *[RetroHub Netplay] Có phòng chơi mới!*",
      `🕹️ *Game:* ${room.game_title} \`[${room.sys_code}]\``,
      room.core ? `⚙️ *Core:* \`${room.core}\`` : "",
      `📱 *Host:* ${room.player_nick} (${room.dev_model})`,
      "",
      `🔑 *Mã phòng:* \`${room.port}\``,
      `🌐 *Máy chủ:* \`${room.host}:${room.port}\``,
      "",
      "👉 *Cách vào chơi:* Mở RetroHub ➔ chọn cùng game ➔ chọn Netplay ➔ nhập mã!",
    ]
      .filter(Boolean)
      .join("\n");

    await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id: env.TELEGRAM_CHANNEL_ID,
        text: text,
        parse_mode: "Markdown",
      }),
    });
  } catch (e) {
    console.error("Telegram broadcast failed:", e);
  }
}
