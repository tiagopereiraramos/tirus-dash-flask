
# 📋 BRM Faturas - Memória Técnica e Status do Projeto

## 1️⃣ Sumário Executivo

### Status Atual do Projeto
- **Projeto:** Sistema BRM Faturas - Gestão de Processos de Download e Envio de Faturas para SAT
- **Versão:** 1.0 (Em Desenvolvimento)
- **Tecnologia Principal:** Flask (Python)
- **Status Geral:** 🟡 Em Desenvolvimento Ativo

### CRUDs Concluídos e Homologados ✅
1. **Operadoras** - 100% Completo
   - CRUD completo com validações
   - Interface responsiva
   - Integração com outras entidades

2. **Clientes** - 100% Completo
   - CRUD completo com relacionamentos
   - Importação em massa via CSV
   - Validações de CNPJ e unicidade

3. **Processos** - 95% Completo
   - CRUD principal com workflow de status
   - Aprovação e rejeição
   - Envio para SAT
   - Sistema de visualização de faturas

4. **Usuários** - 80% Completo
   - Autenticação JWT
   - Controle de acesso básico

### Pendências Principais 🔄
- Finalização do sistema de visualização de faturas
- Implementação completa de roles/permissões
- Sistema de logs e auditoria
- Testes automatizados

---

## 2️⃣ Arquitetura Técnica

### Stack Tecnológica
```
Frontend: Bootstrap 4 + jQuery + Templates Jinja2
Backend: Flask + SQLAlchemy + PostgreSQL/SQLite
Auth: JWT (JSON Web Tokens)
CSS: Custom CSS + Dark Mode
Icons: Feather Icons + Font Awesome
```

### Estrutura do Projeto
```
apps/
├── authentication/     # Módulo de autenticação
├── clientes/          # CRUD de Clientes
├── operadoras/        # CRUD de Operadoras
├── processos/         # CRUD de Processos (Principal)
├── home/              # Dashboard e página inicial
├── models/            # Modelos de dados
├── static/            # Assets estáticos
└── templates/         # Templates HTML
```

### Banco de Dados
- **Desenvolvimento:** SQLite (`apps/db.sqlite3`)
- **Produção:** PostgreSQL (configurável)
- **ORM:** SQLAlchemy com migrations automáticas

---

## 3️⃣ Estrutura de Rotas (Routes)

### Padrão de URLs Adotado
```
/                          # Dashboard principal
/login                     # Autenticação
/operadoras/              # Lista de operadoras
/operadoras/novo          # Criar operadora
/operadoras/editar/<id>   # Editar operadora
/operadoras/visualizar/<id> # Detalhes operadora
/clientes/                # Lista de clientes
/clientes/novo            # Criar cliente
/clientes/editar/<id>     # Editar cliente
/clientes/importar        # Importação CSV
/processos/               # Lista de processos
/processos/novo           # Criar processo
/processos/visualizar/<id> # Detalhes processo
/processos/aprovar/<id>   # Aprovar processo (POST)
/processos/rejeitar/<id>  # Rejeitar processo (POST)
/processos/enviar-sat/<id> # Enviar para SAT (POST)
```

### Verbos HTTP Utilizados
- **GET:** Listagem, visualização, formulários
- **POST:** Criação, ações específicas (aprovar, rejeitar)
- **Não implementado:** PUT, PATCH, DELETE (uso de POST para simplicidade)

---

## 4️⃣ Modelagem dos CRUDs

### Entidade: Operadoras
```sql
CREATE TABLE operadoras (
    id UUID PRIMARY KEY,
    nome VARCHAR(255) NOT NULL UNIQUE,
    url_portal VARCHAR(255),
    observacoes TEXT,
    status_ativo BOOLEAN DEFAULT TRUE,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Regras de Negócio:**
- Nome deve ser único
- URL do portal é opcional
- Status ativo controla visibilidade

### Entidade: Clientes
```sql
CREATE TABLE clientes (
    id UUID PRIMARY KEY,
    razao_social VARCHAR(255) NOT NULL,
    nome_sat VARCHAR(255) NOT NULL,
    cnpj VARCHAR(20) NOT NULL,
    operadora_id UUID REFERENCES operadoras(id),
    filtro VARCHAR(255),
    servico VARCHAR(255),
    dados_sat TEXT,
    unidade VARCHAR(100) NOT NULL,
    site_emissao VARCHAR(255),
    login_portal VARCHAR(100),
    senha_portal VARCHAR(100),
    cpf VARCHAR(20),
    status_ativo BOOLEAN DEFAULT TRUE,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (cnpj, operadora_id, unidade, servico)
);
```

**Regras de Negócio:**
- CNPJ deve ser válido e único por operadora/unidade/serviço
- Relacionamento obrigatório com operadora
- Dados SAT armazenados em JSON text

### Entidade: Processos (Principal)
```sql
CREATE TABLE processos (
    id UUID PRIMARY KEY,
    cliente_id UUID REFERENCES clientes(id),
    mes_ano VARCHAR(7) NOT NULL,
    status_processo VARCHAR(50) DEFAULT 'AGUARDANDO_DOWNLOAD',
    url_fatura VARCHAR(500),
    caminho_s3_fatura VARCHAR(500),
    data_vencimento DATE,
    valor_fatura DECIMAL(15,2),
    aprovado_por_usuario_id UUID,
    data_aprovacao TIMESTAMP,
    enviado_para_sat BOOLEAN DEFAULT FALSE,
    data_envio_sat TIMESTAMP,
    upload_manual BOOLEAN DEFAULT FALSE,
    criado_automaticamente BOOLEAN DEFAULT TRUE,
    observacoes TEXT,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (cliente_id, mes_ano)
);
```

**Status do Processo (Workflow):**
1. `AGUARDANDO_DOWNLOAD` - Processo criado, aguarda download da fatura
2. `AGUARDANDO_APROVACAO` - Fatura baixada, aguarda aprovação
3. `AGUARDANDO_ENVIO_SAT` - Processo aprovado, aguarda envio para SAT
4. `UPLOAD_REALIZADO` - Processo concluído

**Regras de Negócio:**
- Um processo por cliente por mês/ano
- Workflow sequencial de status
- Aprovação requer usuário autenticado
- Dados de fatura obrigatórios para aprovação

---

## 5️⃣ Padrões de Interface (Frontend)

### Layout das Páginas
- **Header:** Logo, menu de navegação, perfil do usuário
- **Sidebar:** Menu lateral colapsível com dark mode
- **Breadcrumb:** Navegação hierárquica
- **Cards:** Conteúdo organizado em cards Bootstrap

### Padrões de Listagem
```html
- Filtros de busca no topo
- Tabela responsiva com ações
- Paginação no rodapé
- Botões de ação: Ver, Editar, Ações específicas
- Estados visuais (badges coloridos para status)
```

### Padrões de Formulário
```html
- Formulários em cards
- Validação client-side e server-side
- Mensagens de feedback (success, danger, warning)
- Campos obrigatórios marcados
- Botões: Salvar, Cancelar, Voltar
```

### Componentes Reutilizáveis
- **Modais:** Confirmação de ações, aprovação/rejeição
- **Badges:** Status coloridos
- **Tooltips:** Informações adicionais
- **Alerts:** Mensagens de feedback

---

## 6️⃣ Padrões de Backend

### Estrutura de APIs
```python
# Padrão de Response JSON
{
    "success": true|false,
    "message": "Mensagem descritiva",
    "data": {...} # Opcional
}

# Status Codes
200 - Sucesso
400 - Erro de validação
404 - Não encontrado
500 - Erro interno
```

### Tratamento de Erros
```python
try:
    # Operação
    db.session.commit()
    flash('Sucesso!', 'success')
except Exception as e:
    db.session.rollback()
    logger.error(f"Erro: {str(e)}")
    flash('Erro interno', 'danger')
```

### Segurança
- **Autenticação:** JWT com decorador `@verify_user_jwt`
- **Autorização:** Controle básico por rotas
- **Validação:** SQLAlchemy + WTForms
- **CSRF:** Token CSRF em formulários

### Logs
```python
import logging
logger = logging.getLogger(__name__)

# Padrões de log
logger.info("Operação realizada: %s", detalhes)
logger.error("Erro: %s", str(e))
logger.debug("Debug info: %s", dados)
```

---

## 7️⃣ Fluxos e Rotinas Automatizadas

### Workflow de Processos
```mermaid
AGUARDANDO_DOWNLOAD → AGUARDANDO_APROVACAO → AGUARDANDO_ENVIO_SAT → UPLOAD_REALIZADO
```

### Criação de Processos Mensais
- **Rota:** `/processos/criar-processos-mensais`
- **Funcionalidade:** Criação em massa de processos para um mês/ano
- **Filtros:** Por operadora (opcional)
- **Regra:** Não duplica processos existentes

### Importação de Clientes
- **Rota:** `/clientes/importar`
- **Formato:** CSV com colunas específicas
- **Validação:** CNPJ, unicidade, relacionamentos

---

## 8️⃣ Referências ao Manual-App

### Alinhamentos com Manual-App
- ✅ Estrutura modular por funcionalidade
- ✅ Separação de responsabilidades (routes, models, forms)
- ✅ Nomenclatura consistente
- ✅ Uso de UUID como chave primária
- ✅ Timestamps automáticos (created_at, updated_at)

### Desvios Justificados
- **Templates Jinja2:** Ao invés de SPA, pela simplicidade do projeto
- **jQuery:** Ao invés de framework moderno, por compatibilidade
- **SQLite em dev:** Facilita desenvolvimento local

---

## 9️⃣ Considerações Finais

### Recomendações Técnicas
1. **Implementar testes unitários** para models e routes principais
2. **Adicionar sistema de logs robusto** com rotação
3. **Implementar cache** para consultas frequentes
4. **Melhorar tratamento de erros** com páginas customizadas
5. **Adicionar monitoramento** de performance

### Riscos Conhecidos
- **Dependência de jQuery:** Biblioteca não mais mantida ativamente
- **Falta de testes:** Pode gerar regressões
- **Autenticação simples:** Não há renovação automática de tokens

### Próximos Passos
1. **Finalizar visualização de faturas** - Resolver erros JavaScript
2. **Implementar sistema de roles** completo
3. **Adicionar auditoria** de ações dos usuários
4. **Melhorar UX** com loading states e feedback visual
5. **Documentar APIs** para integrações futuras

---

## 📊 Métricas do Projeto

| Métrica | Valor |
|---------|-------|
| Linhas de código Python | ~2.500 |
| Templates HTML | 15+ |
| Rotas implementadas | 25+ |
| Modelos de dados | 6 |
| Funcionalidades principais | 4 CRUDs |
| Cobertura de testes | 0% (A implementar) |

---

## 🔗 Links e Referências

- **Repositório:** [Replit Workspace]
- **Documentação Flask:** https://flask.palletsprojects.com/
- **SQLAlchemy:** https://sqlalchemy.org/
- **Bootstrap 4:** https://getbootstrap.com/docs/4.0/

---

*Documento gerado em: 06/06/2025*  
*Última atualização: Status dos CRUDs e pendências técnicas*
