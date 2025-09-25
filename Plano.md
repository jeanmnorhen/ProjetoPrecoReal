# Plano de Desenvolvimento do Projeto PREÇO REAL

## 1. Visão Geral do Projeto

O PREÇO REAL é uma plataforma multicomponente projetada para ser a principal ferramenta de comparação de preços para consumidores e uma poderosa plataforma de vendas para lojistas. A arquitetura é baseada em microsserviços, com comunicação via Kafka, e frontends reativos para web e mobile.

## 2. Arquitetura de Microsserviços

- **servico-usuarios:** Gerencia dados de usuários, autenticação, perfis e a lógica de múltiplos lojistas/funcionários.
- **servico-lojas:** Gerencia o cadastro e a geolocalização das lojas.
- **servico-produtos:** Gerencia o catálogo de produtos canônicos.
- **servico-ofertas:** Gerencia as ofertas de produtos criadas pelos lojistas.
- **servico-busca:** Fornece busca textual e por similaridade, integrado com Elasticsearch.
- **servico-agentes-ia:** Orquestra agentes de IA (Google Gemini) para tarefas como análise de imagem e categorização de produtos.
- **servico-monitoramento:** Coleta e expõe métricas de saúde e de negócio da plataforma, integrado com InfluxDB.
- **servico-healthcheck:** Centraliza a verificação de status dos demais serviços.

## 3. Frontends

- **frontend-tester (Web - Next.js):** Atualmente serve como uma ferramenta de teste e prototipagem. Será evoluído para o Dashboard Administrativo.
- **Aplicativo Móvel (React Native):** O principal ponto de interação para consumidores, lojistas e funcionários.

## 4. Dashboard Administrativo e Catálogo de Produtos

- **Visão:** Transformar o painel administrativo em um dashboard de inteligência de negócios e gerenciamento de dados.
- **Funcionalidades Chave:**
    - Monitoramento de métricas de uso e de preços.
    - Sistema de moderação para críticas de dados de produtos enviadas por usuários.
    - Gerenciamento centralizado do catálogo de produtos canônicos.
- **Objetivo Estratégico:** Aumentar a qualidade e a precisão dos dados dos produtos na plataforma, criando um catálogo rico que simplifica a experiência do lojista, permitindo que ele se concentre na precificação em vez do cadastro manual de informações.

## 5. Próximos Passos e Foco Atual

1.  **Finalizar a Configuração do Ambiente Local:** Garantir que todos os serviços e dependências (Kafka, Postgres, Elasticsearch, etc.) estejam rodando de forma estável com Docker Compose.
2.  **Desenvolver o Dashboard Administrativo:** Implementar as funcionalidades de monitoramento, gestão de críticas e gerenciamento do catálogo de produtos no `frontend-tester`.
3.  **Desenvolver o Aplicativo Móvel (React Native):** Iniciar o desenvolvimento do aplicativo móvel, seguindo o plano de fases, com foco inicial na autenticação e nas funcionalidades do consumidor.
4.  **Segurança e Escalabilidade:** Continuar a revisar e aprimorar a segurança entre os serviços e planejar a infraestrutura para escalabilidade na nuvem (Vercel/AWS/GCP).