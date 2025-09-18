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
    - **Google Firestore:** Banco de dados primário para dados transacionais (OLTP) como perfis de usuário, dados de lojas e produtos canônicos, aproveitando sua natureza serverless.
    - **PostgreSQL + PostGIS:** Banco de dados relacional para dados geoespaciais complexos, como localização de lojas e usuários para consultas de proximidade avançadas.
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
    2.  **TDD:** Desenvolver e implantar o `servico-usuarios` usando Firestore para persistência.

### Fase 2: Microsserviços Core e de Busca
*   **Objetivo:** Migrar as funcionalidades principais e implementar a busca performática.
*   **Passos:**
    1.  Repetir o processo da Fase 1 para: `servico-produtos`, `servico-lojas`, `servico-ofertas`.
    2.  Configurar o cluster de OpenSearch/Elasticsearch.
    3.  **TDD:** Desenvolver e implantar o `servico-busca`. Este serviço consumirá eventos dos outros serviços core para manter seu índice de busca sempre atualizado.
    4.  Integrar o front-end com o `servico-busca` para a funcionalidade de pesquisa.

### Fase 3: Microsserviço de Agentes de IA
*   **Objetivo:** Isolar a lógica de IA em seu próprio serviço assíncrono.
*   **Passos:**
    1.  Definir schemas para os tópicos `tarefas_ia` e `resultados_ia`.
    2.  **TDD:** Implementar os diversos agentes (Busca de Lojas, Busca de Produtos, Categorização, Análise de Imagem) dentro do `servico-agentes-ia`.
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

## 5. Próximos Passos

- [ ] Iniciar a **Fase 0** com a configuração dos serviços de Kafka e Firestore.
- [ ] Iniciar a **Fase 0** com a criação e deploy do `servico-healthcheck`.
- [ ] Iniciar a **Fase 0** com a **configuração e integração do PostgreSQL + PostGIS** para dados geoespaciais.
