# Plano de Implementação do Aplicativo Móvel (React Native)

## 1. Visão Geral

Este documento detalha o plano de desenvolvimento para o **Aplicativo Móvel** do projeto Preço Real, construído com **React Native**. O aplicativo atenderá a três perfis de usuários principais: **Consumidores**, **Lojistas** e **Funcionários**.

-   **Para Consumidores:** O foco é na descoberta de ofertas, busca de produtos (incluindo busca por imagem), e visualização de lojas em um mapa interativo.
-   **Para Lojistas:** O foco é no gerenciamento de **uma ou mais de suas lojas**, cadastro de produtos, publicação de ofertas e gestão de seus funcionários.
-   **Para Funcionários:** O foco é no gerenciamento de produtos e ofertas da loja para a qual trabalham, com acesso condicionado à sua localização e turno de trabalho.

## 2. Tecnologias

-   **Framework:** React Native
-   **Navegação:** React Navigation
-   **Autenticação:** Firebase SDK
-   **Requisições HTTP:** Axios
-   **Estilização:** Styled Components ou React Native Paper (Material Design)
-   **Mapas:** `react-native-maps`
-   **Câmera:** `react-native-vision-camera` ou similar.
-   **Geolocalização em Background:** `react-native-background-geolocation` ou similar, para permitir a verificação de perímetro do funcionário.
-   **Gerenciamento de Estado:** React Context API ou Zustand.

## 3. Estrutura de Telas (Screens)

### Telas Comuns
-   `LoginScreen`: Tela de autenticação.
-   `RegisterScreen`: Tela de cadastro, permitindo a escolha entre perfil "Consumidor" ou "Lojista".
-   `ProfileScreen`: Tela para visualizar e editar dados básicos do perfil.

### Tela de Seleção (Lojista/Funcionário)
-   `StoreSelectionScreen`: Apresentada após o login para lojistas ou funcionários com múltiplas lojas. Permite selecionar a loja a ser gerenciada na sessão ou adicionar uma nova (apenas para lojistas).

### Telas do Consumidor
-   `OfferFeedScreen`: Tela principal com dois feeds de ofertas horizontais (Promoções e Ofertas Gerais).
-   `SearchScreen`: Com busca textual, filtros de categoria, ordenação e botão para busca por imagem.
-   `MapScreen`: Visualização de lojas e ofertas próximas.
-   `ProductDetailScreen`: Detalhes de um produto/oferta.
-   `StoreDetailScreen`: Detalhes de uma loja específica.

### Telas do Lojista (Contextuais à Loja Selecionada)
-   `ShopDashboardScreen`: Painel de controle principal, exibindo dados da **loja atualmente selecionada**.
-   `ManageStoreScreen`: Formulário para o lojista criar ou editar os dados da loja.
-   `ManageProductsScreen`: Interface para o lojista gerenciar o catálogo de produtos da loja.
-   `ManageOffersScreen`: Interface para o lojista criar e gerenciar as ofertas da loja.
-   `ManageEmployeesScreen`: Interface para gerenciar funcionários **da loja selecionada**.

### Telas do Funcionário (Contextuais à Loja Selecionada)
-   `EmployeeDashboardScreen`: Painel de controle para o funcionário, contextual à **loja selecionada**. Exibe as opções de gerenciamento se as condições de acesso (local e turno) forem atendidas.
-   *Esta seção reutilizará as telas `ManageProductsScreen` e `ManageOffersScreen`.*

## 4. Plano de Implementação (Fases)

### Fase 1: Estrutura Base e Autenticação
-   **Objetivo:** Configurar o ambiente e o fluxo de autenticação/navegação para todos os perfis.
-   **Passos:**
    1.  Inicializar e configurar o projeto React Native.
    2.  Integrar o Firebase SDK.
    3.  Implementar as telas `LoginScreen` e `RegisterScreen`.
    4.  Configurar a navegação principal.
    5.  Implementar a lógica de redirecionamento pós-login: Consumidores vão para o feed. Lojistas/Funcionários com múltiplas lojas são direcionados para a `StoreSelectionScreen`. Lojistas/Funcionários com apenas uma loja vão direto para o dashboard respectivo.

### Fase 2: Funcionalidades do Consumidor
-   **Objetivo:** Desenvolver a experiência principal de descoberta de ofertas.

### Fase 3: Funcionalidades do Lojista (Contextual)
-   **Objetivo:** Criar as ferramentas de gerenciamento para os lojistas, considerando o contexto de múltiplas lojas.
-   **Passos:**
    1.  **TDD:** Desenvolver a `StoreSelectionScreen` para listar as lojas do usuário e permitir a seleção.
    2.  Garantir que todas as telas de gerenciamento (loja, produtos, ofertas, funcionários) operem no contexto da loja selecionada.
    3.  **TDD:** Desenvolver as telas `ManageStoreScreen`, `ManageProductsScreen`, `ManageOffersScreen` e `ManageEmployeesScreen`.

### Fase 4: Busca por Imagem (IA)
-   **Objetivo:** Implementar a funcionalidade de busca visual para o consumidor.

### Fase 5: Funcionalidades do Funcionário
-   **Objetivo:** Implementar o painel condicional para o funcionário, considerando o contexto da loja selecionada.
-   **Passos:**
    1.  **TDD:** Implementar a `EmployeeDashboardScreen` com a lógica de verificação de acesso.
    2.  Integrar um serviço de geolocalização em background para verificar a posição do usuário contra o perímetro da **loja selecionada**.
    3.  Implementar a lógica de verificação do turno de trabalho atual.

### Fase 6: Testes, Refinamento e Publicação
-   **Objetivo:** Garantir a qualidade e preparar o aplicativo para o lançamento.

## 5. Próximos Passos

-   [ ] Iniciar a **Fase 1** para reconfigurar a autenticação e navegação.
-   [ ] Proceder com as fases de implementação, começando pela `StoreSelectionScreen`.
