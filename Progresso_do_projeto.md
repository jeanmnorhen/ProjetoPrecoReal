# Progresso do Projeto "Preço Real"

*Última atualização: 4 de outubro de 2025*

## Visão Geral

O projeto "Preço Real" é uma plataforma de comparação de preços com uma arquitetura de microsserviços, projetada para ser uma ferramenta para consumidores e lojistas.

## Status dos Componentes

### Backend (Microsserviços)

Todos os microsserviços de backend estão implementados e operacionais, utilizando Python/Flask, com comunicação via Kafka e uma abordagem de banco de dados poliglota.

-   **`servico-usuarios`**: **Operacional.** Gerencia perfis, autenticação (Firebase), localização (PostGIS) e permissões.
-   **`servico-lojas`**: **Operacional.** Gerencia lojas (Firestore) e suas localizações (PostGIS).
-   **`servico-produtos`**: **Operacional.** Gerencia o catálogo de produtos canônicos e de lojas (Firestore).
-   **`servico-ofertas`**: **Operacional.** Gerencia ofertas de produtos (Firestore).
-   **`servico-busca`**: **Operacional.** Fornece busca via Elasticsearch, sincronizado por eventos Kafka.
-   **`servico-agentes-ia`**: **Operacional.** Orquestra o Google Gemini para análise de imagens e alimentação do catálogo.
-   **`servico-monitoramento`**: **Operacional.** Coleta métricas de negócio e de sistema no InfluxDB.
-   **`servico-healthcheck`**: **Operacional.** Centraliza a verificação de status dos demais serviços.

### Frontend (Dashboard Administrativo - `frontend-tester`)

-   **Status:** Concluído e Operacional.
-   **Tecnologias:** Next.js, React, Tailwind CSS.
-   **Funcionalidades Implementadas:**
    -   Autenticação de administrador com Firebase.
    -   Dashboard de métricas de negócio e uso (`/admin/dashboard`).
    -   Sistema de gestão de críticas de produtos (`/admin/criticas`).
    -   Fluxo completo de "Alimentador de Catálogo com IA" (`/admin/canonicos`), incluindo a fila de aprovação de produtos (`/admin/pending-products`).
    -   Páginas de gerenciamento para Lojas, Usuários e Ofertas.

### Frontend (Aplicativo Móvel - `MobileApp`)

-   **Status:** Não Iniciado.
-   **Tecnologias Planejadas:** React Native.

## Últimas Alterações Relevantes

-   **Remoção do Confluent Cloud:** A configuração de todos os microsserviços foi simplificada para utilizar exclusivamente o ambiente Kafka local (Docker), removendo a lógica de conexão com o Confluent Cloud.

## Próximos Passos (Foco Atual)

Conforme o `Plano.md`, o foco principal do projeto agora é:

1.  **[FOCO PRINCIPAL]** Iniciar o desenvolvimento do **Aplicativo Móvel** em React Native.
2.  Ampliar a cobertura de testes automatizados para o Dashboard Administrativo.
3.  Continuar a revisão de segurança e otimização da infraestrutura.
