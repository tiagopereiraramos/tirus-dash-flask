# DOCUMENTAÇÃO GLOBAL COMPLETA - PARTE 2
## Sistema de Orquestração RPA BEG Telecomunicações - Tirus Dashboard Flask

**Versão:** 1.0.0
**Data:** 2025-01-14
**Continuação da Parte 1**

---

## ÍNDICE DA PARTE 2

6. [Integrações e APIs Externas](#6-integrações-e-apis-externas)
7. [Plataforma RPA](#7-plataforma-rpa)
8. [Processos de Negócio](#8-processos-de-negócio)
9. [Frontend e UX](#9-frontend-e-ux)
10. [Jobs, Scripts e Ferramentas Auxiliares](#10-jobs-scripts-e-ferramentas-auxiliares)
11. [Monitoramento, Logs e Notificações](#11-monitoramento-logs-e-notificações)
12. [Segurança e Compliance](#12-segurança-e-compliance)
13. [Qualidade e Testes](#13-qualidade-e-testes)
14. [Governança de Código](#14-governança-de-código)
15. [Roadmap e Histórico](#15-roadmap-e-histórico)

---

## 6. INTEGRAÇÕES E APIs EXTERNAS

### 6.1 API Externa RPA Terceirizado

**URL Base:** Configurável via `API_EXTERNA_URL` (padrão: `http://191.252.218.230:8000`)

**Autenticação:**
- Método: JWT Token Bearer
- Header: `Authorization: Bearer <token>`
- Token obtido via: `API_EXTERNA_TOKEN` ou login (`API_EXTERNA_USERNAME` + `API_EXTERNA_PASSWORD`)

**Endpoints Principais:**

#### 6.1.1 Executar RPA (Download)
```
POST /executar/{operadora}
Content-Type: application/json

Payload:
{
  "processo_id": "uuid",
  "operacao": "DOWNLOAD_FATURA",
  "cliente": { ... },
  "operadora": { ... },
  "processo": { ... },
  "execucao": { ... },
  "metadata": { ... }
}

Response:
{
  "success": true,
  "job_id": "uuid",
  "status": "EXECUTANDO",
  "message": "Job criado com sucesso"
}
```

#### 6.1.2 Executar SAT (Upload)
```
POST /executar/sat
Content-Type: application/json

Payload:
{
  "processo_id": "uuid",
  "cliente_nome_sat": "string",
  "dados_sat": "string",
  "arquivo_fatura": { ... },
  "metadados": { ... }
}
```

#### 6.1.3 Consultar Status de Job
```
GET /status/{job_id}
Authorization: Bearer <token>

Response:
{
  "job_id": "uuid",
  "status": "SUCESSO|EXECUTANDO|ERRO|TIMEOUT",
  "progress": 75,
  "resultado": { ... },
  "logs": [ ... ]
}
```

#### 6.1.4 Monitoramento em Tempo Real
```
GET /monitoramento/tempo-real
Authorization: Bearer <token>

Response:
{
  "jobs_ativos": 5,
  "jobs_concluidos_hoje": 120,
  "jobs_falhados_hoje": 3,
  "operadoras": {
    "OI": { "ativos": 2, "concluidos": 45 },
    "VIVO": { "ativos": 1, "concluidos": 30 }
  }
}
```

### 6.2 Modelos Pydantic para Payloads

#### 6.2.1 PayloadRPAExterno

**Localização:** `apps/api_externa/models.py`

**Estrutura:**
```python
@dataclass
class PayloadRPAExterno:
    processo_id: str
    operacao: TipoOperacaoExterna
    cliente: DadosCliente
    operadora: DadosOperadora
    processo: DadosProcesso
    execucao: DadosExecucao
    metadata: Metadata

    def validar(self) -> List[str]:
        """Valida payload e retorna lista de erros"""

    def to_dict(self) -> Dict[str, Any]:
        """Serializa para dicionário"""
```

**Campos Obrigatórios:**
- `processo_id` - UUID do processo
- `operacao` - Tipo de operação (DOWNLOAD_FATURA, UPLOAD_SAT)
- `cliente.id`, `cliente.razao_social`, `cliente.cnpj`
- `operadora.id`, `operadora.codigo`, `operadora.nome`
- `processo.id`, `processo.mes_ano`

#### 6.2.2 PayloadSATExterno

**Estrutura:**
```python
@dataclass
class PayloadSATExterno:
    processo_id: str
    cliente_nome_sat: str
    dados_sat: str
    arquivo_fatura: Dict[str, Any]
    metadados: Dict[str, Any]
    metadata: Metadata
```

#### 6.2.3 RespostaRPAExterno

**Estrutura:**
```python
@dataclass
class RespostaRPAExterno:
    success: bool
    processo_id: str
    job_id: Optional[str] = None
    status: Optional[StatusOperacaoExterna] = None
    resultado: Optional[Dict[str, Any]] = None
    erro: Optional[str] = None
    request_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RespostaRPAExterno":
        """Deserializa de dicionário"""
```

### 6.3 Serviço de Integração

**Classe Principal:** `APIExternaService` (`apps/api_externa/services.py`)

**Métodos Principais:**

```python
class APIExternaService:
    def criar_payload_rpa(self, processo: Processo) -> PayloadRPAExterno
    def criar_payload_sat(self, processo: Processo) -> PayloadSATExterno
    def enviar_para_rpa_externo(self, processo: Processo, url_endpoint: str) -> RespostaRPAExterno
    def enviar_para_sat_externo(self, processo: Processo, url_endpoint: str) -> RespostaSATExterno
    def consultar_status_job(self, job_id: str) -> Dict[str, Any]
    def obter_logs_job(self, job_id: str) -> List[str]
```

**Configurações:**
- Timeout: 300 segundos (5 minutos)
- Tentativas máximas: 3
- Retry com backoff exponencial

### 6.4 Sistema de Cache

**Classe:** `CacheManager` (`apps/api_externa/cache.py`)

**Funcionalidades:**
- Cache de respostas de status de jobs
- TTL configurável (padrão: 60 segundos)
- Limpeza automática de entradas expiradas
- Cache em memória (pode ser expandido para Redis)

**Uso:**
```python
from apps.api_externa.cache import get_cache_manager

cache = get_cache_manager()
cache.set(f"job_{job_id}", resultado, ttl=60)
resultado = cache.get(f"job_{job_id}")
```

### 6.5 Monitoramento de Jobs

**Classe:** `JobMonitor` (`apps/api_externa/monitor.py`)

**Funcionalidades:**
- Monitoramento de jobs ativos
- Polling automático de status
- Notificações de conclusão
- Estatísticas agregadas

**Métodos:**
```python
class JobMonitor:
    def adicionar_job(self, job_id: str, processo_id: str)
    def remover_job(self, job_id: str)
    def obter_jobs_ativos(self) -> List[Dict[str, Any]]
    def atualizar_status(self, job_id: str, status: str)
    def obter_estatisticas(self) -> Dict[str, Any]
```

### 6.6 Cliente HTTP

**Classe:** `APIClient` (`apps/api_externa/client.py`)

**Funcionalidades:**
- Cliente HTTP reutilizável
- Gerenciamento de sessão
- Retry automático
- Logging de requisições

**Uso:**
```python
from apps.api_externa.client import APIClient

client = APIClient(base_url="http://api.externa.com")
response = client.post("/executar/oi", json=payload)
```

### 6.7 Autenticação

**Classe:** `APIAuth` (`apps/api_externa/auth.py`)

**Métodos:**
- `obter_token()` - Obtém token JWT
- `renovar_token()` - Renova token expirado
- `validar_token(token)` - Valida token
- `get_headers()` - Retorna headers com autenticação

**Fluxo:**
1. Tenta usar token do `.env` (`API_EXTERNA_TOKEN`)
2. Se não disponível, faz login com username/password
3. Armazena token em cache
4. Renova automaticamente quando expira

---

## 7. PLATAFORMA RPA

### 7.1 Arquitetura RPA

**Padrão:** Classe base abstrata + Implementações específicas + Concentrador

```
RPABase (abstrato)
    ├── EmbratelRPA
    ├── VivoRPA
    ├── OiRPA
    ├── DigitalNetRPA
    └── SatRPA

ConcentradorRPA
    └── Registra e gerencia todos os RPAs

ServicoRPA
    └── Integra RPA com processos
```

### 7.2 Classe Base RPA

**Arquivo:** `apps/rpa/rpa_base.py`

**Interface:**
```python
class RPABase(ABC):
    @abstractmethod
    def executar_download(self, input_data: InputRPA) -> OutputRPA:
        """Executa download de fatura"""

    @abstractmethod
    def executar_upload_sat(self, input_data: InputRPA) -> OutputRPA:
        """Executa upload para SAT"""

    def validar_input(self, input_data: InputRPA) -> List[str]:
        """Valida dados de entrada"""

    def simular_download_dummy(self, input_data: InputRPA) -> OutputRPA:
        """Simula download para testes"""
```

**Input/Output Padronizados:**
```python
@dataclass
class InputRPA:
    cliente_id: str
    operadora_id: str
    mes_ano: str
    credenciais: Dict[str, Any]
    parametros_especiais: Optional[Dict[str, Any]] = None

@dataclass
class OutputRPA:
    sucesso: bool
    status: StatusExecucao
    mensagem: str
    dados_fatura: Optional[Dict[str, Any]] = None
    erro_tecnico: Optional[str] = None
    tempo_execucao: Optional[float] = None
    timestamp: Optional[datetime] = None
```

### 7.3 Concentrador RPA

**Arquivo:** `apps/rpa/base.py`

**Classe:** `ConcentradorRPA`

**Funcionalidades:**
- Registro automático de todos os RPAs
- Resolução de RPA por código de operadora
- Execução padronizada de operações
- Logging centralizado

**Uso:**
```python
from apps.rpa.base import ConcentradorRPA

concentrador = ConcentradorRPA()
rpa = concentrador.obter_rpa("OI")
resultado = rpa.executar_download(input_data)
```

**RPAs Registrados:**
- `EMBRATEL` → `EmbratelRPA`
- `VIVO` → `VivoRPA`
- `OI` → `OiRPA`
- `DIGITALNET` → `DigitalNetRPA`
- `SAT` → `SatRPA`

### 7.4 Serviço RPA

**Classe:** `ServicoRPA` (`apps/rpa/base.py`)

**Métodos:**
```python
class ServicoRPA:
    def executar_download_processo(self, processo_id: str, usuario_id: str) -> Dict[str, Any]
    def executar_upload_sat_processo(self, processo_id: str, usuario_id: str) -> Dict[str, Any]
    def _criar_parametros_entrada(self, processo: Processo) -> ParametrosEntradaPadrao
    def _atualizar_execucao_com_resultado(self, execucao: Execucao, resultado: ResultadoSaidaPadrao)
```

**Fluxo de Execução:**
1. Busca processo no banco
2. Valida se pode executar
3. Cria registro de Execução
4. Obtém RPA apropriado via Concentrador
5. Executa operação
6. Atualiza Execução com resultado
7. Atualiza Processo se sucesso

### 7.5 Implementações Específicas

#### 7.5.1 EmbratelRPA

**Arquivo:** `apps/rpa/rpas/embratel_rpa.py`

**Status:** Implementação base (pode usar RPA terceirizado)

**Características:**
- Portal: `https://portal.embratel.com.br`
- Autenticação: Login/Senha
- Formato de fatura: PDF

#### 7.5.2 VivoRPA

**Arquivo:** `apps/rpa/rpas/vivo_rpa.py`

**Status:** Implementação base (pode usar RPA terceirizado)

**Características:**
- Portal: `https://portal.vivo.com.br`
- Autenticação: Login/Senha + CPF
- Formato de fatura: PDF

#### 7.5.3 OiRPA

**Arquivo:** `apps/rpa/rpas/oi_rpa.py`

**Status:** Não implementado (usa RPA terceirizado)

**Características:**
- Portal: `https://portal.oi.com.br`
- Autenticação: Filtro/CNPJ
- Formato de fatura: PDF

#### 7.5.4 DigitalNetRPA

**Arquivo:** `apps/rpa/rpas/digitalnet_rpa.py`

**Status:** Implementação base (pode usar RPA terceirizado)

**Características:**
- Portal: `https://portal.digitalnet.com.br`
- Autenticação: Login/Senha
- Formato de fatura: PDF

#### 7.5.5 SatRPA

**Arquivo:** `apps/rpa/rpas/sat_rpa.py`

**Status:** Implementado para upload

**Características:**
- Endpoint: Configurável via operadora SAT
- Operação: Apenas upload (não faz download)
- Autenticação: Token Bearer

### 7.6 Pré-requisitos RPA

**Selenium:**
- ChromeDriver ou GeckoDriver
- Gerenciado via `webdriver-manager`

**Ambiente:**
- Python 3.11+
- Chrome/Chromium ou Firefox instalado
- Variáveis de ambiente configuradas

**Configuração:**
```python
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

driver = webdriver.Chrome(ChromeDriverManager().install())
```

### 7.7 Matriz de Operadoras vs Capacidades

| Operadora | RPA Interno | RPA Terceirizado | Status |
|-----------|-------------|------------------|--------|
| Embratel  | ✅         | ✅               | Ativo  |
| Vivo      | ✅         | ✅               | Ativo  |
| Oi        | ❌         | ✅               | Ativo  |
| DigitalNet| ✅         | ✅               | Ativo  |
| SAT       | ✅         | ✅               | Ativo  |

**Regra de Decisão:**
- Se `operadora.rpa_terceirizado = True` → Usa API externa
- Se `operadora.rpa_terceirizado = False` → Usa RPA interno
- Se RPA interno não implementado → Retorna erro

---

## 8. PROCESSOS DE NEGÓCIO

### 8.1 Ciclo de Vida do Processo

**Estados e Transições:**

```
┌─────────────────────┐
│ AGUARDANDO_DOWNLOAD │ ◄─── Criado (automático ou manual)
└──────────┬──────────┘
           │
           │ RPA executa download com sucesso
           ▼
┌─────────────────────┐
│AGUARDANDO_APROVACAO │
└──────────┬──────────┘
           │
    ┌──────┴──────┐
    │             │
    │ Aprovado    │ Rejeitado
    ▼             ▼
┌──────────┐  ┌──────────┐
│AGUARDANDO│  │AGUARDANDO│
│ENVIO_SAT │  │DOWNLOAD  │
└────┬─────┘  └──────────┘
     │
     │ RPA envia para SAT
     ▼
┌──────────┐
│  UPLOAD  │
│REALIZADO │ ────► Finalizado
└──────────┘
```

### 8.2 Criação Automática de Processos

**Trigger:** Agendamento mensal (dia 1º às 06:00)

**Script:** `criar_agendamentos_padrao.py` ou via interface

**Lógica:**
```python
def criar_processos_mensais():
    mes_ano_atual = f"{datetime.now().month:02d}/{datetime.now().year}"
    clientes_ativos = Cliente.query.filter_by(status_ativo=True).all()

    for cliente in clientes_ativos:
        # Verifica se já existe
        processo_existente = Processo.query.filter_by(
            cliente_id=cliente.id,
            mes_ano=mes_ano_atual
        ).first()

        if not processo_existente:
            processo = Processo(
                cliente_id=cliente.id,
                mes_ano=mes_ano_atual,
                status_processo=StatusProcesso.AGUARDANDO_DOWNLOAD.value,
                criado_automaticamente=True
            )
            db.session.add(processo)

    db.session.commit()
```

### 8.3 Execução de Download

**Iniciadores:**
1. Manual: Usuário clica em "Executar Download"
2. Agendado: Agendamento executa automaticamente
3. API: Endpoint REST para execução

**Fluxo:**
1. Validação de pré-requisitos
   - Processo no status correto
   - Cliente ativo
   - Operadora configurada
   - RPA disponível (interno ou terceirizado)

2. Criação de Execução
   - Registro no banco com status EXECUTANDO
   - Número de tentativa incrementado

3. Execução RPA
   - Se terceirizado: Envia payload para API externa
   - Se interno: Executa Selenium localmente

4. Aguardamento de Resultado
   - Polling de status (API externa)
   - Aguardar conclusão (RPA interno)

5. Atualização de Processo
   - Se sucesso: Atualiza dados da fatura, move para AGUARDANDO_APROVACAO
   - Se falha: Mantém status, permite nova tentativa

### 8.4 Aprovação de Processo

**Atores:** Usuários com perfil APROVADOR ou ADMIN

**Pré-requisitos:**
- Processo com status AGUARDANDO_APROVACAO
- Fatura disponível (url_fatura ou caminho_s3_fatura)
- Dados completos (data_vencimento, valor_fatura)

**Ações Possíveis:**
1. **Aprovar:**
   - Status → AGUARDANDO_ENVIO_SAT
   - Registra aprovador e data
   - Permite envio para SAT

2. **Rejeitar:**
   - Status → AGUARDANDO_DOWNLOAD
   - Remove aprovação
   - Permite novo download

**Interface:**
- Botão "Aprovar" na listagem de processos
- Modal de confirmação
- Campo opcional para observações

### 8.5 Envio para SAT

**Pré-requisitos:**
- Processo aprovado (AGUARDANDO_ENVIO_SAT)
- Fatura disponível
- Cliente vinculado ao SAT

**Fluxo:**
1. Validação de pré-requisitos
2. Criação de Execução (tipo UPLOAD_SAT)
3. Criação de payload SAT
4. Envio para API externa (RPA terceirizado SAT)
5. Aguardamento de confirmação
6. Atualização: Status → UPLOAD_REALIZADO

**Configuração SAT:**
- Operadora com código "SAT"
- `rpa_terceirizado = True`
- `url_endpoint_rpa` configurado
- `rpa_auth_token` configurado

### 8.6 Exceções e Tratamento de Erros

**Erros Comuns:**

1. **Timeout RPA:**
   - Status Execução → TIMEOUT
   - Processo mantém status atual
   - Permite nova tentativa

2. **Credenciais Inválidas:**
   - Status Execução → FALHOU
   - Detalhes no campo `detalhes_erro`
   - Requer correção manual de credenciais

3. **Portal Indisponível:**
   - Status Execução → FALHOU
   - Log detalhado em `mensagem_log`
   - Retry automático configurável

4. **Fatura Não Encontrada:**
   - Status Execução → FALHOU
   - Mensagem: "Fatura não encontrada para o período"
   - Processo mantém status AGUARDANDO_DOWNLOAD

### 8.7 Indicadores de Performance

**KPIs Rastreados:**
- Taxa de sucesso de downloads
- Tempo médio de execução
- Taxa de aprovação
- Taxa de envio SAT bem-sucedido
- Número de tentativas por processo

**Dashboard:**
- `GET /processos/dashboard-monitoramento`
- Estatísticas em tempo real
- Gráficos por operadora
- Histórico de execuções

---

## 9. FRONTEND E UX

### 9.1 Estrutura de Templates

**Layout Base:**
- `templates/layouts/base.html` - Layout principal
- `templates/layouts/base-fullscreen.html` - Layout para autenticação
- `templates/includes/navigation.html` - Menu superior
- `templates/includes/sidebar.html` - Menu lateral
- `templates/includes/scripts.html` - Scripts comuns

**Templates por Módulo:**
- `templates/home/` - Dashboard e páginas estáticas
- `templates/accounts/` - Login e registro
- `templates/clientes/` - Gestão de clientes
- `templates/operadoras/` - Gestão de operadoras
- `templates/processos/` - Gestão de processos
- `templates/usuarios/` - Gestão de usuários
- `templates/agendamentos/` - Gestão de agendamentos
- `templates/notificacoes/` - Notificações
- `templates/relatorios/` - Relatórios

### 9.2 Componentes Frontend

#### 9.2.1 Dashboard de Monitoramento

**Arquivo:** `templates/processos/dashboard_monitoramento.html`

**Funcionalidades:**
- Cards com estatísticas gerais
- Tabela de processos recentes
- Gráficos de status (Morris.js)
- Filtros por operadora, status, período

**JavaScript:** `static/assets/js/monitoramento-rpa.js`

#### 9.2.2 Dashboard API Externa

**Arquivo:** `templates/processos/dashboard_api_externa.html`

**Funcionalidades:**
- Monitoramento em tempo real de jobs
- Indicadores de jobs ativos/concluídos
- Logs em tempo real
- Controles de execução

**JavaScript:** `static/assets/js/api-externa-funcional.js`

#### 9.2.3 Modal de Monitoramento RPA

**Arquivo:** `templates/processos/modal_monitoramento_rpa.html`

**Funcionalidades:**
- Modal com detalhes de execução
- Logs em tempo real via polling
- Indicadores de progresso
- Botões de ação (cancelar, retry)

### 9.3 Convenções de Nomenclatura

**CSS Classes:**
- `btn-{action}` - Botões (btn-primary, btn-success, etc.)
- `badge-{status}` - Badges de status
- `card` - Cards de conteúdo
- `table-{style}` - Tabelas (table-striped, table-hover)

**JavaScript Functions:**
- `{action}{Entity}()` - Ex: `downloadRPA()`, `enviarParaSAT()`
- `{entity}{Action}()` - Ex: `processoAprovar()`

**IDs:**
- `{entity}-{id}-{action}` - Ex: `processo-123-download`

### 9.4 Bibliotecas e Dependências

**CSS:**
- Bootstrap 4.6
- Datta Able Theme
- Feather Icons
- Toastr (notificações)

**JavaScript:**
- jQuery 3.6
- Morris.js (gráficos)
- jQuery Mask (máscaras de input)
- Toastr (notificações)

### 9.5 Responsividade

**Breakpoints:**
- Mobile: < 768px
- Tablet: 768px - 991px
- Desktop: 992px+
- Large: 1200px+

**Classes Responsivas:**
- `d-none d-md-block` - Ocultar em mobile
- `col-12 col-md-6 col-lg-4` - Grid responsivo

---

## 10. JOBS, SCRIPTS E FERRAMENTAS AUXILIARES

### 10.1 Scripts de Inicialização

#### 10.1.1 `create_tables.py`

**Propósito:** Criar todas as tabelas do banco de dados

**Uso:**
```bash
python create_tables.py
```

**Funcionalidades:**
- Cria todas as tabelas via SQLAlchemy
- Não executa migrations (usa `db.create_all()`)

#### 10.1.2 `inicializar_banco.py`

**Propósito:** Inicialização completa do banco

**Uso:**
```bash
python inicializar_banco.py
```

**Funcionalidades:**
- Cria tabelas
- Cria usuário admin padrão
- Cria operadoras padrão
- Cria agendamentos padrão

#### 10.1.3 `criar_usuario_teste.py`

**Propósito:** Criar usuário de teste

**Uso:**
```bash
python criar_usuario_teste.py
```

**Parâmetros:** Configuráveis no código

### 10.2 Scripts de Migração

#### 10.2.1 `migrar_banco_usuarios.py`

**Propósito:** Migrar usuários de sistema legado

**Uso:**
```bash
python migrar_banco_usuarios.py
```

#### 10.2.2 `migrar_agendamentos_operadora.py`

**Propósito:** Associar agendamentos a operadoras

**Uso:**
```bash
python migrar_agendamentos_operadora.py
```

#### 10.2.3 `migrar_operadoras_rpa_terceirizado.py`

**Propósito:** Configurar operadoras para usar RPA terceirizado

**Uso:**
```bash
python migrar_operadoras_rpa_terceirizado.py
```

#### 10.2.4 `migrar_sat_como_operadora.py`

**Propósito:** Criar operadora SAT universal

**Uso:**
```bash
python migrar_sat_como_operadora.py
```

#### 10.2.5 `migrar_remover_campos_obsoletos.py`

**Propósito:** Remover campos obsoletos de modelos

**Uso:**
```bash
python migrar_remover_campos_obsoletos.py
```

### 10.3 Scripts de Agendamento

#### 10.3.1 `criar_agendamentos_padrao.py`

**Propósito:** Criar agendamentos padrão do sistema

**Uso:**
```bash
python criar_agendamentos_padrao.py
```

**Agendamentos Criados:**
- Criar Processos Mensais (dia 1º, 06:00)
- Executar Downloads Automáticos (seg-sex, 08:00)
- Enviar Relatórios Semanais (sexta, 17:00)

#### 10.3.2 `criar_agendamentos_por_operadora.py`

**Propósito:** Criar agendamentos específicos por operadora

**Uso:**
```bash
python criar_agendamentos_por_operadora.py
```

### 10.4 Scripts de Manutenção

#### 10.4.1 `atualizar_status_processos.py`

**Propósito:** Corrigir status de processos inconsistentes

**Uso:**
```bash
python atualizar_status_processos.py
```

**Funcionalidades:**
- Verifica e corrige status baseado em execuções
- Move processos para status correto

#### 10.4.2 `atualizar_codigos_operadoras.py`

**Propósito:** Atualizar códigos de operadoras

**Uso:**
```bash
python atualizar_codigos_operadoras.py
```

#### 10.4.3 `corrigir_json_operadoras.py`

**Propósito:** Corrigir JSON de configuração de operadoras

**Uso:**
```bash
python corrigir_json_operadoras.py
```

#### 10.4.4 `limpar_banco_manter_usuarios.py`

**Propósito:** Limpar banco mantendo apenas usuários

**Uso:**
```bash
python limpar_banco_manter_usuarios.py
```

**⚠️ ATENÇÃO:** Script destrutivo, usar com cuidado

### 10.5 Scripts de Teste

#### 10.5.1 `simular_dados_execucao.py`

**Propósito:** Simular dados de execução para testes

**Uso:**
```bash
python simular_dados_execucao.py
```

#### 10.5.2 `testar_polling_automatico.py`

**Propósito:** Testar sistema de polling de jobs

**Uso:**
```bash
python testar_polling_automatico.py
```

#### 10.5.3 `check_db.py`

**Propósito:** Verificar conexão e estrutura do banco

**Uso:**
```bash
python check_db.py
```

### 10.6 Scripts de Configuração

#### 10.6.1 `configurar_token_api_externa.py`

**Propósito:** Configurar token da API externa

**Uso:**
```bash
python configurar_token_api_externa.py
```

#### 10.6.2 `verificar_usuarios.py`

**Propósito:** Verificar e listar usuários

**Uso:**
```bash
python verificar_usuarios.py
```

### 10.7 Scripts Shell

#### 10.7.1 `build.sh`

**Propósito:** Build da aplicação

**Uso:**
```bash
bash build.sh
```

#### 10.7.2 `deploy_manual.sh`

**Propósito:** Deploy manual passo a passo

**Uso:**
```bash
bash deploy_manual.sh
```

#### 10.7.3 `deploy_ssh.sh`

**Propósito:** Deploy via SSH

**Uso:**
```bash
bash deploy_ssh.sh <host> <user>
```

#### 10.7.4 `build-easypanel.sh`

**Propósito:** Build para Easypanel

**Uso:**
```bash
bash build-easypanel.sh
```

#### 10.7.5 `setup_uv.sh`

**Propósito:** Configurar ambiente UV (gerenciador de pacotes)

**Uso:**
```bash
bash setup_uv.sh
```

#### 10.7.6 `forcar_recarregamento.sh`

**Propósito:** Forçar reload da aplicação

**Uso:**
```bash
bash forcar_recarregamento.sh
```

#### 10.7.7 `limpar_cache_e_reiniciar.sh`

**Propósito:** Limpar cache e reiniciar

**Uso:**
```bash
bash limpar_cache_e_reiniciar.sh
```

---

## 11. MONITORAMENTO, LOGS E NOTIFICAÇÕES

### 11.1 Sistema de Logging

**Configuração:** `run.py` e `apps/__init__.py`

**Níveis:**
- DEBUG - Informações detalhadas de debug
- INFO - Informações gerais
- WARNING - Avisos
- ERROR - Erros
- CRITICAL - Erros críticos

**Formato:**
```python
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)
```

**Uso:**
```python
import logging
logger = logging.getLogger(__name__)

logger.debug("Mensagem de debug")
logger.info("Operação realizada")
logger.warning("Atenção necessária")
logger.error("Erro ocorreu", exc_info=True)
```

### 11.2 Logs de Execução RPA

**Armazenamento:**
- Campo `mensagem_log` na tabela `execucoes`
- Logs detalhados por tentativa
- Inclui timestamps, ações, erros

**Estrutura:**
```
[2025-01-14 10:30:15] Iniciando execução RPA
[2025-01-14 10:30:16] Conectando ao portal...
[2025-01-14 10:30:20] Login realizado com sucesso
[2025-01-14 10:30:25] Buscando fatura para período 01/2025
[2025-01-14 10:30:30] Fatura encontrada
[2025-01-14 10:30:35] Download concluído
```

### 11.3 Monitoramento em Tempo Real

**Endpoint:** `GET /api/externa/tempo-real/status`

**Funcionalidades:**
- Jobs ativos no momento
- Jobs concluídos hoje
- Jobs falhados hoje
- Estatísticas por operadora
- Gráficos de performance

**Atualização:**
- Polling automático a cada 10 segundos (configurável)
- WebSocket (planejado)

### 11.4 Dashboard de Monitoramento

**Rota:** `GET /processos/dashboard-monitoramento`

**Métricas:**
- Total de processos
- Por status
- Por operadora
- Taxa de sucesso
- Tempo médio de execução

**Gráficos:**
- Morris.js para visualização
- Atualização em tempo real

### 11.5 Sistema de Notificações

**Classe:** `NotificationService` (`apps/api_externa/notifications.py`)

**Status:** Parcialmente implementado

**Canais Planejados:**
- ✅ Toastr (notificações web)
- ⏳ Email (planejado)
- ⏳ Slack (planejado)
- ⏳ Telegram (planejado)

**Tipos de Notificação:**
- Download concluído
- Download falhou
- Processo aprovado
- Processo rejeitado
- Envio SAT concluído
- Envio SAT falhou

**Modelo:** `Notificacao` (`apps/models/notificacao.py`)

**Campos:**
- `tipo_notificacao` - Tipo
- `destinatario_id` - Usuário destinatário
- `mensagem` - Mensagem
- `status_envio` - Status do envio
- `data_envio` - Data de envio

---

## 12. SEGURANÇA E COMPLIANCE

### 12.1 Autenticação

**Framework:** Flask-Login

**Métodos:**
- Login por username/password
- OAuth GitHub (opcional, configurável)

**Sessão:**
- Baseada em cookies
- CSRF protection habilitado
- Timeout configurável

**Senhas:**
- Hash com Werkzeug (PBKDF2)
- Não armazenadas em texto plano
- Validação de força (planejado)

### 12.2 Autorização

**Perfis:**
- ADMIN - Acesso total
- APROVADOR - Aprovação de processos
- OPERADOR - Execução de operações

**Decoração:**
```python
from flask_login import login_required

@blueprint.route('/rota')
@login_required
def minha_rota():
    # Verifica se usuário está logado
    pass
```

**Verificação de Permissões:**
```python
if not current_user.tem_permissao('aprovar_processos'):
    flash('Sem permissão', 'error')
    return redirect(url_for('home.index'))
```

### 12.3 CSRF Protection

**Framework:** Flask-WTF

**Configuração:**
- Habilitado globalmente
- Timeout: 3600 segundos (1 hora)
- Token em todos os formulários

**Uso:**
```html
<form method="POST">
    {{ csrf_token() }}
    <!-- campos -->
</form>
```

**AJAX:**
```javascript
headers: {
    'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
}
```

### 12.4 Proteção de Dados Sensíveis

**Credenciais:**
- Senhas de portal: Criptografadas (planejado)
- Tokens API: Armazenados em `.env`
- Não expostos em logs

**Dados Pessoais:**
- CNPJ, CPF: Armazenados mas não expostos desnecessariamente
- LGPD compliance (planejado)

### 12.5 Validação de Entrada

**Formulários:**
- WTForms para validação
- Sanitização de dados
- Validação de tipos

**APIs:**
- Pydantic para validação de payloads
- Validação de tipos
- Validação de formato

### 12.6 SQL Injection

**Proteção:**
- SQLAlchemy ORM (proteção automática)
- Nunca concatenação de strings
- Parâmetros nomeados

**Exemplo Correto:**
```python
# ✅ Correto
Processo.query.filter_by(cliente_id=cliente_id).all()

# ❌ Errado
query = f"SELECT * FROM processos WHERE cliente_id = {cliente_id}"
```

### 12.7 Auditoria

**Rastreamento:**
- `data_criacao` e `data_atualizacao` em todos os modelos
- `executado_por_usuario_id` em execuções
- `aprovado_por_usuario_id` em processos
- Logs de ações críticas

**Logs de Auditoria:**
- Ações de usuários
- Mudanças de status
- Aprovações/rejeições
- Exclusões

---

## 13. QUALIDADE E TESTES

### 13.1 Estrutura de Testes

**Framework:** pytest

**Configuração:** `pyproject.toml`

**Marcadores:**
- `@pytest.mark.unit` - Testes unitários
- `@pytest.mark.integration` - Testes de integração
- `@pytest.mark.slow` - Testes lentos

**Execução:**
```bash
pytest                    # Todos os testes
pytest -m unit           # Apenas unitários
pytest -m "not slow"     # Excluir lentos
pytest --cov=apps        # Com cobertura
```

### 13.2 Cobertura de Testes

**Status Atual:** ⚠️ Baixa cobertura (melhorias necessárias)

**Ferramenta:** pytest-cov

**Meta:** 80%+ de cobertura

**Execução:**
```bash
pytest --cov=apps --cov-report=html
```

### 13.3 Testes Unitários

**Exemplos:**
- Testes de modelos
- Testes de validações
- Testes de métodos de negócio

**Estrutura:**
```
tests/
├── unit/
│   ├── test_models.py
│   ├── test_services.py
│   └── test_utils.py
```

### 13.4 Testes de Integração

**Exemplos:**
- Testes de rotas
- Testes de fluxos completos
- Testes de integração com API externa

**Estrutura:**
```
tests/
├── integration/
│   ├── test_routes.py
│   ├── test_api_externa.py
│   └── test_workflows.py
```

### 13.5 Testes de API Externa

**Arquivo:** `APISEXTERNAS/TESTES/test_integracao_rpa.py`

**Funcionalidades:**
- Testes de endpoints
- Testes de payloads
- Testes de autenticação

### 13.6 Qualidade de Código

**Ferramentas:**
- `black` - Formatação
- `isort` - Ordenação de imports
- `flake8` - Linting
- `mypy` - Type checking
- `ruff` - Linter rápido

**Configuração:** `pyproject.toml`

**Execução:**
```bash
black apps/
isort apps/
flake8 apps/
mypy apps/
ruff check apps/
```

### 13.7 Pre-commit Hooks

**Status:** Planejado

**Configuração:**
- `pre-commit` framework
- Hooks para black, isort, flake8
- Validação antes de commit

---

## 14. GOVERNANÇA DE CÓDIGO

### 14.1 Padrões de Código

**Documentação:** `DOCUMENTACAO_PADROES_DESENVOLVIMENTO.md`

**Principais Regras:**
- Código em português brasileiro
- Docstrings em português
- Tipagem forte quando possível
- PEP 8 para Python
- Nomenclatura: Classes (PascalCase), Funções (snake_case)

### 14.2 Estrutura de Commits

**Formato Sugerido:**
```
tipo: descrição curta

Descrição detalhada (opcional)

Fixes: #123
```

**Tipos:**
- `feat:` - Nova funcionalidade
- `fix:` - Correção de bug
- `docs:` - Documentação
- `refactor:` - Refatoração
- `test:` - Testes
- `chore:` - Manutenção

### 14.3 Branching Strategy

**Branches:**
- `main` - Produção
- `develop` - Desenvolvimento
- `feature/` - Features
- `fix/` - Correções
- `hotfix/` - Hotfixes

### 14.4 Code Review

**Processo:**
1. Criar branch de feature
2. Desenvolver e testar
3. Abrir Pull Request
4. Code review
5. Merge após aprovação

**Checklist:**
- ✅ Código segue padrões
- ✅ Testes passam
- ✅ Documentação atualizada
- ✅ Sem breaking changes
- ✅ Performance considerada

### 14.5 Dependências

**Gerenciamento:**
- `requirements.txt` - Dependências principais
- `pyproject.toml` - Dependências com versões
- `uv.lock` - Lock file (UV)

**Atualização:**
```bash
pip install -r requirements.txt
# ou
uv pip install -r requirements.txt
```

---

## 15. ROADMAP E HISTÓRICO

### 15.1 Histórico de Implementações

**Fase 1 - Análise Estrutural:**
- ✅ Análise de arquitetura
- ✅ Identificação de problemas
- ✅ Sugestões de melhorias

**Fase 2 - Módulos Principais:**
- ✅ Implementação de modelos
- ✅ Sistema de autenticação
- ✅ CRUD de entidades principais

**Fase 3 - Módulos Especializados:**
- ✅ Integração API externa
- ✅ Sistema RPA
- ✅ Monitoramento em tempo real
- ✅ Agendamentos

**Melhorias Implementadas:**
- ✅ Logs detalhados de execução
- ✅ Monitoramento em tempo real
- ✅ Dashboard de estatísticas
- ✅ Sistema de agendamentos por operadora
- ✅ SAT como operadora universal
- ✅ RPA terceirizado como padrão

### 15.2 Melhorias Pendentes

**Curto Prazo:**
- ⏳ Testes automatizados completos
- ⏳ Notificações omnicanal (Email, Slack, Telegram)
- ⏳ Otimização de queries
- ⏳ Cache de consultas frequentes
- ⏳ Documentação de API REST

**Médio Prazo:**
- ⏳ Sistema de filas (Celery + Redis)
- ⏳ WebSocket para tempo real
- ⏳ Dashboard de analytics avançado
- ⏳ Exportação de relatórios (PDF, Excel)
- ⏳ API REST completa

**Longo Prazo:**
- ⏳ Microserviços (separação de RPA)
- ⏳ Kubernetes deployment
- ⏳ CI/CD completo
- ⏳ Monitoramento com Prometheus/Grafana
- ⏳ Backup automático

### 15.3 Issues Conhecidas

**1. RPA Interno Não Implementado:**
- OiRPA não implementado
- Dependência de RPA terceirizado

**2. Testes Incompletos:**
- Baixa cobertura de testes
- Falta testes de integração

**3. Performance:**
- Queries N+1 em alguns endpoints
- Falta de cache em consultas frequentes

**4. Notificações:**
- Apenas Toastr implementado
- Email/Slack/Telegram pendentes

### 15.4 Decisões Técnicas Importantes

**1. UUID como ID:**
- Facilita distribuição
- Evita conflitos
- Compatibilidade PostgreSQL/SQLite

**2. Status-Based Workflow:**
- Estados explícitos
- Transições controladas
- Auditoria completa

**3. RPA Terceirizado:**
- Escalabilidade
- Manutenção simplificada
- Menor carga no servidor

**4. Execuções Separadas:**
- Histórico completo
- Análise de falhas
- Suporte a retry

---

## ANEXOS

### A.1 Checklist de Handover

**Ambiente:**
- [ ] Variáveis de ambiente configuradas
- [ ] Banco de dados inicializado
- [ ] Usuários criados
- [ ] Operadoras configuradas
- [ ] API externa configurada

**Documentação:**
- [ ] Documentação lida
- [ ] Playbooks revisados
- [ ] Scripts de migração conhecidos
- [ ] Processos de deploy entendidos

**Código:**
- [ ] Estrutura de pastas compreendida
- [ ] Modelos de dados mapeados
- [ ] Fluxos principais entendidos
- [ ] Integrações conhecidas

### A.2 Contatos e Recursos

**Repositório:**
- GitHub: `begtelecomunicacoes/tirus-dash-flask`

**Documentação Adicional:**
- `DOCUMENTACAO_PADROES_DESENVOLVIMENTO.md`
- `PLAYBOOKS/` - Playbooks detalhados por módulo
- `APISEXTERNAS/` - Documentação de APIs externas

**Suporte:**
- Email: tiago@begtelecomunicacoes.com.br

---

**FIM DA DOCUMENTAÇÃO GLOBAL COMPLETA**

**Versão:** 1.0.0
**Última Atualização:** 2025-01-14
