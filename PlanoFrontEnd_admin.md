# Plano de Desenvolvimento do Frontend - Dashboard Administrativo

## 1. Visão Geral

O painel administrativo será um dashboard centralizado, construído com Next.js e Tailwind CSS, projetado para fornecer aos administradores uma visão completa do ecossistema do "PREÇO REAL". O foco é monitorar a saúde da plataforma, gerenciar o catálogo de produtos e garantir a qualidade dos dados.

## 2. Autenticação

- Acesso restrito a usuários com o status de `admin` no Firebase Authentication.
- Utilização de um `Higher-Order Component` (HOC) `withAdminAuth` para proteger todas as rotas do dashboard.

## 3. Estrutura de Páginas e Componentes

### 3.1. Layout Principal (`/admin/layout.tsx`)

- **Navbar Superior:** Exibirá o logo, o nome do usuário logado e um botão de logout.
- **Sidebar (Navegação Lateral):** Conterá links para as principais seções do dashboard:
  - Dashboard
  - Gestão de Críticas
  - Catálogo de Produtos (Canônicos)
  - Lojas
  - Usuários
  - Ofertas

### 3.2. Página Principal (`/admin/dashboard`)

Esta página fornecerá uma visão geral com widgets interativos.

- **Componentes:**
  - `StatCard`: Componente reutilizável para exibir métricas chave (ex: "Usuários Ativos", "Ofertas Criadas").
  - `PriceTrendChart`: Gráfico de linhas (usando Recharts ou similar) para monitorar a média de preços de um produto selecionado ao longo do tempo. O admin poderá filtrar por produto e por região.
  - `UsageChart`: Gráfico de barras ou linhas para visualizar a atividade dos usuários (ex: pesquisas por dia, produtos mais buscados).

### 3.3. Gestão de Críticas de Produtos (`/admin/criticas`)

Interface para gerenciar o feedback dos usuários sobre a qualidade dos dados dos produtos.

- **Componentes:**
  - `CriticismQueueTable`: Tabela que exibe uma fila de produtos com críticas pendentes. Colunas: Produto, Tipo de Crítica (ex: "Foto errada"), Comentário do Usuário, Data.
  - `CriticismResolutionModal`: Ao clicar em um item da fila, um modal será aberto para o administrador:
    - Exibirá os dados atuais do produto canônico.
    - Mostrará a sugestão/crítica do usuário.
    - Permitirá ao admin **editar diretamente** os campos do produto canônico (descrição, foto, etc.) e salvar a alteração.
    - Um botão para "Rejeitar" a crítica.

### 3.4. Catálogo de Produtos Canônicos (`/admin/canonicos`)

Gerenciamento completo do catálogo de produtos, que é a base para as ofertas dos lojistas.

- **Componentes:**
  - `SearchAndFilterBar`: Barra com campo de busca textual e filtros por categoria.
  - `CanonicalProductsTable`: Tabela com a lista de produtos canônicos. Colunas: Foto, Nome do Produto, Categoria, Código de Barras, Ações.
  - `ProductFormModal`: Um modal para **criar** e **editar** produtos canônicos. O formulário conterá campos para:
    - Nome do produto
    - Descrição detalhada
    - Categoria (seleção)
    - Código de barras (EAN/UPC)
    - Upload de imagem de alta qualidade.
  - `AlertDialog`: Para confirmação antes de excluir um produto.

### 3.5. Gestão de Lojas, Usuários e Ofertas

As seções de Lojas (`/admin/lojas`), Usuários (`/admin/usuarios`) e Ofertas (`/admin/ofertas`) consistirão em páginas de CRUD (Criar, Ler, Atualizar, Deletar) mais simples, utilizando tabelas para listar os dados e modais para edição e criação.

- **Componentes reutilizáveis:**
  - `DataTable`: Tabela genérica com funcionalidades de paginação e ordenação.
  - `FormModal`: Modal genérico para formulários de edição/criação.

## 4. Lógica e Estado

- **Gerenciamento de Estado:** Utilização do `AuthContext` para informações de autenticação. Para o estado das páginas (dados de tabelas, filtros), o estado local do React (`useState`, `useReducer`) será suficiente inicialmente.
- **Comunicação com API:** Todas as chamadas para os microsserviços de backend serão centralizadas e gerenciadas através de um `ApiService` ou hooks customizados (ex: `useApi`).

## 5. Objetivo Final

O dashboard deve capacitar os administradores a manter um catálogo de produtos de alta qualidade, garantindo que os lojistas tenham uma experiência fluida ao criar ofertas, focando apenas no preço e na quantidade, enquanto os consumidores recebem informações precisas e confiáveis.