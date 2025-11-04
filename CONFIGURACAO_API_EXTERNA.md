# Configuração da API Externa

## Visão Geral

A API externa em `http://191.252.218.230:8000` requer autenticação JWT para funcionar. Este documento explica como configurar e usar a integração.

## 🔑 Autenticação

### 1. Obter Token JWT

A API externa requer um token JWT válido. Para obter um token:

1. **Acesse a documentação**: http://191.252.218.230:8000/docs
2. **Faça login** ou obtenha um token JWT válido
3. **Configure o token** no arquivo `.env`

### 2. Configurar Token

Execute o script de configuração:

```bash
python configurar_token_api_externa.py
```

Ou configure manualmente no arquivo `.env`:

```env
# API Externa Configuration
API_EXTERNA_URL=http://191.252.218.230:8000
API_EXTERNA_TOKEN=seu_token_jwt_aqui
```

## 🧪 Testes

### Testar Autenticação

```bash
python teste_autenticacao_api_externa.py
```

### Testar Ciclo Completo

```bash
python teste_ciclo_completo_frontend.py
```

## 📊 Monitoramento

### Dashboard da API Externa

Acesse o dashboard para monitorar jobs em tempo real:

- **URL**: `/api/v2/externos/dashboard`
- **Funcionalidades**:
  - Status da conexão
  - Jobs ativos
  - Logs em tempo real
  - Detalhes dos jobs

### Endpoints Disponíveis

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/v2/externos/health` | GET | Status da API externa |
| `/api/v2/externos/jobs` | GET | Lista jobs ativos |
| `/api/v2/externos/status/{job_id}` | GET | Status de um job específico |
| `/api/v2/externos/executar/{processo_id}` | POST | Executar RPA/SAT |
| `/api/v2/externos/monitorar/{job_id}` | POST | Monitorar job |

## 🔄 Fluxo de Trabalho

### 1. Download RPA
- **Trigger**: Botão "Download" no processo
- **Status**: `AGUARDANDO_DOWNLOAD` → `DOWNLOAD_EM_ANDAMENTO` → `DOWNLOAD_CONCLUIDO`
- **Endpoint**: `/api/v2/externos/executar/{processo_id}` com `tipo: "rpa"`

### 2. Aprovação
- **Trigger**: Botão "Aprovar" no processo
- **Status**: `DOWNLOAD_CONCLUIDO` → `AGUARDANDO_ENVIO_SAT`

### 3. Envio SAT
- **Trigger**: Botão "Enviar SAT" no processo
- **Status**: `AGUARDANDO_ENVIO_SAT` → `UPLOAD_REALIZADO`
- **Endpoint**: `/api/v2/externos/executar/{processo_id}` com `tipo: "sat"`

## 📋 Operadoras Suportadas

As seguintes operadoras estão configuradas e suportadas:

| Código | Nome | Status |
|--------|------|--------|
| `OI` | Oi | ✅ Suportada |
| `VIVO` | Vivo | ✅ Suportada |
| `EMBRATEL` | Embratel | ✅ Suportada |
| `DIGITALNET` | Digitalnet | ✅ Suportada |

## 🔧 Configuração de Operadoras

### Atualizar Códigos

Se necessário, execute o script para atualizar os códigos das operadoras:

```bash
python atualizar_codigos_operadoras.py
```

### Verificar Mapeamento

```bash
python atualizar_codigos_operadoras.py verificar
```

## 🚨 Troubleshooting

### Erro: "Operadora não é suportada"
- Verifique se o código da operadora está na lista de suportadas
- Execute o script de atualização de códigos

### Erro: "Token inválido"
- Verifique se o token JWT está configurado no `.env`
- Teste a autenticação com o script de teste

### Erro: "CSRF token inválido"
- O teste simula cliques no frontend
- Verifique se a aplicação está rodando
- Verifique se o usuário está logado

### Erro: "Processo não está no status adequado"
- RPA: Processo deve estar em `AGUARDANDO_DOWNLOAD`
- SAT: Processo deve estar em `DOWNLOAD_CONCLUIDO`

## 📈 Logs e Monitoramento

### Logs da Aplicação

Os logs são salvos em:
- **Console**: Durante desenvolvimento
- **Arquivo**: Em produção (configurar logging)

### Monitoramento de Jobs

- **Dashboard**: Interface web para monitoramento
- **API**: Endpoints para consulta de status
- **Cache**: Armazenamento temporário de status

## 🔐 Segurança

### Tokens JWT
- Tokens têm validade de 12 horas
- Renovação automática configurada
- Armazenamento seguro em variáveis de ambiente

### CSRF Protection
- Todas as requisições web requerem CSRF token
- Tokens são validados automaticamente
- Proteção contra ataques CSRF

## 📞 Suporte

Para problemas com a API externa:

1. **Verificar logs** da aplicação
2. **Testar conexão** com script de teste
3. **Verificar documentação** da API externa
4. **Contatar administrador** da API externa

## 🔄 Atualizações

### Versão Atual
- **API Externa**: http://191.252.218.230:8000
- **Documentação**: http://191.252.218.230:8000/docs
- **Status**: ✅ Funcionando

### Próximas Atualizações
- [ ] WebSocket para logs em tempo real
- [ ] Notificações push
- [ ] Relatórios avançados
- [ ] Configuração via interface web
