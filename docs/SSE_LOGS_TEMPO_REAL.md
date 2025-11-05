# SSE - Logs em Tempo Real

Sistema de Server-Sent Events para monitoramento de logs da API externa em tempo real.

## 🚀 Endpoints Disponíveis

### 1. Stream de Logs (SSE)

**Endpoint:** `GET /api/v2/logs-tempo-real/stream/<job_id>`

**Descrição:** Stream de logs filtrados por ID do job em tempo real

**Parâmetros:**
- `job_id` (path): ID do job de execução do RPA

**Resposta:** Stream SSE com eventos JSON

**Exemplo de uso:**
```javascript
const jobId = 'abc-123-def-456';
const eventSource = new EventSource(`/api/v2/logs-tempo-real/stream/${jobId}`);

eventSource.onmessage = function(event) {
    const log = JSON.parse(event.data);
    
    // Exibir log na tela
    console.log(`[${log.timestamp}] [${log.level}] ${log.message}`);
    
    // Processar por tipo
    if (log.type === 'connection') {
        console.log('✅ Conectado ao stream de logs');
    } else if (log.type === 'log') {
        // Adicionar log ao DOM
        appendLogToScreen(log);
    } else if (log.type === 'error') {
        console.error('❌ Erro:', log.message);
    }
};

eventSource.onerror = function(event) {
    console.error('⚠️ Erro no SSE. Reconectando...');
};

// Fechar conexão quando não precisar mais
// eventSource.close();
```

---

### 2. Teste de Conexão

**Endpoint:** `GET /api/v2/logs-tempo-real/teste-conexao`

**Descrição:** Verifica se a conexão com a API externa de logs está funcionando

**Resposta:**
```json
{
  "success": true,
  "message": "Conexão com API externa de logs estabelecida com sucesso",
  "status_code": 200,
  "token_status": "Token JWT global válido"
}
```

**Exemplo de uso:**
```javascript
fetch('/api/v2/logs-tempo-real/teste-conexao')
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('✅', data.message);
        } else {
            console.error('❌', data.message);
        }
    });
```

---

## 📦 Formato dos Logs

### Evento de Conexão
```json
{
  "type": "connection",
  "message": "Conectado ao stream de logs para job abc-123",
  "timestamp": ""
}
```

### Evento de Log Normal
```json
{
  "type": "log",
  "level": "INFO",
  "message": "Processando RPA da operadora VIVO",
  "operadora": "VIVO",
  "job_id": "abc-123-def-456",
  "timestamp": "2025-11-05T01:53:35.123Z",
  "service": "rpa-api",
  "logger": "app.main"
}
```

### Evento de Erro
```json
{
  "type": "error",
  "message": "Erro de conexão: Connection timeout",
  "timestamp": ""
}
```

---

## 🔐 Autenticação

O sistema **automaticamente** usa o **token JWT global** configurado pelos administradores. Não é necessário enviar cabeçalhos de autenticação nas requisições SSE.

---

## 🔄 Como Funciona

1. **Cliente** abre conexão SSE: `new EventSource('/api/v2/logs-tempo-real/stream/job-123')`
2. **Servidor Flask** conecta à API externa: `http://191.252.218.230:8000/events/logs`
3. **API Externa** envia logs em tempo real via SSE
4. **Servidor Flask** filtra logs por `job_id` e repassa ao cliente
5. **Cliente** recebe apenas logs do job específico

---

## 💡 Exemplo Completo (HTML + JavaScript)

```html
<!DOCTYPE html>
<html>
<head>
    <title>Logs em Tempo Real</title>
    <style>
        #log-container {
            font-family: 'Courier New', monospace;
            background: #1e1e1e;
            color: #dcdcdc;
            padding: 20px;
            height: 500px;
            overflow-y: auto;
        }
        .log-entry {
            margin: 5px 0;
            padding: 5px;
            border-left: 3px solid #4CAF50;
        }
        .log-error {
            border-left-color: #f44336;
            color: #ff6b6b;
        }
        .log-warning {
            border-left-color: #ff9800;
            color: #ffd93d;
        }
    </style>
</head>
<body>
    <h1>Logs em Tempo Real - Job: <span id="job-id"></span></h1>
    <button onclick="stopLogs()">Parar Logs</button>
    <div id="log-container"></div>
    
    <script>
        const jobId = 'abc-123'; // ID do job
        document.getElementById('job-id').textContent = jobId;
        
        let eventSource = null;
        
        function startLogs() {
            eventSource = new EventSource(`/api/v2/logs-tempo-real/stream/${jobId}`);
            const container = document.getElementById('log-container');
            
            eventSource.onmessage = function(event) {
                const log = JSON.parse(event.data);
                
                const logEntry = document.createElement('div');
                logEntry.className = 'log-entry';
                
                if (log.level === 'ERROR') {
                    logEntry.classList.add('log-error');
                } else if (log.level === 'WARNING') {
                    logEntry.classList.add('log-warning');
                }
                
                logEntry.innerHTML = `
                    [${log.timestamp || new Date().toISOString()}] 
                    <strong>${log.level}</strong>: 
                    ${log.message}
                    ${log.operadora ? `(${log.operadora})` : ''}
                `;
                
                container.appendChild(logEntry);
                container.scrollTop = container.scrollHeight;
            };
            
            eventSource.onerror = function(event) {
                console.error('Erro no SSE:', event);
                const errorEntry = document.createElement('div');
                errorEntry.className = 'log-entry log-error';
                errorEntry.textContent = '⚠️ Conexão perdida. Tentando reconectar...';
                container.appendChild(errorEntry);
            };
        }
        
        function stopLogs() {
            if (eventSource) {
                eventSource.close();
                console.log('Stream de logs encerrado');
            }
        }
        
        // Iniciar automaticamente
        startLogs();
    </script>
</body>
</html>
```

---

## 🛠️ Integração com Backend

### API Externa

- **Endpoint SSE:** `http://191.252.218.230:8000/events/logs`
- **Autenticação:** Bearer Token JWT (token global do sistema)
- **Filtros:** Logs filtrados por `job_id` automaticamente

### Token JWT Global

O sistema usa o token JWT configurado por administradores:
1. Acesse `/usuarios` como admin
2. Edite um usuário admin
3. Clique em **"Obter Novo JWT (Global)"**
4. O token é usado automaticamente pelo SSE

---

## 🔍 Troubleshooting

### Erro: "Token JWT não configurado"
**Solução:** Acesse `/usuarios` como admin e clique em "Obter Novo JWT (Global)"

### Erro: "Conexão perdida"
**Solução:** O browser reconectará automaticamente. Se persistir, verifique se a API externa está online

### Logs não aparecem
**Solução:** Verifique se o `job_id` está correto e se há logs sendo gerados pela API externa

---

## 📚 Referências

- **SSE Spec:** https://html.spec.whatwg.org/multipage/server-sent-events.html
- **EventSource API:** https://developer.mozilla.org/en-US/docs/Web/API/EventSource
- **API Externa:** http://191.252.218.230:8000/docs
