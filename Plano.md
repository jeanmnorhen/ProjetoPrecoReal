# Plano Ambicioso de Evolução do Projeto Preço Real (Revisado)

## 1. Visão Geral

Este documento detalha o plano estratégico para evoluir a arquitetura do projeto Preço Real para um sistema moderno, escalável e orientado a eventos. A nova arquitetura utilizará **Python/Flask** para os microsserviços, **Apache Kafka** como barramento de eventos e **Vercel** para deployment contínuo.

A abordagem de persistência será **poliglota**, utilizando a melhor tecnologia de banco de dados para cada caso de uso: **Google Firestore** para dados transacionais, um motor de busca como **OpenSearch/Elasticsearch** para buscas textuais e uma base de dados de série temporal como **TimescaleDB** para analytics.

A metodologia de desenvolvimento adotada será **Test-Driven Development (TDD)**, garantindo a qualidade e a robustez de cada funcionalidade.

## 2. Arquitetura Proposta

- **Frontend (Next.js):** Interface do usuário, adaptada para se comunicar com um API Gateway. Para operações de leitura (ex: buscar ofertas), utilizará um padrão síncrono (Request/Response). Para operações de escrita (ex: criar oferta), o Gateway publicará eventos no Kafka.
- **Comunicação (Apache Kafka):** O sistema nervoso central da aplicação, garantindo comunicação assíncrona, desacoplamento e resiliência entre os microsserviços.
- **Microsserviços (Python/Flask):** Serviços independentes por domínio de negócio, containerizados e implantados como funções serverless na Vercel. Incluirão: `servico-usuarios`, `servico-lojas`, `servico-produtos`, `servico-ofertas`, `servico-busca`, `servico-agentes-ia`, e `servico-monitoramento`.
- **Persistência de Dados (Estratégia Poliglota):**
    - Google Firestore: Banco de dados para dados transacionais (OLTP) específicos que se beneficiem de sua natureza serverless e escalabilidade horizontal.
    - PostgreSQL + PostGIS: Banco de dados relacional para dados geoespaciais complexos, como localização de lojas e usuários para consultas de proximidade avançadas, e também para dados transacionais (OLTP) de serviços como `servico-usuarios`.
    - **OpenSearch/Elasticsearch:** Motor de busca dedicado para alimentar a funcionalidade de busca textual em tempo real, garantindo performance e relevância.
    - **TimescaleDB/InfluxDB:** Banco de dados de série temporal para armazenar o histórico de preços, permitindo consultas analíticas (OLAP) eficientes para o dashboard do administrador.
- **Agentes de IA (google-generativeai):** Encapsulados no `servico-agentes-ia`, consumirão tarefas do Kafka e publicarão resultados em tópicos de resposta.
- **Deployment (Vercel):** Plataforma unificada para o deploy serverless do front-end Next.js e dos microsserviços Python/Flask.

### Tópicos Kafka Propostos:
- `eventos_usuarios`, `eventos_produtos`, `eventos_lojas`, `eventos_ofertas`
- `eventos_precos_arquivados` (para o serviço de monitoramento)
- `tarefas_ia` (solicitações para os agentes)
- `resultados_ia` (respostas dos agentes)

### 2.1. Ambiente de Desenvolvimento Local (Docker)

Para agilizar o desenvolvimento e evitar custos com serviços de nuvem durante esta fase, o projeto utilizará **Docker** e **Docker Compose**. A infraestrutura de backend, como **Apache Kafka**, **PostgreSQL/PostGIS**, e outros bancos de dados, será provisionada localmente em containers.

Isso garante que o ambiente de desenvolvimento seja uma réplica fiel do ambiente de produção, facilitando a transição e permitindo que os desenvolvedores trabalhem de forma autônoma e sem dependência de serviços externos. O arquivo `docker-compose.yml` na raiz do projeto orquestrará a inicialização desses serviços.

## 3. Metodologia de Desenvolvimento (TDD)
IMPORTANTE! O ciclo de desenvolvimento para cada nova funcionalidade seguirá estritamente o TDD (Teste -> Código -> Refatoração) utilizando `pytest`.

## 4. Plano de Implementação (Fases)

### Fase 0: Prova de Conceito (PoC) e Configuração do Ambiente
*   **Objetivo:** Validar a pilha de tecnologia, os fluxos de trabalho e as decisões arquiteturais críticas.
*   **Passos:**
    1.  Configurar os serviços gerenciados: Apache Kafka, Google Firestore e o banco de dados de série temporal.
    2.  **TDD:** Criar e implantar o `servico-healthcheck` (Python/Flask) na Vercel.
    3.  Criar scripts de produtor/consumidor para validar a conectividade com o Kafka.
    4.  **Estratégia Geoespacial:** A decisão foi tomada para utilizar **PostgreSQL + PostGIS** como a estratégia para dados geoespaciais, devido à sua robustez e capacidade para consultas complexas.

### Fase 1: Microsserviço de Usuários
*   **Objetivo:** Migrar a funcionalidade de gerenciamento de usuários.
*   **Passos:**
    1.  Definir schemas de eventos para `eventos_usuarios`.
    2.  **TDD:** Desenvolver e implantar o `servico-usuarios` usando PostgreSQL para persistência. Para operações de escrita (criação, atualização, exclusão), o serviço publicará eventos no tópico `eventos_usuarios` do Kafka.

### Fase 2: Microsserviços Core e de Busca
*   **Objetivo:** Migrar as funcionalidades principais e implementar a busca performática.
*   **Passos:**
    1.  Repetir o processo da Fase 1 para: `servico-produtos`, `servico-lojas`, `servico-ofertas`.
    2.  Configurar o cluster de OpenSearch/Elasticsearch.
    3.  **TDD:** Desenvolver e implantar o `servico-busca`. Este serviço consumirá eventos dos outros serviços core para manter seu índice de busca sempre atualizado.
    4.  Integrar o front-end com o `servico-busca` para a funcionalidade de pesquisa.

### Fase 3: Microsserviço de Agentes de IA
*   **Objetivo:** Isolar a lógica de IA em seu próprio serviço assíncrono e expandir as capacidades de IA.
*   **Passos:**
    1.  Definir schemas para os tópicos `tarefas_ia` e `resultados_ia`. (Concluído para Análise de Imagem)
    2.  **TDD:** Implementar os diversos agentes dentro do `servico-agentes-ia`:
        *   **Análise de Imagem:** Identificação de produtos a partir de imagens. (Concluído)
        *   **Busca de Produtos em Lojas:** Agente especialista para buscar produtos na internet a partir de texto e URLs de lojas.
        *   **Categorização de Produtos:** Agente para categorizar automaticamente produtos usando `google-generativeai`.
    3.  Implantar e integrar com os demais serviços que dependem de resultados de IA.

### Fase 4: Microsserviço de Monitoramento e Analytics
*   **Objetivo:** Implementar o dashboard de monitoramento de preços para o Administrador.
*   **Passos:**
    1.  Definir o schema do tópico `eventos_precos_arquivados`.
    2.  **TDD:** Desenvolver o `servico-monitoramento`. Ele consumirá eventos de ofertas, os arquivará no banco de série temporal (ex: TimescaleDB) e exporá um endpoint com as agregações (média, min, max) e dados históricos.
    3.  Implantar o serviço e construir a interface de visualização no front-end do admin.

### Fase 5: Testes de Integração e Go-Live
*   **Objetivo:** Garantir que todo o ecossistema funciona em harmonia.
*   **Passos:**
    1.  Desenvolver testes de integração end-to-end que simulem fluxos completos do usuário.
    2.  Monitorar o fluxo de eventos no Kafka e a performance de todos os serviços.
    3.  Descomissionar gradualmente o backend monolítico antigo.
    4.  Realizar o lançamento oficial da nova arquitetura.

### Fase 6: Aprimoramentos do Frontend e Experiência do Usuário
*   **Objetivo:** Melhorar a interface do usuário e implementar funcionalidades avançadas para o consumidor e lojista.
*   **Passos:**
    1.  Implementar feeds de ofertas dinâmicos e infinitos, separados por tipo (Promoções, Promoções Relâmpago, Ofertas).
    2.  Desenvolver a interface de usuário para filtragem de ofertas por categoria (botões).
    3.  Implementar opções de ordenação de ofertas por "Proximidade" e "Preço" (ascendente/descendente).
    4.  Desenvolver a lógica e UI para "Verificação e Sugestão para Catálogo" (frontend para sugestões de produtos via análise de imagem).
    5.  Criar um painel administrativo dedicado para o lojista, incluindo gerenciamento de "vitrine virtual" e "anúncios ativos".
    6.  Integrar um gráfico de tendência de preços (ex: Recharts) na página de monitoramento do administrador.
    7.  Implementar a exibição condicional de links de Admin na Navbar.

### Fase 7: Gerenciamento Avançado do Catálogo Canônico (Admin)
*   **Objetivo:** Fornecer ferramentas robustas para o administrador gerenciar o catálogo de produtos canônicos.
*   **Passos:**
    1.  Desenvolver a interface de usuário para "Revisão de Sugestões de Produtos" (tabela de termos sugeridos com status e ações).
    2.  Implementar a lógica de "Rejeitar" sugestões, incluindo a exclusão automática de novas sugestões de termos já rejeitados.
    3.  Desenvolver o workflow de aprovação de produtos sugeridos para torná-los canônicos.
    4.  Integrar o "Agente Especialista em Categorização de Produtos" no fluxo de aprovação de produtos canônicos.

---

# Plano de Teste do Projeto

**Objetivo:** Garantir a qualidade, funcionalidade, performance e segurança dos microserviços e da aplicação frontend do Projeto Preço Real.

**Escopo:**
*   **Microserviços Backend:**
    *   `servico-usuarios`
    *   `servico-produtos`
    *   `servico-lojas`
    *   `servico-ofertas`
    *   `servico-busca`
    *   `servico-monitoramento`
    *   `servico-agentes-ia`
*   **Aplicação Frontend:** `frontend-tester`
*   **Infraestrutura:** Kafka, PostgreSQL/PostGIS, Elasticsearch, InfluxDB, Firebase.

**Tipos de Teste:**

1.  **Testes Unitários:**
    *   **Foco:** Componentes individuais (funções, classes) dos microserviços.
    *   **Ferramentas:** `pytest` com `pytest-mock` (para Python).
    *   **Estratégia de Mock:** Utilização de fixtures individuais para cada dependência externa, mockando variáveis de ambiente, funções de inicialização e variáveis globais para isolar a unidade de teste.
    *   **Cobertura:** Mínimo de 80% de cobertura de código para lógica de negócio crítica.

2.  **Testes de Integração:**
    *   **Foco:** Interação entre microserviços e com serviços externos (bancos de dados, filas de mensagem, APIs de terceiros).
    *   **Ferramentas:** `pytest` (para Python), testes baseados em requisições HTTP.
    *   **Estratégia:** Utilização de ambientes de teste dedicados (Docker Compose para ambiente local, ambientes de staging para nuvem) para simular o ambiente de produção. Mocks serão usados para serviços de terceiros que não podem ser facilmente provisionados em ambientes de teste.

3.  **Testes de Ponta a Ponta (E2E):**
    *   **Foco:** Fluxos completos do usuário através da aplicação frontend e dos microserviços backend.
    *   **Ferramentas:** A definir (ex: Cypress, Playwright para frontend; scripts Python/shell para orquestração de chamadas de API).
    *   **Estratégia:** Simulação de cenários de usuário, validação de dados em todas as camadas da aplicação.

4.  **Testes de Performance/Carga:**
    *   **Foco:** Comportamento do sistema sob diferentes cargas de usuário e dados.
    *   **Ferramentas:** A definir (ex: Locust, JMeter).
    *   **Métricas:** Latência, throughput, utilização de recursos.

5.  **Testes de Segurança:**
    *   **Foco:** Identificação de vulnerabilidades (autenticação, autorização, injeção de SQL, XSS, etc.).
    *   **Ferramentas:** A definir (ex: OWASP ZAP, Snyk).
    *   **Processo:** Análise estática de código (SAST), análise dinâmica de aplicação (DAST).

6.  **Testes de Usabilidade (Frontend):**
    *   **Foco:** Experiência do usuário, facilidade de uso, acessibilidade.
    *   **Métodos:** Testes manuais, feedback de usuários.

**Ambientes de Teste:**

*   **Local:** Docker Compose para simular a infraestrutura de backend.
*   **Staging/Homologação:** Ambiente na nuvem (Vercel para microserviços, provedores de serviço para bancos de dados/filas) que replica o ambiente de produção.

**Processo de Teste:**

1.  **Desenvolvimento Orientado a Testes (TDD):** Sempre que possível, escrever testes antes de implementar a funcionalidade.
2.  **Integração Contínua (CI):** Execução automática de testes unitários e de integração em cada push para o repositório.
3.  **Deploy Contínuo (CD):** Após a aprovação dos testes em staging, deploy automático para produção.
4.  **Monitoramento:** Monitoramento contínuo em produção para identificar anomalias e erros.

**Manutenção do Plano de Teste:**

Este documento (`plano.md`) deve ser mantido atualizado com as mudanças na arquitetura, novas funcionalidades e ferramentas de teste. Revisões periódicas serão realizadas para garantir sua relevância e eficácia.