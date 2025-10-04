Documentação Unificada do Projeto PREÇO REAL
1. Visão Geral e Arquitetura de Microsserviços
1.1. Visão Geral do Projeto
O PREÇO REAL é uma plataforma multicomponente projetada para ser uma ferramenta de comparação de preços para consumidores e uma plataforma de vendas para lojistas. Sua arquitetura é baseada em microsserviços, com comunicação assíncrona via Kafka, e frontends reativos para web e mobile.
1.2. Arquitetura de Microsserviços
A plataforma é composta pelos seguintes serviços chave:
servico-usuarios: Gerencia dados de usuários, autenticação, perfis e a lógica de múltiplos lojistas/funcionários.
servico-lojas: Gerencia o cadastro e a geolocalização das lojas.
servico-produtos: Gerencia o catálogo de produtos canônicos.
servico-ofertas: Gerencia as ofertas de produtos criadas pelos lojistas.
servico-busca: Fornece busca textual e por similaridade, integrado com Elasticsearch.
servico-agentes-ia: Orquestra agentes de IA (Google Gemini) para tarefas como análise de imagem e categorização de produtos.
servico-monitoramento: Coleta e expõe métricas de saúde e de negócio da plataforma, integrado com InfluxDB.
servico-healthcheck: Centraliza a verificação de status dos demais serviços.
1.3. Frontends
Dashboard Administrativo (Web - Next.js): Plataforma completa para administração, monitoramento, gerenciamento de catálogo com IA e moderação de dados.
Aplicativo Móvel (React Native): O principal ponto de interação para consumidores e lojistas. Atualmente Não Iniciado.
1.4. Dashboard Administrativo e Catálogo de Produtos
O painel administrativo está sendo transformado em um dashboard de inteligência de negócios e gerenciamento de dados.
Funcionalidades Chave: Monitoramento de métricas de uso e de preços, sistema de moderação para críticas de dados, e gerenciamento centralizado do catálogo de produtos canônicos, assistido por IA.
Status (Atualizado em Setembro/2025): O desenvolvimento do Dashboard Administrativo foi concluído, com a implementação das funcionalidades de monitoramento, gestão de críticas e o novo fluxo de gerenciamento do catálogo com IA.
2. Plano de Desenvolvimento do Frontend - Dashboard Administrativo
O painel administrativo será um dashboard centralizado, construído com Next.js e Tailwind CSS, focado em monitorar a saúde da plataforma, gerenciar o catálogo de produtos e garantir a qualidade dos dados.
2.1. Autenticação
O acesso é restrito a usuários com o status de admin no Firebase Authentication. Utiliza-se um Higher-Order Component (HOC) withAdminAuth para proteger todas as rotas do dashboard.
2.2. Estrutura de Páginas e Componentes
O layout principal (/admin/layout.tsx) inclui uma Navbar Superior (logo, usuário, logout) e uma Sidebar (navegação lateral) com links para: Dashboard, Gestão de Críticas, Catálogo de Produtos (Canônicos), Lojas, Usuários e Ofertas.
Páginas Chave
Página Principal (/admin/dashboard): Visão geral com widgets interativos, incluindo StatCard (métricas) e PriceTrendChart (gráfico de preços).
Catálogo de Produtos (/admin/catalogo): Central de gerenciamento, permitindo a criação e edição de produtos canônicos através de um formulário que inclui campos para upload de imagem de alta qualidade.
Gestão de Lojas, Usuários e Ofertas: Consistem em páginas de CRUD (Criar, Ler, Atualizar, Deletar) mais simples, utilizando DataTable para listagem e FormModal para edição.
2.3. Lógica e Estado
O gerenciamento de estado utiliza o AuthContext para autenticação. Para o estado das páginas, o estado local do React (useState, useReducer) é utilizado inicialmente. A comunicação com a API é centralizada e gerenciada através de um ApiService ou hooks customizados.
3. Implementação da IA Multimodal Local (MLLMs)
RELATÓRIO DE IMPLEMENTAÇÃO LOCAL DE MODELOS MULTIMODAIS (MLLMs) PARA CRIAÇÃO AUTOMATIZADA DE CATÁLOGO DE PRODUTOS: Otimização GGUF e Arquitetura Assíncrona
3.1. Análise de Viabilidade e Seleção de Modelos Multimodais (MLLM)
A. O Caso de Uso: Automação de Fichas Técnicas de Produtos
O pipeline visa ingerir uma imagem de produto e gerar dados estruturados essenciais, como nome, categorização precisa e descrição textual. Este processo automatizado preenche um "card de produto" de forma confiável, exigindo reconhecimento visual detalhado (VLM) e geração sofisticada de linguagem natural (LLM). A viabilidade reside na seleção de MLLMs otimizados para execução local.
B. Fundamentos dos MLLMs Locais: Arquitetura e Modelos Candidatos
A arquitetura MLLM opera em três componentes principais:
Codificador Visual (Vision Encoder): Processa a imagem e extrai características visuais (e.g., CLIP ViT-L/14).
Projetor: Camada de rede neural que traduz os embeddings visuais para o formato que o LLM pode entender, sendo o elo multimodal.
Decodificador de Texto (Text Decoder): O LLM base (como LLaMA ou Mistral) que gera o texto descritivo e estruturado.
A variante BakLLaVA é tecnicamente superior para inferência local otimizada, utilizando o eficiente Mistral AI como LLM base e mantendo o poder de processamento visual do LLaVA.
C. Otimização Essencial: GGUF e llama.cpp
O formato GGUF (General Use Format), do projeto llama.cpp, é fundamental para a viabilidade da execução de MLLMs em hardware de consumidor.
Quantização: O GGUF permite a quantização do modelo (compressão dos pesos) em níveis de precisão baixos (e.g., Q4_K_M, Q8_0), reduzindo drasticamente a pegada de memória (um modelo 7B de 14 GB pode cair para ~4.5 GB).
Requisitos de Hardware: O requisito prático mínimo de VRAM é de 8 GB ou, preferencialmente, 12 GB a 16 GB para garantir fluidez, acomodando o LLM quantizado mais os requisitos do Codificador Visual (CLIP). GPUs de consumidor como uma NVIDIA RTX 4070Ti SUPER com 16GB de VRAM são ideais.
3.2. Projeto da Arquitetura de Serviço de Inferência (MLOps Local)
A. A Necessidade Crítica de Assincronicidade no Pipeline
A execução de tarefas multimodais é um processo de longa duração (long-running process). Portanto, a arquitetura deve ser assíncrona para não bloquear o servidor web principal.
B. Design da API Assíncrona e Fluxo de Dados
O sistema de inferência utiliza a seguinte arquitetura:
Serviço Web (FastAPI): Recebe o upload da imagem.
Fila de Mensagens (RabbitMQ/Redis): Usada para a comunicação entre o serviço web e o worker.
Worker Assíncrono (Celery/RQ): Responsável por carregar o MLLM (via llama-cpp-python), processar a imagem e gerar o JSON estruturado.
Endpoint de Polling: Permite que o Frontend consulte periodicamente o status do job de inferência (por meio de um ID da tarefa), retornando a resposta em JSON assim que a tarefa estiver concluída.
C. Recomendações de Implementação Acionáveis
Estratégia de Armazenamento: Implementar o salvamento de arquivos no FastAPI para um volume compartilhado (Docker Volume), passando apenas o caminho/ID do arquivo para o Celery Worker.
Output Determinístico: A integração do Pydantic com o constrained decoding nativo é fundamental para garantir que a saída do LLM seja validada e estruturada (JSON).
Rigor na Engenharia de Prompt e Pré-processamento: Desenvolver prompts que incorporem a lista de categorias e o requisito de descrição mínima (e.g., 150 palavras) para guiar o MLLM. É mandatório integrar bibliotecas de pré-processamento (OpenCV/Pillow) no worker para garantir a normalização visual das imagens antes da ingestão.