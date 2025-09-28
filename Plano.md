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

- **Dashboard Administrativo (Web - Next.js):** Plataforma completa para administração, monitoramento, gerenciamento de catálogo com IA e moderação de dados.
- **Aplicativo Móvel (React Native):** O principal ponto de interação para consumidores e lojistas. **(Não iniciado)**

## 4. Dashboard Administrativo e Catálogo de Produtos

- **Visão:** Transformar o painel administrativo em um dashboard de inteligência de negócios e gerenciamento de dados.
- **Funcionalidades Chave:**
    - Monitoramento de métricas de uso e de preços.
    - Sistema de moderação para críticas de dados de produtos enviadas por usuários.
    - Gerenciamento centralizado do catálogo de produtos canônicos, assistido por IA.
- **Objetivo Estratégico:** Aumentar a qualidade e a precisão dos dados dos produtos na plataforma, criando um catálogo rico que simplifica a experiência do lojista, permitindo que ele se concentre na precificação em vez do cadastro manual de informações.

## 5. Próximos Passos e Foco Atual (Atualizado em Setembro/2025)

1.  **[FOCO PRINCIPAL] Desenvolver o Aplicativo Móvel (React Native):** Iniciar a implementação das fases descritas no `PlanoFrontEnd_Mobile.md`, começando pela estrutura de autenticação e navegação.
2.  **Ampliar Cobertura de Testes do Frontend:** Criar testes de componentes para o Dashboard Administrativo, garantindo a estabilidade das funcionalidades existentes.
3.  **Segurança e Escalabilidade:** Continuar a revisar e aprimorar a segurança entre os serviços e otimizar a infraestrutura para escalabilidade na nuvem (Vercel/GCP).
4.  **[CONCLUÍDO] Desenvolver o Dashboard Administrativo:** As funcionalidades de monitoramento, gestão de críticas e o novo fluxo de gerenciamento do catálogo com IA foram implementadas.