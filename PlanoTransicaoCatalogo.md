### **Plano de Transição: Reformulação do Gerenciamento de Catálogo Canônico com IA**

#### 1. Visão Geral e Objetivo

O objetivo é substituir o atual "Gerenciamento de Produtos Canônicos" por um "Alimentador de Catálogo" inteligente. Este novo sistema usará o Google Gemini para ativamente popular e enriquecer o catálogo de produtos canônicos, minimizando o trabalho manual e garantindo dados de alta qualidade (nome, categorias, descrição, imagem) para os lojistas. O processo será centrado em um fluxo de "envio para aprovação", onde os administradores validam os dados gerados pela IA.

#### 2. Análise de Impacto e Arquitetura

A nova rotina impactará três componentes principais:

1.  **`servico-agentes-ia` (Ampliação):** Deixará de ser apenas um consumidor de tarefas assíncronas para se tornar o cérebro do processo. Ele receberá as solicitações do dashboard, orquestrará as chamadas ao Gemini e se comunicará com o `servico-produtos`.
2.  **`servico-produtos` (Expansão):** O banco de dados e a API precisarão ser expandidos para suportar o conceito de "status de aprovação" e o gerenciamento de múltiplas imagens por produto.
3.  **`frontend-tester` (Reformulação):** A interface de gerenciamento de produtos será completamente redesenhada para acomodar a nova busca unificada, o fluxo de trabalho assíncrono (enquanto a IA trabalha) e a nova tela de "Fila de Aprovação".

#### 3. Plano de Implementação (Fases)

**Fase 1: Backend - Expansão do `servico-produtos`**

O alicerce. Precisamos preparar o banco de dados e a API para receber os novos dados.

*   **Schema do Banco de Dados (PostgreSQL):**
    1.  Adicionar uma coluna `status` à tabela `canonical_products` (ex: `pending_approval`, `approved`, `rejected`).
    2.  Criar uma nova tabela `product_images` (`id`, `product_id`, `image_url`, `source`, `is_primary`, `status`). Isso permitirá associar múltiplas imagens a um produto para que o admin escolha a melhor.

*   **API do `servico-produtos`:**
    1.  Criar novos endpoints para administradores:
        *   `POST /api/products/{id}/approve`: Muda o status do produto para `approved`.
        *   `POST /api/products/{id}/reject`: Muda o status do produto para `rejected`.
        *   `GET /api/products/pending`: Lista todos os produtos com status `pending_approval`.
        *   `POST /api/images/{image_id}/set-primary`: Define uma imagem como a principal para um produto.

**Fase 2: Backend - Ampliação do `servico-agentes-ia`**

O cérebro da operação. Implementação da nova lógica de IA.

*   **Novos Endpoints na API:**
    1.  `POST /api/agents/catalog-intake`: Este será o endpoint principal que o frontend irá chamar. Ele aceitará um corpo de requisição com `text_query` (nome ou categoria) ou `image_base64`.

*   **Lógica Interna do `catalog-intake`:**
    1.  **Recebimento:** Recebe a consulta (texto ou imagem).
    2.  **Busca Interna:** Primeiro, busca no `servico-busca` para verificar se um produto similar já existe no catálogo canônico.
    3.  **Cenário 1: Produto Encontrado.**
        *   Se a consulta foi uma imagem, o `servico-agentes-ia` irá salvá-la via `servico-produtos` como uma imagem candidata (`status: 'pending_review'`) para o produto existente.
        *   Retorna os dados do produto encontrado para o frontend.
    4.  **Cenário 2: Produto NÃO Encontrado.**
        *   **Prompt para Gemini:** Cria um prompt detalhado para o Gemini, pedindo para gerar: `nome`, `descrição detalhada` e uma lista de `categorias` relevantes, com base no texto ou imagem.
        *   **Salvar para Aprovação:** Envia os dados gerados pela IA (nome, descrição, categorias) e a imagem para o `servico-produtos`, que irá criar um novo produto com `status: 'pending_approval'`.
        *   Retorna uma resposta imediata ao frontend com um `task_id`, informando que o produto está sendo processado.
    5.  **Cenário 3: Categoria Recebida.**
        *   Se a consulta for uma categoria (ex: "chocolates"), o serviço usará o Gemini com o prompt "liste 10 produtos populares na categoria 'chocolates', com nome e descrição".
        *   Para cada um dos 10 produtos, ele irá criar um registro com `status: 'pending_approval'` no `servico-produtos`.

**Fase 3: Frontend - Reformulação do Dashboard (UI/UX)**

A interface para o administrador.

1.  **Página "Alimentador de Catálogo":**
    *   Substituir a página atual de "Gerenciamento de Produtos Canônicos".
    *   **Componente Principal:** Uma barra de pesquisa proeminente que aceita texto ou upload de imagem.
    *   **Área de Resultados:**
        *   Se um produto existente é encontrado, ele é exibido com um botão "Editar".
        *   Se um novo produto está sendo gerado, exibe uma mensagem de status como "🔍 Processando... A IA está gerando os detalhes do novo produto."

2.  **Nova Página/Componente: "Fila de Aprovação"**
    *   Consome o endpoint `GET /api/products/pending` do `servico-produtos`.
    *   Exibe uma tabela com os produtos pendentes (nome, categorias, status).
    *   Cada item terá um botão "Revisar".

3.  **Modal/Tela de Revisão:**
    *   Ao clicar em "Revisar", abre uma tela onde o administrador vê todos os dados gerados pelo Gemini (nome, descrição, categorias) e a(s) imagem(ns).
    *   O admin pode editar qualquer campo.
    *   Se houver múltiplas imagens, ele pode selecionar a principal.
    *   Botões "Aprovar" e "Rejeitar" que chamam os respectivos endpoints no `servico-produtos`.

#### 4. Resumo das Mudanças

*   **Banco de Dados:** Adição da coluna `status` em `canonical_products` e nova tabela `product_images`.
*   **`servico-produtos`:** Novos endpoints para listar pendências e gerenciar aprovações/imagens.
*   **`servico-agentes-ia`:** Novo endpoint principal (`catalog-intake`) e lógica de orquestração com Gemini.
*   **Frontend:** UI redesenhada com foco em busca, status de tarefas assíncronas e uma nova fila de moderação/aprovação.
