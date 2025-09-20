# Plano Ambicioso de Evolução do Projeto Preço Real (Revisado)

## 1. Visão Geral

Este documento detalha o plano estratégico para evoluir a arquitetura do projeto Preço Real para um sistema moderno, escalável e orientado a eventos. A nova arquitetura utilizará **Python/Flask** para os microsserviços, **Apache Kafka** como barramento de eventos, e duas interfaces de frontend distintas: um **Painel Administrativo em Next.js** e um **Aplicativo Móvel em React Native**.

A abordagem de persistência será **poliglota**, utilizando a melhor tecnologia de banco de dados para cada caso de uso: **PostgreSQL/PostGIS** para dados relacionais e geoespaciais, um motor de busca como **Elasticsearch** para buscas textuais e uma base de dados de série temporal como **InfluxDB** para analytics.

A metodologia de desenvolvimento adotada será **Test-Driven Development (TDD)**, garantindo a qualidade e a robustez de cada funcionalidade.

## 2. Arquitetura Proposta

- **Interfaces de Usuário (Frontends):**
    - **Painel Administrativo (Next.js):** Aplicação web para uso interno dos **Administradores**.
    - **Aplicativo Móvel (React Native):** Aplicação para **Consumidores**, **Lojistas** e **Funcionários**. Focada na experiência do usuário final, como busca de ofertas, gerenciamento de lojas/produtos pelos lojistas e seus funcionários (com permissões condicionais), e uso de funcionalidades nativas como a câmera.
- **Comunicação (Apache Kafka):** O sistema nervoso central da aplicação, garantindo comunicação assíncrona, desacoplamento e resiliência entre os microsserviços.
- **Microsserviços (Python/Flask):** Serviços independentes por domínio de negócio, implantados como funções serverless na Vercel. Incluirão: `servico-usuarios` (gerenciando dados de usuários e as relações de múltiplos papéis [proprietário, funcionário] entre usuários e múltiplas lojas), `servico-lojas`, `servico-produtos`, `servico-ofertas`, `servico-busca`, `servico-agentes-ia`, e `servico-monitoramento`.
- **Persistência de Dados (Estratégia Poliglota):**
    - **PostgreSQL + PostGIS:** Banco de dados relacional para dados transacionais (OLTP). Essencial para o `servico-usuarios` (incluindo uma tabela de junção `user_store_roles` para gerenciar as relações muitos-para-muitos) e `servico-lojas` (com dados geoespaciais para geofencing).
    - **Elasticsearch:** Motor de busca dedicado para alimentar a funcionalidade de busca textual em tempo real.
    - **InfluxDB:** Banco de dados de série temporal para armazenar o histórico de preços, permitindo consultas analíticas (OLAP) eficientes.
- **Agentes de IA (google-generativeai):** Encapsulados no `servico-agentes-ia`.
- **Deployment (Vercel):** Plataforma unificada para o deploy do frontend e dos microsserviços.

### Tópicos Kafka Propostos:
- `eventos_usuarios`, `eventos_produtos`, `eventos_lojas`, `eventos_ofertas`
- `eventos_funcionarios` (para registrar a associação/desassociação de funcionários)
- `eventos_precos_arquivados` (para o serviço de monitoramento)
- `tarefas_ia` (solicitações para os agentes)
- `resultados_ia` (respostas dos agentes)

### 2.1. Ambiente de Desenvolvimento Local (Docker)

Para agilizar o desenvolvimento, o projeto utilizará **Docker** e **Docker Compose** para provisionar a infraestrutura de backend localmente.

## 3. Metodologia de Desenvolvimento (TDD)
O ciclo de desenvolvimento seguirá estritamente o TDD (Teste -> Código -> Refatoração) utilizando `pytest`.

## 4. Plano de Implementação (Fases)

### Fase 0: Prova de Conceito (PoC) e Configuração do Ambiente
*   **Objetivo:** Validar a pilha de tecnologia e os fluxos de trabalho.

### Fase 1: Microsserviço de Usuários
*   **Objetivo:** Implementar o gerenciamento de usuários, incluindo o modelo de dados muitos-para-muitos para as relações Lojista-Loja e Funcionário-Loja.
*   **Passos:**
    1.  Definir schemas de eventos para `eventos_usuarios` e `eventos_funcionarios`.
    2.  **TDD:** Desenvolver e implantar o `servico-usuarios`, incluindo os endpoints e a lógica para gerenciar a tabela de junção de papéis (adicionar/remover proprietários/funcionários de lojas) e gerenciar turnos.

### Fase 2: Microsserviços Core e de Busca
*   **Objetivo:** Implementar as funcionalidades principais e a busca.

### Fase 3: Microsserviço de Agentes de IA
*   **Objetivo:** Isolar a lógica de IA em um serviço assíncrono.

### Fase 4: Microsserviço de Monitoramento e Analytics
*   **Objetivo:** Implementar o dashboard de monitoramento de preços.

### Fase 5: Testes de Integração e Go-Live
*   **Objetivo:** Garantir que todo o ecossistema funciona em harmonia.

### Fase 6: Desenvolvimento do Aplicativo Móvel (React Native)
*   **Objetivo:** Implementar as funcionalidades para o consumidor, lojista e funcionário no aplicativo móvel.
*   **Passos:**
    1.  **Implementar uma tela de seleção de loja** para usuários (lojistas/funcionários) associados a múltiplos estabelecimentos.
    2.  Criar o painel administrativo do lojista, garantindo que **todo o contexto de gerenciamento (produtos, ofertas, funcionários) seja relativo à loja selecionada**.
    3.  Implementar o painel do funcionário com acesso condicional (geofencing e verificação de turno) **contextual à loja selecionada**.
    4.  Integrar serviços de geolocalização em background para a verificação de perímetro.
    5.  Desenvolver as funcionalidades do consumidor (feeds de ofertas, busca, etc.).

### Fase 7: Desenvolvimento do Painel Administrativo (Next.js)
*   **Objetivo:** Fornecer ferramentas robustas para o administrador no painel web.

---

# Plano de Teste do Projeto
(O plano de teste permanece o mesmo em escopo geral, mas os testes de unidade, integração e E2E deverão cobrir a nova funcionalidade de múltiplas lojas.)
