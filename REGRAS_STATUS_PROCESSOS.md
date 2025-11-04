# 📋 Regras Completas de Status de Processos
## Tirus Dashboard - Sistema de Orquestração RPA

**Versão:** 1.0  
**Data:** 04/11/2025  
**Desenvolvido para:** BEG Telecomunicações

---

## 🔄 Máquina de Estados

```
┌─────────────────────────────────────────────────────────────────┐
│                    AGUARDANDO_DOWNLOAD                           │
│  - Status inicial do processo                                    │
│  - Pode executar: Download via API Externa RPA                  │
│  - Retry automático até obter fatura                            │
└──────────────┬──────────────────────────────────────────────────┘
               │
               │ ✅ Download concluído COM fatura
               │ (url_fatura + data_vencimento)
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   AGUARDANDO_APROVACAO                           │
│  - Aguardando aprovação manual do usuário                       │
│  - Pode executar: Aprovar ou Rejeitar                           │
│  - Exibe fatura para visualização                               │
└──────────┬─────────────────────────┬────────────────────────────┘
           │                         │
           │ ✅ Aprovar              │ ❌ Rejeitar
           │                         │
           ▼                         ▼
┌──────────────────────┐  ┌────────────────────────────────┐
│ AGUARDANDO_ENVIO_SAT │  │   AGUARDANDO_DOWNLOAD          │
│  - Aprovado          │  │   (volta para tentativa nova)  │
│  - Pode enviar SAT   │  └────────────────────────────────┘
└──────────┬───────────┘
           │
           │ ✅ Upload SAT concluído
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     UPLOAD_REALIZADO                             │
│  - Processo concluído com sucesso                               │
│  - Fatura enviada para o SAT                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📐 Regras Detalhadas

### 1. **AGUARDANDO_DOWNLOAD**

**Descrição:** Processo criado e aguardando download da fatura da operadora.

**Condições:**
- ✅ Processo foi criado manualmente ou automaticamente
- ❌ Ainda não possui fatura vinculada (`url_fatura` é `NULL`)

**Ações Disponíveis:**
- 🔄 **Executar Download via RPA** → `POST /processos/executar-download/<id>`
- 🗑️ **Deletar processo** → `DELETE /processos/<id>`
- 📝 **Editar dados** → `PUT /processos/<id>`

**Transições:**
- ✅ **Download bem-sucedido COM fatura** → `AGUARDANDO_APROVACAO`
  - Requisitos: `url_fatura IS NOT NULL` AND `data_vencimento IS NOT NULL`
  - Método: `processo.marcar_download_completo()`
  
- ⚠️ **Download falhou** → **PERMANECE em AGUARDANDO_DOWNLOAD**
  - Sistema deve tentar novamente (retry automático)
  - Limite de tentativas: 3 (configurável)

**Ícones na Listagem:**
- 🔽 Download (botão principal)
- 📝 Editar
- 🗑️ Deletar

---

### 2. **AGUARDANDO_APROVACAO**

**Descrição:** Fatura foi baixada e está aguardando aprovação manual do usuário.

**Condições:**
- ✅ Possui fatura vinculada (`url_fatura IS NOT NULL`)
- ✅ Possui data de vencimento (`data_vencimento IS NOT NULL`)
- ❌ Ainda não foi aprovado (`aprovado_por_usuario_id IS NULL`)

**Ações Disponíveis:**
- 👁️ **Visualizar Fatura** → Modal ou nova aba com `url_fatura`
- ✅ **Aprovar** → `POST /processos/aprovar/<id>`
- ❌ **Rejeitar** → `POST /processos/rejeitar/<id>`

**Transições:**
- ✅ **Aprovação** → `AGUARDANDO_ENVIO_SAT`
  - Registra `aprovado_por_usuario_id` e `data_aprovacao`
  - Método: `processo.aprovar(usuario_id, observacoes)`
  
- ❌ **Rejeição** → `AGUARDANDO_DOWNLOAD`
  - Limpa `aprovado_por_usuario_id` e `data_aprovacao`
  - Registra motivo em `observacoes`
  - Método: `processo.rejeitar(observacoes)`

**Ícones na Listagem:**
- 👁️ Visualizar Fatura
- ✅ Aprovar (botão verde)
- ❌ Rejeitar (botão vermelho)

---

### 3. **AGUARDANDO_ENVIO_SAT**

**Descrição:** Processo foi aprovado e está pronto para upload no SAT.

**Condições:**
- ✅ Possui fatura vinculada
- ✅ Foi aprovado (`aprovado_por_usuario_id IS NOT NULL`)
- ❌ Ainda não foi enviado para SAT (`enviado_para_sat = FALSE`)

**Ações Disponíveis:**
- 📤 **Enviar para SAT via RPA** → `POST /processos/executar-upload-sat/<id>`
- 👁️ **Visualizar Fatura**
- 📝 **Editar dados**

**Transições:**
- ✅ **Upload SAT bem-sucedido** → `UPLOAD_REALIZADO`
  - Marca `enviado_para_sat = TRUE`
  - Registra `data_envio_sat`
  - Método: `processo.enviar_para_sat()`
  
- ⚠️ **Upload falhou** → **PERMANECE em AGUARDANDO_ENVIO_SAT**
  - Sistema deve tentar novamente (retry automático)

**Ícones na Listagem:**
- 📤 Enviar SAT (botão principal)
- 👁️ Visualizar Fatura
- 📝 Editar

---

### 4. **UPLOAD_REALIZADO**

**Descrição:** Processo concluído - fatura foi enviada para o SAT com sucesso.

**Condições:**
- ✅ Fatura vinculada
- ✅ Aprovado
- ✅ Enviado para SAT (`enviado_para_sat = TRUE`)

**Ações Disponíveis:**
- 👁️ **Visualizar Fatura**
- 📊 **Ver histórico de execuções**

**Transições:**
- ❌ **Nenhuma** - Status final

**Ícones na Listagem:**
- ✅ Concluído (ícone verde)
- 👁️ Visualizar
- 📊 Histórico

---

## 🔁 Sistema de Retry Automático

### Política de Retry para Download

**Quando aplicar:**
- ❌ Download falhou (exceção ou erro de RPA)
- ❌ Download não encontrou fatura
- ❌ Timeout na execução

**Configurações:**
```python
MAX_TENTATIVAS_DOWNLOAD = 3
INTERVALO_RETRY_MINUTOS = 30
RETRY_EXPONENCIAL = True  # 30min, 1h, 2h
```

**Implementação:**
1. Criar campo `tentativas_download` (int) no modelo Processo
2. Incrementar a cada falha
3. Se `tentativas_download >= MAX_TENTATIVAS`:
   - Marcar como "Falha Permanente"
   - Enviar notificação ao usuário
4. Caso contrário: agendar nova tentativa

### Política de Retry para Upload SAT

**Configurações:**
```python
MAX_TENTATIVAS_UPLOAD = 3
INTERVALO_RETRY_MINUTOS = 30
```

**Mesma lógica do download**

---

## 📦 Processamento em Lote

### Regras de Fila Interna

**Prioridade:**
1. 🔴 **ALTA**: Processos com menos de 3 dias até vencimento
2. 🟡 **MÉDIA**: Processos com 3-7 dias até vencimento
3. 🟢 **BAIXA**: Processos com mais de 7 dias até vencimento

**Limites:**
- Máximo de **5 jobs simultâneos** por operadora
- Máximo de **20 jobs simultâneos** no total
- Timeout por job: **10 minutos**

**Implementação:**
```python
class FilaProcessamento:
    def __init__(self):
        self.fila_alta = []
        self.fila_media = []
        self.fila_baixa = []
        self.em_execucao = {}
    
    def adicionar(self, processo):
        prioridade = self._calcular_prioridade(processo)
        if prioridade == 'ALTA':
            self.fila_alta.append(processo)
        elif prioridade == 'MEDIA':
            self.fila_media.append(processo)
        else:
            self.fila_baixa.append(processo)
    
    def processar_proxima(self):
        if self.fila_alta:
            return self.fila_alta.pop(0)
        elif self.fila_media:
            return self.fila_media.pop(0)
        elif self.fila_baixa:
            return self.fila_baixa.pop(0)
        return None
```

---

## 🔔 Notificações em Tempo Real (SSE)

### Endpoint SSE

**URL:** `GET /processos/sse/status`

**Eventos:**
1. **job_started**: Job de RPA iniciado
2. **job_progress**: Progresso do job (0-100%)
3. **job_completed**: Job concluído com sucesso
4. **job_failed**: Job falhou
5. **status_changed**: Status do processo mudou

**Exemplo de Implementação Frontend:**
```javascript
const eventSource = new EventSource('/processos/sse/status');

eventSource.addEventListener('status_changed', (event) => {
  const data = JSON.parse(event.data);
  console.log(`Processo ${data.processo_id}: ${data.status_antigo} → ${data.status_novo}`);
  // Atualizar UI
});

eventSource.addEventListener('job_progress', (event) => {
  const data = JSON.parse(event.data);
  console.log(`Job ${data.job_id}: ${data.progress}%`);
  // Atualizar barra de progresso
});
```

---

## 🎨 Ícones por Status

### Mapeamento Completo

| Status | Ícone Principal | Cor | Ações Disponíveis |
|--------|----------------|-----|-------------------|
| AGUARDANDO_DOWNLOAD | 🔽 Download | Azul | Download, Editar, Deletar |
| AGUARDANDO_APROVACAO | ⏳ Pendente | Amarelo | Visualizar, Aprovar, Rejeitar |
| AGUARDANDO_ENVIO_SAT | 📤 Enviar | Roxo | Enviar SAT, Visualizar, Editar |
| UPLOAD_REALIZADO | ✅ Concluído | Verde | Visualizar, Histórico |

### Badges HTML
```html
<!-- AGUARDANDO_DOWNLOAD -->
<span class="badge bg-primary">
  <i class="fas fa-download"></i> Aguardando Download
</span>

<!-- AGUARDANDO_APROVACAO -->
<span class="badge bg-warning">
  <i class="fas fa-clock"></i> Aguardando Aprovação
</span>

<!-- AGUARDANDO_ENVIO_SAT -->
<span class="badge bg-info">
  <i class="fas fa-upload"></i> Aguardando Envio SAT
</span>

<!-- UPLOAD_REALIZADO -->
<span class="badge bg-success">
  <i class="fas fa-check-circle"></i> Concluído
</span>
```

---

## ✅ Checklist de Implementação

- [ ] Adicionar campos `tentativas_download` e `tentativas_upload` ao modelo
- [ ] Implementar `FilaProcessamento` para processamento em lote
- [ ] Criar endpoint SSE `/processos/sse/status`
- [ ] Implementar retry automático com backoff exponencial
- [ ] Atualizar template `index.html` com ícones corretos
- [ ] Criar dashboard de monitoramento em tempo real
- [ ] Adicionar testes para todas as transições de status
- [ ] Documentar APIs no Swagger

---

## 📞 Suporte

Para dúvidas sobre as regras de status, consulte:
- **Documentação da API Externa:** `DOCUMENTACAO_INTEGRACAO_FRONTEND.md`
- **Código-fonte:** `apps/models/processo.py`
- **Rotas:** `apps/processos/routes.py`
