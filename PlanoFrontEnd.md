# Plano de Implementação de Front-ends para Teste de Funcionalidades Backend

## 1. Visão Geral

Este documento descreve o plano para desenvolver um conjunto de interfaces de usuário (front-ends) utilizando Next.js. O objetivo principal é fornecer ferramentas visuais para testar e validar as APIs expostas pelos microsserviços Python/Flask do backend do projeto Preço Real. Cada interface será projetada para interagir com funcionalidades específicas do backend, permitindo a criação, leitura, atualização e exclusão de dados, bem como o acionamento de processos.

## 2. Tecnologias

*   **Framework:** Next.js (com React)
*   **Autenticação:** Firebase SDK (para integração com Firebase Authentication)
*   **Requisições HTTP:** Fetch API ou Axios
*   **Estilização:** Tailwind CSS (sugestão para agilidade no desenvolvimento de UI de teste)

## 3. Estrutura do Projeto Frontend

Será mantido um único projeto Next.js que conterá diferentes páginas ou seções, cada uma dedicada a testar um microsserviço ou um conjunto de funcionalidades relacionadas.

```
/frontend-tester
├── pages/
│   ├── index.tsx (Página inicial/Login)
│   ├── healthcheck.tsx
│   ├── usuarios.tsx
│   ├── lojas.tsx
│   ├── produtos.tsx
│   ├── ofertas.tsx
│   └── geospatial-poc.tsx (Opcional)
├── components/ (Componentes reutilizáveis como formulários, tabelas)
├── lib/ (Funções utilitárias, configuração do Firebase, clientes de API)
├── styles/
├── public/
└── ... (outros arquivos de configuração do Next.js)
```

## 4. Plano de Implementação (Fases)

### Fase 0: Configuração Base do Projeto Frontend

*   **Objetivo:** Estabelecer a estrutura fundamental do projeto Next.js e a integração com a autenticação.
*   **Passos:**
    1.  Inicializar um novo projeto Next.js (`npx create-next-app@latest frontend-tester`).
    2.  Instalar e configurar o Firebase SDK para o frontend, utilizando as variáveis de ambiente `NEXT_PUBLIC_FIREBASE_*`.
    3.  Implementar uma página de **Login/Cadastro** (`pages/index.tsx`) que permita aos usuários autenticar-se via Firebase Auth e obter um ID Token.
    4.  Configurar um mecanismo para armazenar e enviar o ID Token nas requisições HTTP para os microsserviços backend (e.g., via `Authorization: Bearer <token>`).
    5.  Configurar variáveis de ambiente no Next.js para as URLs base de cada microsserviço backend (e.g., `NEXT_PUBLIC_USERS_API_URL`, `NEXT_PUBLIC_STORES_API_URL`).
    6.  Configurar o deployment contínuo do projeto Next.js na Vercel.

### Fase 1: Teste do `servico-healthcheck`

*   **Objetivo:** Validar a acessibilidade e o status do microsserviço de healthcheck.
*   **Passos:**
    1.  Criar a página `pages/healthcheck.tsx`.
    2.  Implementar uma requisição GET para o endpoint `/health` do `servico-healthcheck`.
    3.  Exibir o status retornado (`"ok"` ou `"error"`) na interface.

### Fase 2: Teste do `servico-usuarios` (CRUD)

*   **Objetivo:** Validar todas as operações CRUD do microsserviço de usuários.
*   **Passos:**
    1.  Criar a página `pages/usuarios.tsx`.
    2.  **Criação:** Desenvolver um formulário para criar novos usuários, incluindo campos para `email`, `name`, `latitude` e `longitude` (para o geohash).
    3.  **Leitura:** Implementar uma tabela para listar todos os usuários (se houver um endpoint de listagem) ou um campo de busca por ID para exibir detalhes de um usuário específico.
    4.  **Atualização:** Adicionar funcionalidade para editar os dados de um usuário existente, com um formulário pré-preenchido.
    5.  **Exclusão:** Implementar um botão para deletar um usuário, com confirmação.
    6.  Garantir que todas as requisições sejam autenticadas com o ID Token do Firebase.

### Fase 3: Teste dos Microsserviços de Lojas, Produtos e Ofertas (Criação)

*   **Objetivo:** Validar a criação de entidades nos microsserviços de lojas, produtos e ofertas, incluindo as validações de propriedade.
*   **Passos:**
    1.  **`pages/lojas.tsx`:** Criar um formulário para registrar novas lojas, com campos como `name`, `address`, `store_category`, `description`, `location` (latitude/longitude).
    2.  **`pages/produtos.tsx`:** Criar um formulário para adicionar produtos. Este formulário precisará de um campo para `store_id` (que pode ser um input manual ou um dropdown populado com lojas existentes para facilitar o teste).
    3.  **`pages/ofertas.tsx`:** Criar um formulário para registrar ofertas. Este formulário precisará de um campo para `product_id` (input manual ou dropdown populado com produtos existentes).
    4.  Garantir que todas as requisições sejam autenticadas e que as validações de propriedade (dono da loja, dono do produto) sejam testadas.

### Fase 4: Teste da PoC Geoespacial (Visualização Opcional)

*   **Objetivo:** Se a PoC geoespacial for exposta via API, criar uma interface para visualizar seus resultados.
*   **Passos:**
    1.  Criar a página `pages/geospatial-poc.tsx`.
    2.  Permitir que o usuário insira uma localização (latitude/longitude).
    3.  Fazer uma requisição à API da PoC (se disponível) e exibir as lojas retornadas, talvez com suas distâncias.
    4.  Considerar a integração com um mapa simples (e.g., Leaflet, Google Maps Embed) para visualização.

### Fase 5: Deployment Contínuo e Refinamento

*   **Objetivo:** Manter o ambiente de teste frontend atualizado e funcional.
*   **Passos:**
    1.  Configurar o pipeline de CI/CD na Vercel para deployment automático a cada push para o branch principal.
    2.  Realizar testes de integração end-to-end manuais ou automatizados (se o escopo permitir) para validar os fluxos completos.
    3.  Coletar feedback da equipe de backend para refinar as interfaces de teste conforme necessário.

## 5. Próximos Passos

- [ ] Iniciar a **Fase 0** com a configuração do projeto Next.js e autenticação Firebase.
- [ ] Iniciar a **Fase 1** com a implementação da página de healthcheck.
- [ ] Iniciar a **Fase 2** com a implementação das funcionalidades CRUD para usuários.