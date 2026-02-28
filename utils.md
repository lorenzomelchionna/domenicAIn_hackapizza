# Hackapizza API - Curl Commands

---

## HTTP Endpoints (GET)

### Info ristorante (solo il tuo)
```bash
curl -X GET "https://hackapizza.datapizza.tech/restaurant/3" -H "x-api-key: dTpZhKpZ02-fe756e6e4185e69a6f00aae8"
```

### Menu del ristorante
```bash
curl -X GET "https://hackapizza.datapizza.tech/restaurant/3/menu" -H "x-api-key: dTpZhKpZ02-fe756e6e4185e69a6f00aae8"
```

### Lista tutti i ristoranti
```bash
curl -X GET "https://hackapizza.datapizza.tech/restaurants" -H "x-api-key: dTpZhKpZ02-fe756e6e4185e69a6f00aae8"
```

### Ricette disponibili
```bash
curl -X GET "https://hackapizza.datapizza.tech/recipes" -H "x-api-key: dTpZhKpZ02-fe756e6e4185e69a6f00aae8"
```

### Storico bid di un turno
```bash
curl -X GET "https://hackapizza.datapizza.tech/bid_history?turn_id=1" -H "x-api-key: dTpZhKpZ02-fe756e6e4185e69a6f00aae8"
```

### Pasti serviti (per turno e ristorante)
```bash
curl -X GET "https://hackapizza.datapizza.tech/meals?turn_id=1&restaurant_id=3" -H "x-api-key: dTpZhKpZ02-fe756e6e4185e69a6f00aae8"
```

### Entry di mercato
```bash
curl -X GET "https://hackapizza.datapizza.tech/market/entries" -H "x-api-key: dTpZhKpZ02-fe756e6e4185e69a6f00aae8"
```

---

## MCP Tools (POST /mcp)

### Invia offerte asta cieca (closed_bid phase)
```bash
curl -X POST "https://hackapizza.datapizza.tech/mcp" \
  -H "x-api-key: dTpZhKpZ02-fe756e6e4185e69a6f00aae8" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "closed_bid",
      "arguments": {
        "bids": [
          {"ingredient": "Pomodoro", "bid": 10, "quantity": 5},
          {"ingredient": "Mozzarella", "bid": 15, "quantity": 3}
        ]
      }
    },
    "id": 1
  }'
```

### Imposta/aggiorna menu (speaking, closed_bid, waiting)
```bash
curl -X POST "https://hackapizza.datapizza.tech/mcp" \
  -H "x-api-key: dTpZhKpZ02-fe756e6e4185e69a6f00aae8" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "save_menu",
      "arguments": {
        "items": [
          {"name": "Margherita", "price": 12},
          {"name": "Marinara", "price": 10}
        ]
      }
    },
    "id": 1
  }'
```

### Prepara piatto (serving phase)
```bash
curl -X POST "https://hackapizza.datapizza.tech/mcp" \
  -H "x-api-key: dTpZhKpZ02-fe756e6e4185e69a6f00aae8" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "prepare_dish",
      "arguments": {
        "dish_name": "Margherita"
      }
    },
    "id": 1
  }'
```

### Servi piatto a cliente (serving phase)
```bash
curl -X POST "https://hackapizza.datapizza.tech/mcp" \
  -H "x-api-key: dTpZhKpZ02-fe756e6e4185e69a6f00aae8" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "serve_dish",
      "arguments": {
        "dish_name": "Margherita",
        "client_id": "client_123"
      }
    },
    "id": 1
  }'
```

### Apri/chiudi ristorante
```bash
curl -X POST "https://hackapizza.datapizza.tech/mcp" \
  -H "x-api-key: dTpZhKpZ02-fe756e6e4185e69a6f00aae8" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "update_restaurant_is_open",
      "arguments": {
        "is_open": true
      }
    },
    "id": 1
  }'
```

### Crea entry mercato (BUY o SELL)
```bash
curl -X POST "https://hackapizza.datapizza.tech/mcp" \
  -H "x-api-key: dTpZhKpZ02-fe756e6e4185e69a6f00aae8" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "create_market_entry",
      "arguments": {
        "side": "SELL",
        "ingredient_name": "Pomodoro",
        "quantity": 3,
        "price": 8
      }
    },
    "id": 1
  }'
```

### Accetta entry di mercato
```bash
curl -X POST "https://hackapizza.datapizza.tech/mcp" \
  -H "x-api-key: dTpZhKpZ02-fe756e6e4185e69a6f00aae8" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "execute_transaction",
      "arguments": {
        "market_entry_id": 123
      }
    },
    "id": 1
  }'
```

### Elimina tua entry di mercato
```bash
curl -X POST "https://hackapizza.datapizza.tech/mcp" \
  -H "x-api-key: dTpZhKpZ02-fe756e6e4185e69a6f00aae8" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "delete_market_entry",
      "arguments": {
        "market_entry_id": 123
      }
    },
    "id": 1
  }'
```

### Invia messaggio a un team
```bash
curl -X POST "https://hackapizza.datapizza.tech/mcp" \
  -H "x-api-key: dTpZhKpZ02-fe756e6e4185e69a6f00aae8" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "send_message",
      "arguments": {
        "recipient_id": 5,
        "text": "Ciao! Vuoi scambiare ingredienti?"
      }
    },
    "id": 1
  }'
```

---

## SSE Events (connessione real-time)

### Connetti agli eventi SSE
```bash
curl -N "https://hackapizza.datapizza.tech/events/3" \
  -H "Accept: text/event-stream" \
  -H "x-api-key: dTpZhKpZ02-fe756e6e4185e69a6f00aae8"
```

---

## Operazioni consentite per fase

| Operazione | speaking | closed_bid | waiting | serving | stopped |
|------------|----------|------------|---------|---------|---------|
| `save_menu` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `closed_bid` | ❌ | ✅ | ❌ | ❌ | ❌ |
| `prepare_dish` | ❌ | ❌ | ❌ | ✅ | ❌ |
| `serve_dish` | ❌ | ❌ | ❌ | ✅ | ❌ |
| `create_market_entry` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `execute_transaction` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `delete_market_entry` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `send_message` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `update_restaurant_is_open` | ✅ | ✅ | ✅ | ✅ (close only) | ❌ |
| `restaurant_info` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `get_meals` | ✅ | ✅ | ✅ | ✅ | ✅ |
