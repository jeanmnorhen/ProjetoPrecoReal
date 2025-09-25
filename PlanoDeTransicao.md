# Plano de Transição para o Novo Dashboard Administrativo

## 1. Visão Geral

Este documento descreve os passos necessários para adaptar o projeto "PREÇO REAL" às novas diretrizes de documentação, que redefinem o painel administrativo como um dashboard de inteligência e gestão de catálogo.

## 2. Backend (Microsserviços)

As seguintes alterações são necessárias para suportar as novas funcionalidades do frontend.

### 2.1. `servico-usuarios`

*   **[TAREFA] Criar endpoint para críticas de produtos:**
    *   `POST /api/criticas`: Endpoint para receber críticas de produtos enviadas pelos usuários do aplicativo móvel.
    *   **Payload:** `{ "produto_id": "...", "tipo_critica": "...", "comentario": "..." }`
    *   A crítica deve ser salva no banco de dados com o status "pendente".

### 2.2. `servico-produtos`

*   **[REVISÃO] Fortalecer o CRUD de produtos canônicos:**
    *   Garantir que o CRUD existente (`GET`, `POST`, `PUT`, `DELETE /api/produtos`) suporta todos os campos necessários (descrição detalhada, foto de alta qualidade, código de barras).
    *   O endpoint `PUT /api/produtos/<id>` será fundamental para o admin corrigir os dados a partir das críticas.

### 2.3. `servico-monitoramento`

*   **[TAREFA] Criar endpoints para o dashboard:**
    *   `GET /api/metricas/uso`: Retornar dados para os widgets de uso do aplicativo (ex: usuários ativos, pesquisas por dia).
    *   `GET /api/metricas/precos`: Retornar dados para o gráfico de média de preços, com capacidade de filtrar por produto e região.

## 3. Frontend (Dashboard Administrativo)

Esta é a maior frente de trabalho. A implementação será dividida em fases.

### Fase 1: Estrutura Base e Widgets

*   **[TAREFA] Adaptar o layout:** Transformar o `frontend-tester` no novo layout de dashboard com `Navbar` e `Sidebar`.
*   **[TAREFA] Desenvolver a página principal (`/admin/dashboard`):**
    *   Implementar os `StatCard`s para métricas chave.
    *   Integrar com o `servico-monitoramento` para exibir os gráficos `PriceTrendChart` and `UsageChart`.

### Fase 2: Gestão de Críticas

*   **[TAREFA] Desenvolver a página `/admin/criticas`:**
    *   Implementar a `CriticismQueueTable` para listar as críticas pendentes.
    *   Desenvolver o `CriticismResolutionModal` que permite ao admin visualizar a crítica e editar o produto canônico diretamente, consumindo a API do `servico-produtos`.

### Fase 3: Gestão do Catálogo

*   **[TAREFA] Desenvolver a página `/admin/canonicos`:**
    *   Implementar a `CanonicalProductsTable` com busca e filtro.
    *   Desenvolver o `ProductFormModal` para criar e editar produtos canônicos.

## 4. Frontend (Aplicativo Móvel)

*   **[TAREFA] Implementar a funcionalidade "Reportar Problema":**
    *   Adicionar o botão na tela de detalhes do produto.
    *   Criar o modal com o formulário de crítica.
    *   Integrar com o novo endpoint `POST /api/criticas` no `servico-usuarios`.

## 5. Ordem de Implementação Sugerida

1.  **Backend:** Implementar as novas APIs nos serviços (`servico-usuarios` e `servico-monitoramento`).
2.  **Frontend Admin (Fase 1):** Estruturar o dashboard e os widgets.
3.  **Frontend Admin (Fase 2 & 3):** Implementar as funcionalidades de gestão de críticas e catálogo.
4.  **Frontend Mobile:** Adicionar a funcionalidade de reporte de problemas.
