# RELATÓRIO DE IMPLEMENTAÇÃO LOCAL DE MODELOS MULTIMODAIS (MLLMs) PARA CRIAÇÃO AUTOMATIZADA DE CATÁLOGO DE PRODUTOS: Otimização GGUF e Arquitetura Assíncrona

## I. Análise de Viabilidade e Seleção de Modelos Multimodais (MLLM)

### A. O Caso de Uso: Automação de Fichas Técnicas de Produtos

O objetivo principal desta implementação é estabelecer um pipeline robusto capaz de ingerir uma imagem de produto e, em seguida, gerar dados estruturados essenciais, incluindo o nome do produto, a categorização precisa e uma descrição textual coerente e rica. Este processo automatizado visa preencher um "card de produto" de forma confiável. Tal aplicação exige a capacidade de um modelo não apenas para o reconhecimento visual detalhado (tarefa VLM, Vision-Language Model), mas também para a geração sofisticada e estruturada de linguagem natural (tarefa LLM, Large Language Model). A viabilidade reside na seleção de MLLMs otimizados para execução local.

### B. Fundamentos dos MLLMs Locais: Arquitetura e Modelos Candidatos

A proposta de utilizar modelos como LLaMA 3 e LLaVA está alinhada com as melhores práticas atuais para sistemas multimodais abertos. O LLaVA (Large Language and Vision Assistant) é reconhecido como o framework arquitetônico pioneiro para sistemas locais, ligando um codificador visual a um LLM.

#### 1. A Estrutura Arquitetônica e a Escolha do Modelo

A arquitetura MLLM opera em três componentes principais:
1.  **Codificador Visual (Vision Encoder):** Responsável por processar a imagem de entrada e extrair características visuais. Historicamente, modelos como o CLIP (Contrastive Language–Image Pre-training), utilizando a variante ViT-L/14 (Vision Transformer - Large, Patch 14), são a base comum para o LLaVA, LLaVA-1.5 e arquiteturas subsequentes como Qwen VL e Llama 3 MLLM.
2.  **Projetor:** Uma camada de rede neural (frequentemente uma MLP simples) que traduz os embeddings visuais do codificador para um formato que o LLM pode entender e incorporar em sua sequência de tokens. Este é o elo multimodal.
3.  **Decodificador de Texto (Text Decoder):** O LLM base (como LLaMA ou Mistral) que recebe os embeddings visuais e gera o texto descritivo e estruturado.

Entre as opções sugeridas (LLaMA 3 e LLaVA), a variante **BakLLaVA** é tecnicamente superior para inferência local otimizada. BakLLaVA utiliza o eficiente **Mistral AI** como LLM base, mantendo o poder de processamento visual do LLaVA, resultando em um modelo que geralmente apresenta melhor desempenho na geração de linguagem, mantendo-se mais acessível ao hardware de consumo.

#### 2. Otimização Essencial: GGUF e llama.cpp

A execução de MLLMs em hardware de consumidor não seria viável sem técnicas agressivas de otimização de memória. O formato **GGUF (General Use Format)**, desenvolvido pelo projeto `llama.cpp`, é a tecnologia fundamental para esta viabilidade.

O GGUF permite a **quantização** do modelo (compressão dos pesos) em níveis de precisão extremamente baixos (e.g., Q4_K_M, Q8_0, que representam 4-bit ou 8-bit, e até 1.5-bit), reduzindo drasticamente a pegada de memória e permitindo a inferência em tempo real. Por exemplo, um modelo de 7 bilhões de parâmetros (7B) em precisão padrão (FP16) exigiria cerca de 14 GB de memória. Com a quantização Q4_K_M, esse requisito cai para aproximadamente 4.5 GB, tornando-o gerenciável em GPUs com VRAM limitada ou mesmo apenas com a RAM do sistema.

### C. Requisitos de Hardware e Otimização de Memória

#### 1. O Desafio da Memória Multimodal

Ao lidar com MLLMs, a pegada de memória é composta pelo LLM quantizado mais os requisitos do Codificador Visual (CLIP) e seus embeddings. O Codificador Visual é um modelo separado (e.g., ViT-L/14) que, em implementações LLaVA, é frequentemente mantido em precisão mais alta ou em um formato ligeiramente separado, como o arquivo GGUF dedicado para o modelo CLIP (`BakLLaVA-1-clip-model.gguf`).

A otimização de memória deve, portanto, abordar ambas as partes. Se a quantização (como técnicas avançadas como LUQ) não for aplicada de forma uniforme ao MLLM completo, o Codificador Visual pode se tornar o gargalo de consumo de memória de pico. Para um modelo 7B quantizado (~4.5 GB), os pesos e as ativações do CLIP e o buffer de contexto exigem memória adicional, empurrando o requisito prático mínimo de VRAM para **8 GB** ou, preferencialmente, **12 GB a 16 GB** para garantir fluidez e acomodar contextos mais longos.

#### 2. Fatores Críticos de Desempenho

A performance de inferência em `llama.cpp` não depende unicamente da capacidade da VRAM, mas também da capacidade de processamento da CPU e da velocidade de transferência de dados.

*   **VRAM:** GPUs de consumidor (como uma NVIDIA RTX 4070Ti SUPER com 16GB de VRAM) são ideais, permitindo carregar modelos maiores (como 14B ou 24B quantizados em IQ3_XS ou Q4_K_M) e atingir taxas de geração acima de 40 tokens por segundo, essenciais para a geração rápida de descrições ricas.
*   **CPU e RAM:** O `llama.cpp` suporta inferência híbrida CPU+GPU, o que significa que se a VRAM for insuficiente, as camadas do modelo podem ser descarregadas (offloaded) para a RAM. Nesses casos, a frequência da RAM e o desempenho single-thread da CPU tornam-se fatores dominantes na latência de inferência, ditando a eficiência da troca de dados entre CPU e GPU.

**Tabela 1: Comparativo de Viabilidade de MLLMs Quantizados (GGUF)**

| Modelo Base (LLM) | VLM Associado (e.g., CLIP) | Tamanho Típico GGUF (Q4_K_M) | Requisito Mínimo VRAM Estimado (Início) | Foco e Vantagem |
| :--- | :--- | :--- | :--- | :--- |
| LLaVA 1.5 - 7B | ViT-L/14 | ~4.5 GB (LLM) + CLIP | 8 GB (Híbrido CPU/GPU) | Alta performance de VLM em hardware restrito. |
| **BakLLaVA 1 - 7B (Mistral)** | **CLIP** | **~4.5 GB (LLM) + CLIP** | **8 GB (Híbrido CPU/GPU)** | **Recomendado:** Baseado em Mistral (mais poderoso para linguagem). |
| LLaVA-NeXT 13B | ViT-L/14 | ~8 GB (LLM) + CLIP | 12-16 GB | Maior precisão na categorização/descrição, exigindo mais VRAM. |

## II. Projeto da Arquitetura de Serviço de Inferência (MLOps Local)

### A. A Necessidade Crítica de Assincronicidade no Pipeline

A execução de tarefas multimodais em MLLMs, que envolvem a codificação visual da imagem seguida pela geração de longos trechos de texto, é intrinsecamente um *long-running process*. Mesmo com otimizações GGUF que atingem 40-60 tokens/segundo, a geração de descrições ricas pode levar vários segundos.

Se esta tarefa for executada no thread principal de uma web API síncrona, ela inevitavelmente bloqueará o event loop do servidor, causando timeouts para o usuário e paralisando o processamento de quaisquer outras requisições, comprometendo a escalabilidade e a experiência do usuário. A única solução arquitetônica viável para a execução de modelos de machine learning é a desvinculação da requisição HTTP do processamento pesado.

A arquitetura recomendada utiliza **FastAPI** para gerenciar os endpoints e a entrada de dados, e **Celery** como um sistema de fila de tarefas, usando **Redis** ou RabbitMQ como broker e backend. Quando o cliente envia a imagem e o prompt, o FastAPI imediatamente retorna um `task_id` e atribui o trabalho de inferência ao Celery Worker. O cliente pode então consultar o status da tarefa, permitindo que a aplicação permaneça responsiva.

### B. Gestão Robusta de Arquivos Multimodais (Imagem)

A forma como a imagem é transferida do endpoint para o worker é um ponto crucial de otimização, especialmente para garantir que o sistema possa lidar com imagens de alta resolução sem falhas de memória ou congestionamento da fila.

#### 1. Tratamento Inicial de Arquivos no FastAPI

O FastAPI lida nativamente com o upload de arquivos grandes (como imagens) usando o tipo `UploadFile`, que implementa uma interface assíncrona baseada em `SpooledTemporaryFile`. Isso impede que o servidor consuma toda a memória RAM para o upload inicial, tratando o arquivo como um stream.

#### 2. Estratégia de Transferência de Dados para o Celery

Embora seja tecnicamente possível serializar o conteúdo binário da imagem (convertido para bytes e depois em Base64) e passá-lo diretamente como argumento na mensagem da tarefa Celery, esta prática é altamente desaconselhada para MLLMs, onde as imagens podem ser grandes. Imagens codificadas em Base64 criam strings de dados massivas que sobrecarregam o broker de mensagens (Redis), aumentam a latência de enfileiramento e limitam a escalabilidade do sistema.

O padrão MLOps exige que arquivos grandes sejam desacoplados do broker. A arquitetura ideal é:

1.  O endpoint FastAPI recebe a imagem e a salva em um volume de armazenamento persistente (e.g., um disco compartilhado, MinIO ou um volume Docker montado).
2.  O FastAPI envia à tarefa Celery apenas a **referência do arquivo** (o caminho no sistema de arquivos ou um ID de storage) e os parâmetros do prompt.
3.  O Celery Worker lê o arquivo de imagem do volume persistente, processa-o e armazena os resultados (o JSON gerado) no backend (e.g., Redis) ou em um banco de dados.

Esta abordagem garante robustez e escalabilidade.

**Tabela 2: Estratégias de Gerenciamento de Arquivos no Pipeline Assíncrono**

| Estratégia | Transferência | Vantagens | Desvantagens | Recomendação para MLLM Local |
| :--- | :--- | :--- | :--- | :--- |
| 1. Byte Stream (Base64) | Codificação em string na mensagem Celery. | Simples de implementar no Python. | Risco de saturação do broker (Redis); Alta latência de serialização/desserialização. | **Não recomendado** (Risco de falha de serviço). |
| 2. Path/Storage ID | FastAPI salva o arquivo, Celery recebe o caminho/ID. | Altamente escalável; Lida com arquivos grandes. | Requer sistema de arquivos compartilhado (volume Docker). | **Recomendado** (Robustez e Escalabilidade). |

### C. Orquestração e Contêinerização (Docker)

Para garantir a reprodutibilidade e a execução padronizada, a implantação deve ser feita via **Docker Compose**. Os serviços essenciais incluem: a API (**FastAPI**), o Broker de Fila (**Redis**) e o Worker de Inferência (**Celery**).

O Worker de Inferência é o componente mais complexo, pois precisa de otimizações para compilação C/C++ (`llama.cpp`) e bibliotecas de processamento de imagem.

*   **Otimização do Dockerfile:** A compilação de `llama-cpp-python` exige ferramentas de desenvolvimento e dependências C/C++. Além disso, o pré-processamento de imagens no worker exige bibliotecas como OpenCV ou Pillow, que podem ter dependências de sistema (e.g., `libopencv-dev`).
*   **Melhores Práticas:** Recomenda-se o uso de imagens base Python slim (e.g., `python:3.x-slim`). Para manter o tamanho da imagem final reduzido e seguro, deve-se adotar uma construção *multi-stage* e instalar as dependências de sistema via `apt-get install -y --no-install-recommends` seguida da remoção do cache (`rm -rf /var/lib/apt/lists/*`).

## III. O Pipeline de Processamento de Imagem e Engenharia de Prompt

### A. Pré-processamento Obrigatório de Imagem

O desempenho do MLLM depende da qualidade e da consistência da entrada visual. Imagens de produtos reais frequentemente apresentam variações de iluminação, cor e ruído que podem levar a resultados inconsistentes.

O worker deve utilizar bibliotecas como **OpenCV** ou **Pillow** para executar:

1.  **Redimensionamento e Normalização Dimensional:** Os Vision Encoders (como o CLIP ViT-L/14) são treinados em dimensões fixas. O redimensionamento garante que a imagem esteja em um formato padronizado (e.g., 224x224 ou 336x336) antes de ser processada.
2.  **Ajuste de Domínio (Domain Adaptation):** Técnicas como correção de cor, realce de contraste ou correspondência de histograma (e.g., `histogram_match` usando espaços de cor como YCrCb) são cruciais para reduzir a discrepância (*domain shift*) entre o ambiente de treinamento do modelo e as condições da imagem de produto real. Isso aumenta a resiliência e a precisão do MLLM na identificação de atributos.

### B. Engenharia de Prompt para Tarefas Multimodais

O texto de instrução (o prompt) é a interface de controle do MLLM. Para atingir os três objetivos—identificação, categorização e descrição—o prompt deve ser dividido e otimizado para extração de dados estruturados.

1.  **Extração de Atributos:** O prompt deve direcionar o MLLM a se comportar como um "analista de catálogo" e extrair informações factuais. A categorização pode ser feita em um modo *zero-shot* ou baseada em uma lista de categorias fornecidas no prompt.
2.  **Geração de Texto Longo:** A geração da descrição exige uma instrução de estilo e volume (e.g., "gere uma descrição otimizada para SEO, focando em benefícios, com no mínimo 150 palavras").

## IV. Garantia da Qualidade do Output: Estruturação de Dados (JSON Schema)

Para que a saída do MLLM possa preencher automaticamente um card de produto, ela deve ser 100% confiável e aderente a um esquema de dados rígido. A geração de texto livre pelo LLM é inerentemente propensa a variações, o que exigiria lógica complexa de parsing e validação.

### A. Pydantic como Contrato de Dados

A biblioteca **Pydantic** resolve este problema ao permitir a definição de um esquema de dados rigoroso usando *type hints* em Python.

1.  **Definição de Esquema:** Cria-se uma classe que herda de `pydantic.BaseModel` definindo campos como `product_name`, `category_standard` e `description_long`.
2.  **Geração de Instruções:** As funções `Field` e as *docstrings* nos modelos Pydantic servem como instruções adicionais que o LLM utilizará para entender o tipo de conteúdo esperado em cada campo.
3.  **Validação:** O Pydantic garante que, se o output do modelo for JSON, ele será validado contra o esquema antes de ser consumido pelo restante do pipeline, evitando falhas de tipagem ou ausência de campos.

### B. Forçando o JSON com `llama-cpp-python`

A simples solicitação de um formato JSON no prompt é insuficiente. A implementação requer o uso de *constrained decoding* (decodificação restrita) para garantir que a gramática da saída seja estritamente JSON.

O `llama-cpp-python` suporta nativamente a restrição da resposta a um JSON válido, ou a um JSON Schema específico, através do argumento `response_format` na chamada de inferência. Este mecanismo utiliza o esquema Pydantic (convertido para JSON Schema) para guiar o processo de geração de tokens, garantindo que apenas tokens que formam um JSON sintaticamente correto (e aderente ao esquema) sejam selecionados.

Embora LLMs avançados possuam funcionalidade de "Function Calling" (como os modelos OpenAI), a implementação `llama.cpp` atinge o mesmo nível de confiabilidade para modelos GGUF, que normalmente não possuem essa capacidade nativa. Esta é uma funcionalidade essencial para a automação pretendida.

**Tabela 3: Esquema Pydantic Essencial para Ficha Técnica**

| Campo (Pydantic) | Tipo de Dado | Descrição | Função no MLLM |
| :--- | :--- | :--- | :--- |
| `product_name` | `str` | Nome de e-commerce conciso e otimizado. | Geração de texto conciso. |
| `category_standard` | `str` | Categoria de alto nível (e.g., "Móveis", "Eletrônicos"). | Classificação zero-shot. |
| `description_long` | `str` | Descrição rica em detalhes, materiais e benefícios (min. 150 palavras). | Geração de texto detalhado. |
| `color_primary` | `str` | Cor dominante do produto (em português). | Extração de atributos. |
| `features_list` | `List[str]` | Lista de três características principais em tópicos. | Sumarização e extração de *selling points*. |

## V. Guia Prático de Implementação e Otimização Avançada

### A. Configuração do Ambiente e Carregamento do MLLM

A implementação deve ser centrada no Celery Worker. A biblioteca `llama-cpp-python` é o runtime de inferência.

1.  **Carregamento do Modelo:** O modelo BakLLaVA deve ser carregado utilizando a classe apropriada (e.g., `LLaVACPPModel` em bibliotecas de alto nível baseadas em `llama.cpp`). Este processo requer o carregamento dos dois arquivos GGUF (o LLM principal e o modelo CLIP).
2.  **Inicialização Única:** É imperativo que a instanciação e o carregamento dos pesos do MLLM na VRAM/RAM ocorra **apenas uma vez**, durante a inicialização do Celery Worker, e não a cada nova tarefa. Isso elimina o alto custo de setup da memória para cada requisição.

### B. Otimizações de Memória e Desempenho em Tempo de Execução

As otimizações em tempo de execução são fundamentais para maximizar a utilização do hardware de consumo.

1.  **Inferência Híbrida (CPU+GPU Offloading):** O `llama.cpp` foi projetado para gerenciar o uso de memória de forma inteligente. Em sistemas com VRAM insuficiente para carregar todas as camadas do modelo (um cenário comum com 8GB de VRAM), a funcionalidade de *offloading* permite carregar as camadas mais sensíveis à latência na GPU e descarregar as camadas restantes para a RAM, executando-as na CPU. Isso otimiza o uso total dos recursos disponíveis.
2.  **Seleção de Quantização:** A escolha da quantização GGUF (e.g., Q4_K_M, Q5_K_M, Q8_0) é um trade-off direto entre performance (velocidade/precisão) e tamanho de memória. Modelos com quantização mais baixa (e.g., Q4_K_M) oferecem maior eficiência e portabilidade, sendo adequados para a primeira implementação, enquanto Q8_0 oferece melhor precisão, mas exige mais memória.

### C. Monitoramento do Pipeline

Um sistema de MLOps robusto requer observabilidade.

1.  **Rastreamento de Tarefas:** O endpoint FastAPI deve imediatamente retornar um `task_id` ao receber a imagem. Este ID permite que o cliente rastreie o estado da tarefa assíncrona (e.g., `PENDING`, `STARTED`, `SUCCESS`), minimizando o tempo de espera percebido.
2.  **Dashboard de Observabilidade:** Recomenda-se a utilização do **Flower**, o dashboard oficial do Celery. O Flower fornece monitoramento em tempo real do estado dos workers (capacidade e saúde) e métricas importantes como a latência de execução de tarefas e as taxas de sucesso/falha, permitindo o ajuste fino dos recursos.

## VI. Conclusões e Recomendações

A análise confirma que o projeto de criar um sistema local e automatizado de catalogação de produtos usando MLLMs é altamente viável, desde que a arquitetura seja estritamente assíncrona e utilize o ecossistema de otimização `llama.cpp`/GGUF.

### A. Síntese da Viabilidade Técnica

A chave para o sucesso reside na gestão eficiente de dois desafios técnicos interligados: a memória do modelo e a latência da inferência.

1.  **Seleção de Modelo Otimizada:** O **BakLLaVA GGUF** (baseado em Mistral 7B) é a escolha técnica superior. Sua arquitetura multimodal e a distribuição quantizada via GGUF o tornam ideal para hardware com 8GB a 16GB de VRAM. A atenção deve ser dada à memória combinada do LLM e do Codificador Visual (CLIP).
2.  **Arquitetura MLOps Essencial:** A adoção do stack **FastAPI + Celery + Redis** não é opcional; é um requisito funcional para desacoplar a requisição HTTP da tarefa de inferência, garantindo a responsividade do sistema.
3.  **Output Determinístico:** A integração do **Pydantic** com o *constrained decoding* nativo do `llama-cpp-python` é fundamental para traduzir a capacidade generativa do LLM em dados estruturados e validados (JSON), permitindo a automação direta do preenchimento de cards de produtos.

### B. Recomendações de Implementação Acionáveis

Para a fase de desenvolvimento, recomendam-se as seguintes ações:

1.  **Priorizar a Estratégia de Armazenamento:** Implementar imediatamente o mecanismo de salvamento de arquivos no FastAPI para um volume compartilhado (Docker Volume) e passar apenas o caminho/ID do arquivo para o Celery Worker, evitando a sobrecarga do broker de mensagens com dados binários de imagem.
2.  **Ajuste Fino de Hardware e Quantização:** Realizar benchmarks internos com diferentes quantizações GGUF (Q4_K_M vs. Q5_K_M) no hardware de destino, monitorando a taxa de tokens/segundo. Para hardware com menos de 12GB de VRAM, configurar o *offloading* de camadas para a CPU (`n_gpu_layers < total_layers`) é mandatório.
3.  **Rigor na Engenharia de Prompt e Pré-processamento:** Desenvolver prompts que não apenas solicitem o formato JSON Pydantic, mas que também incorporem a lista de categorias e o requisito de descrição mínima (150 palavras) para guiar o MLLM. Integrar bibliotecas de pré-processamento (OpenCV/Pillow) no worker para garantir a normalização visual das imagens antes da ingestão pelo CLIP.