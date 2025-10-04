Relatório Técnico de Implementação Local de IA Multimodal para Automação de Catálogo (Arquitetura GGUF/MLOps)
I. Resumo Executivo e Conclusões da Viabilidade Técnica
A. O Caso de Uso: Automação de Fichas Técnicas de Produtos
O foco desta documentação é estabelecer a viabilidade e o blueprint arquitetônico para a criação de um pipeline robusto e local, capaz de automatizar a geração de fichas técnicas de produtos. O sistema deve ingerir uma imagem do produto e, subsequentemente, gerar dados estruturados essenciais, incluindo o nome do produto conciso, a categorização precisa, e uma descrição textual coerente e rica, pronta para preencher um card de produto de e-commerce.
Esta aplicação exige uma arquitetura Multimodal de Linguagem (MLLM) que combine reconhecimento visual detalhado (Vision-Language Model, VLM) com geração sofisticada e estruturada de linguagem natural (Large Language Model, LLM). A viabilidade deste projeto em infraestrutura de consumo é alcançada estritamente através da seleção de MLLMs otimizados para execução local, utilizando o ecossistema GGUF/llama.cpp e uma arquitetura de serviço fundamentalmente assíncrona.
B. Síntese das Escolhas Tecnológicas Chave
A análise técnica converge na seleção de um stack tecnológico otimizado para superar os desafios de memória e latência inerentes à inferência multimodal em hardware local:
1. Modelo Multimodal (MLLM) Preferencial: O BakLLaVA 1 - 7B, construído sobre a arquitetura LLaVA 1.5, é a escolha técnica recomendada. Sua base no Mistral AI 7B oferece desempenho de geração de linguagem superior ao de muitos modelos LLaMA-base, o que é crítico para produzir descrições ricas e coerentes.
2. Otimização e Runtime: O formato GGUF (General Use Format), desenvolvido pelo projeto llama.cpp, é o facilitador central da viabilidade local. Ele permite a quantização agressiva dos pesos do modelo, reduzindo drasticamente a pegada de memória. Modelos de 7 bilhões de parâmetros podem ser quantizados, por exemplo, para aproximadamente 4.5 GB na precisão Q4_K_M, tornando-os gerenciáveis em GPUs com VRAM limitada (8 GB ou mais).
3. Arquitetura MLOps Essencial: A stack FastAPI + Celery + Redis é um requisito funcional. A latência inerente à inferência multimodal exige o desacoplamento da requisição HTTP do processo de geração, que pode levar vários segundos. O uso de Celery como sistema de fila de tarefas garante que a API principal (FastAPI) permaneça responsiva, retornando imediatamente um task_id ao cliente.
C. Ações Críticas de Implementação
O sucesso em traduzir a capacidade generativa do MLLM em dados de catálogo utilizáveis é contingente à implementação rigorosa de duas estratégias:
1. Gerenciamento de Arquivos por Volume Compartilhado: A transferência de imagens de alta resolução deve evitar a sobrecarga do broker de mensagens (Redis). O FastAPI deve salvar o arquivo em um volume persistente (e.g., Docker Volume) e apenas o caminho de referência (Path/Storage ID) deve ser enviado ao Celery Worker.
2. Output Estruturado Determinístico: A integração do Pydantic para definição de esquema de dados, juntamente com o constrained decoding nativo do llama-cpp-python, é fundamental. Isso força o MLLM a gerar uma saída JSON que seja sintaticamente válida e aderente ao esquema, eliminando a necessidade de lógica complexa de parsing e validação posterior.
II. Fundamentos e Escolha do Modelo Multimodal (MLLM)
A. A Arquitetura MLLM Local (LLaVA-like)
A arquitetura MLLM opera na interconexão de três módulos distintos. A otimização de memória deve levar em conta a pegada combinada de todos eles.
1. Codificador Visual (Vision Encoder)
O Codificador Visual é responsável por processar a imagem de entrada e extrair características significativas. O padrão de mercado para sistemas LLaVA é o CLIP (Contrastive Language–Image Pre-training), comumente utilizando a variante ViT-L/14 (Vision Transformer - Large, Patch 14). O CLIP é um modelo que mapeia tanto imagens quanto texto para um espaço vetorial compartilhado, sendo a base para tarefas de zero-shot classification e retrieval. Versões pré-treinadas pela OpenAI (openai/clip-vit-large-patch14) ou variantes ajustadas pela comunidade (como aquelas treinadas com o LAION-2B, e.g., laion/CLIP-ViT-L-14-laion2B-s32B-b82K) formam a base do processamento visual.
2. Projetor e Decodificador de Texto (Text Decoder)
O Projetor atua como uma camada intermediária (frequentemente uma Rede Neural Multicamadas, MLP) que traduz os embeddings visuais extraídos pelo Codificador para um formato compreensível pelo LLM. O Decodificador de Texto é o LLM base (Mistral ou LLaMA) que recebe a instrução textual (o prompt) e os embeddings visuais, gerando o texto descritivo e estruturado de saída.
B. A Escolha Otimizada e a Otimização GGUF
A variante BakLLaVA 1 - 7B é selecionada por sua base no Mistral AI 7B. Este LLM base demonstrou consistentemente um desempenho superior em tarefas de geração de linguagem em comparação com modelos Llama 2 de maior porte (13B), o que é essencial para o requisito de geração de descrições ricas e longas de produtos.
Para a execução local, o formato GGUF (General Use Format), desenvolvido sob o projeto llama.cpp , é indispensável. O GGUF permite a quantização (compressão de pesos do modelo) em níveis de precisão extremamente baixos (e.g., 4-bit, 8-bit). A quantização Q4_K_M, por exemplo, reduz um modelo de 7B de 14 GB (precisão FP16) para aproximadamente 4.5 GB de footprint de memória. Existem opções ainda mais compactas, como a quantização Q3_K_L, que pode reduzir o modelo para 3.82 GB. O modelo BakLLaVA GGUF recomendado é distribuído pela comunidade, como em advanced-stack/bakllava-mistral-v1-gguf, com a variante Q4_K_M em cerca de 4.37 GB.
C. Análise de Requisitos de Hardware e Memória
O desafio da memória multimodal reside na soma do LLM quantizado e dos requisitos do Codificador Visual (CLIP), que também requer memória para seus pesos e ativações.
Table II.1: Comparativo de Viabilidade Técnica e Otimização de MLLMs GGUF (Recomendação)
Modelo Base (LLM)
	VLM Associado (CLIP Variant)
	Tamanho Típico GGUF (Q4_K_M)
	Requisito Mínimo VRAM Estimado (Início)
	Foco e Vantagem
	LLaVA 1.5 - 7B
	ViT-L/14
	~4.5 GB (LLM) + CLIP
	8 GB (Híbrido CPU/GPU)
	Alta performance de VLM em hardware restrito.
	BakLLaVA 1 - 7B (Mistral)
	CLIP
	~4.5 GB (LLM) + CLIP
	8 GB (Híbrido CPU/GPU)
	Recomendado: Baseado em Mistral (mais poderoso para linguagem).
	LLaVA-NeXT 13B
	ViT-L/14
	~8 GB (LLM) + CLIP
	12-16 GB
	Maior precisão na categorização/descrição, exigindo mais VRAM.
	Para garantir fluidez na geração de descrições ricas (atingindo taxas de 40 tokens/segundo ou mais), o requisito prático de VRAM para um modelo 7B quantizado é de 8 GB no mínimo. No entanto, 12 GB a 16 GB são altamente preferenciais para acomodar modelos maiores ou contextos mais longos.
D. Considerações Críticas: Licenciamento e Inferência Híbrida
A escolha do BakLLaVA 1, embora tecnicamente ideal, possui uma ressalva importante: o modelo foi treinado com um corpus de dados LLaVA que não é comercialmente permissivo. Para um projeto de automação de catálogo comercial, isso representa um risco de licenciamento. Assim, o uso do BakLLaVA 1 deve ser restrito à Prova de Conceito (PoC). A equipe de engenharia deve planejar migrar para o BakLLaVA 2 assim que for lançado, pois este é prometido como uma versão com dataset significativamente maior e comercialmente viável.
Além disso, a otimização GGUF impõe um desafio de desempenho na inferência híbrida. Em cenários onde a VRAM é insuficiente (e.g., apenas 8 GB), as camadas do modelo precisam ser descarregadas (offloaded) para a RAM do sistema e executadas pela CPU. Embora isso torne a execução possível, a latência de inferência passa a depender criticamente da velocidade de transferência de dados (largura de banda da RAM e desempenho single-thread da CPU). Observações de implementações reais indicam que, mesmo com hardware aparentemente suficiente, o tempo de resposta pode se estender de 30 a 60 segundos se o offloading não for eficiente. Portanto, o design de hardware para o Celery Worker deve priorizar CPUs com alto desempenho e RAM de alta frequência para mitigar essa latência de transferência.
III. A Estratégia de MLOps Assíncrono para Inferência em Produção
A. Imperativo da Assincronicidade no Pipeline
A execução de tarefas multimodais é inerentemente um long-running process. Mesmo com a otimização GGUF que permite taxas de geração elevadas, a criação de uma descrição longa pode consumir vários segundos. Se esta inferência for executada no thread principal de uma API web síncrona, o resultado será o bloqueio do event loop do servidor, o que causa timeouts para os usuários e compromete a escalabilidade e a experiência geral do sistema.
A solução arquitetônica funcional é a desvinculação da requisição HTTP do processamento pesado. O padrão MLOps exige o uso do stack FastAPI (para gerenciar endpoints e entrada de dados) e Celery (como sistema de fila de tarefas), utilizando Redis ou RabbitMQ como broker. O cliente envia a imagem e o prompt ao FastAPI, que imediatamente retorna um task_id e atribui o trabalho de inferência a um Celery Worker em background. O cliente pode então consultar o status da tarefa, permitindo que a aplicação permaneça totalmente responsiva.
B. Gestão Robusta de Arquivos Multimodais (Imagens)
A manipulação de arquivos binários grandes, como imagens de alta resolução, é um ponto crucial de otimização no pipeline assíncrono.
O padrão de arquitetura deve evitar a serialização do conteúdo binário da imagem (por exemplo, Base64) e sua inclusão direta como argumento na mensagem da tarefa Celery. Imagens codificadas em Base64 resultam em strings de dados massivas que sobrecarregam o broker de mensagens (Redis), elevam a latência de enfileiramento e limitam a escalabilidade do sistema.
A estratégia MLOps recomendada é: o endpoint FastAPI recebe a imagem (utilizando o tipo UploadFile que trata o arquivo como stream para evitar o consumo total de RAM no upload inicial ) e a salva em um volume de armazenamento persistente compartilhado (e.g., MinIO ou um volume Docker montado). O FastAPI envia à tarefa Celery apenas a referência do arquivo (o caminho no sistema de arquivos ou um ID de storage), juntamente com os parâmetros do prompt. O Celery Worker, por sua vez, acessa o volume compartilhado, lê o arquivo de imagem referenciado, realiza o processamento e armazena os resultados.
Table III.1: Estratégias de Gerenciamento de Arquivos no Pipeline Assíncrono
Estratégia
	Transferência
	Vantagens
	Desvantagens
	Recomendação MLOps
	Byte Stream (Base64)
	Codificação em string na mensagem Celery.
	Simples de implementar em Python.
	Risco de saturação do broker; Alta latência de serialização/desserialização.
	Não Adotar (Risco de Inescalabilidade)
	Path/Storage ID
	FastAPI salva o arquivo, Celery recebe o caminho/ID.
	Altamente escalável; Lida com arquivos grandes.
	Requer sistema de arquivos compartilhado (Volume Docker).
	Essencial (Robustez e Escalabilidade)
	C. Contêinerização e Otimização do Worker (Docker)
Para garantir reprodutibilidade e execução padronizada, o ambiente deve ser contêinerizado via Docker Compose, englobando a API (FastAPI), o Broker (Redis) e o Worker de Inferência (Celery).
Otimizar o Worker de Inferência é crucial. A biblioteca llama-cpp-python — o runtime de inferência — exige ferramentas de desenvolvimento e dependências C/C++ para compilação. Além disso, o pré-processamento de imagens no worker requer bibliotecas como OpenCV ou Pillow. Para manter o tamanho da imagem Docker reduzido e seguro, é recomendável o uso de imagens base Python slim (python:3.x-slim) e a adoção de uma construção multi-stage para garantir que as dependências de construção sejam descartadas na imagem final.
É fundamental que o carregamento dos pesos do MLLM (o modelo BakLLaVA e o modelo CLIP) na VRAM/RAM ocorra apenas uma vez, durante a inicialização do Celery Worker. A instanciação e o carregamento do modelo a cada tarefa introduziriam um custo de setup proibitivo em termos de latência.
IV. Garantia de Output Determinístico: Pydantic e Constrained Decoding
O objetivo final do pipeline é preencher automaticamente um card de produto. Para que a saída do MLLM seja diretamente consumível por sistemas a jusante (e.g., um banco de dados de catálogo), ela deve ser 100% confiável e aderente a um esquema de dados rígido, evitando a geração de texto livre e as variações inerentes dos LLMs.
A. Pydantic como Contrato de Dados (JSON Schema Definition)
A biblioteca Pydantic resolve o desafio da estruturação, permitindo a definição de um esquema de dados rigoroso através de type hints em Python, utilizando classes que herdam de pydantic.BaseModel.
Este esquema define o contrato de dados, especificando campos essenciais como product_name, category_standard, e description_long, juntamente com seus tipos esperados (str, List[str], etc.). As docstrings e as funções Field do Pydantic são aproveitadas para fornecer instruções adicionais ao MLLM sobre o conteúdo desejado para cada campo (e.g., requisitos de volume ou estilo). O Pydantic realiza a validação da saída JSON contra o esquema definido, crucial para prevenir falhas de tipagem ou ausência de campos no pipeline subsequente.
Table IV.1: Esquema Pydantic Essencial para Ficha Técnica (Requisito de Output)
Campo (Pydantic)
	Tipo de Dado
	Descrição
	Função no MLLM
	product_name
	str
	Nome de e-commerce conciso e otimizado.
	Geração de título.
	category_standard
	str
	Categoria de alto nível (e.g., "Móveis", "Eletrônicos").
	Classificação zero-shot.
	description_long
	str
	Descrição rica em detalhes, materiais e benefícios (min. 150 palavras).
	Geração de texto detalhado.
	color_primary
	str
	Cor dominante do produto (em português).
	Extração de atributos.
	features_list
	List[str]
	Lista de três a cinco características principais em tópicos.
	Sumarização e extração de selling points.
	B. Forçando o JSON com Constrained Decoding
A simples instrução no prompt para formatar a saída como JSON não garante a integridade gramatical ou a aderência ao esquema. Para obter confiabilidade, a implementação deve utilizar o constrained decoding (decodificação restrita).
A biblioteca llama-cpp-python oferece suporte nativo para restringir a resposta a um JSON válido, ou a um JSON Schema específico, por meio do argumento response_format na chamada de inferência. Este mecanismo utiliza o esquema Pydantic (convertido para JSON Schema) para guiar o processo de geração de tokens. O MLLM é forçado a selecionar apenas tokens que formam um JSON sintaticamente correto e que respeitam a tipagem e estrutura definidas no esquema, garantindo a conversão da capacidade generativa em dados estruturados validados. Esta funcionalidade é essencial para replicar a confiabilidade de mecanismos de "Function Calling" em modelos GGUF locais.
V. Otimização Avançada e Fluxo de Trabalho do Worker
A. Pré-processamento Obrigatório de Imagem para MLLM
O desempenho e a precisão do MLLM na identificação de atributos são diretamente proporcionais à qualidade e consistência da entrada visual. Imagens de produtos reais, que variam em iluminação e ruído, podem levar a resultados inconsistentes.
1. Redimensionamento e Normalização Dimensional: Os Codificadores Visuais (como o CLIP ViT-L/14) são treinados em dimensões fixas (e.g., 224x224, 336x336 ). O Celery Worker deve utilizar bibliotecas como OpenCV ou Pillow para redimensionar a imagem de entrada para um formato padronizado antes da ingestão.
2. Adaptação de Domínio (Domain Adaptation): É crucial aplicar técnicas para reduzir o domain shift entre as condições da imagem real do produto e o ambiente de treinamento do modelo (e.g., LAION). Técnicas de correção de cor, realce de contraste ou correspondência de histograma (em espaços de cor como YCrCb) aumentam a resiliência e a precisão do MLLM na extração de atributos, garantindo que variações ambientais não mascarem as características intrínsecas do produto.
B. Engenharia de Prompt Multimodal Otimizada
O prompt de instrução serve como a interface de controle do MLLM, exigindo precisão para extrair dados estruturados.
O prompt deve ser dividido para abordar os múltiplos objetivos:
* Instrução de Função: Direcionar o MLLM a se comportar como um "analista de catálogo".
* Restrição de Formato: Solicitar explicitamente que a saída seja um objeto JSON aderente ao esquema Pydantic definido.
* Restrição de Conteúdo: Incorporar requisitos de volume (e.g., "gere uma descrição otimizada para SEO, focando em benefícios, com no mínimo 150 palavras") e, idealmente, fornecer uma lista restrita de categorias para a classificação zero-shot.
C. Otimizações de Memória em Tempo de Execução (llama-cpp-python)
A otimização do runtime é essencial para maximizar a taxa de tokens/segundo em hardware de consumo.
1. Seleção de Quantização: A escolha entre as diferentes quantizações GGUF (Q4_K_M, Q5_K_M, Q8_0) representa um trade-off direto entre performance/precisão e tamanho de memória. A equipe deve realizar benchmarks internos monitorando a taxa de geração em tokens/segundo e a acurácia do JSON gerado para calibrar a melhor opção para o hardware de destino. Q4_K_M é a escolha de maior eficiência para a implementação inicial.
2. Inferência Híbrida (Offloading): Em sistemas com VRAM insuficiente para o modelo completo (tipicamente abaixo de 12 GB), a configuração de offloading no llama-cpp-python é obrigatória. Isso envolve definir um número de camadas (parâmetro n_gpu_layers) que serão carregadas na GPU, enquanto o restante será descarregado para a RAM e executado pela CPU. Este gerenciamento inteligente otimiza a utilização total dos recursos, embora a performance geral possa ser limitada pela latência de comunicação CPU-GPU.
VI. Recursos Essenciais do Hugging Face Hub
Para facilitar a implementação, as referências diretas a modelos e datasets do Hugging Face Hub são cruciais, fornecendo os componentes GGUF necessários e os recursos para avaliação e benchmarking.
A. Modelos MLLM e Pesos GGUF Recomendados
A inferência local depende da obtenção de pesos GGUF compatíveis com llama.cpp.
Table VI.1: Modelos Chave do Hugging Face para o Pipeline GGUF
Tipo de Recurso
	Nome Recomendado (Hugging Face Path)
	Arquivo GGUF (Exemplo Q4_K_M)
	Propósito no Projeto
	MLLM (GGUF)
	advanced-stack/bakllava-mistral-v1-gguf
	bakllava-mistral-v1-gguf.Q4_K_M.gguf (~4.37 GB)
	Motor de inferência multimodal para geração de JSON estruturado.
	Vision Encoder
	openai/clip-vit-large-patch14
	Componente fundamental da arquitetura LLaVA/BakLLaVA.
	Codificador Visual, responsável pela extração de features visuais.
	Opção Alternativa (Maior Precisão)
	LLaVA-NeXT 13B (via community GGUF)
	~8 GB (Q4_K_M)
	Opção para benchmarking e maior precisão, requer VRAM superior (12-16 GB).
	B. Datasets Multimodais de E-commerce para Avaliação
O sucesso da automação depende da capacidade do MLLM de operar no domínio de e-commerce.
1. crossingminds/shopping-queries-image-dataset  Este dataset é altamente recomendado para a fase de avaliação. Ele estende o Shopping Queries Dataset ao incluir informações de imagem e embeddings visuais, além de consultas associadas. É um recurso valioso para benchmarking da capacidade de classificação, extração de atributos e teste da performance do MLLM em cenários de e-commerce.
2. Recursos Genéricos e Metodológicos Para além de datasets de produto, referências metodológicas como o paper que propõe a abordagem ModICT (Multimodal In-Context Tuning) são úteis para orientar o fine-tuning futuro. Esta metodologia foca em gerar descrições ricas, otimizadas com palavras-chave de marketing, um objetivo direto do campo description_long. Recursos de Image Captioning genéricos, como aqueles baseados em BLIP ou TrOCR , podem servir para tarefas auxiliares, como reconhecimento de texto em rótulos de produtos, se a extração de atributos for complementada por OCR.
C. Implicações Futuras: Retrieval-Augmented Generation (RAG) Multimodal
O uso do Codificador Visual (CLIP) para extrair embeddings visuais e textuais abre caminho para a próxima fase do projeto: a integração de Geração Aumentada por Recuperação (RAG) Multimodal.
Em vez de confiar apenas na memória e capacidade do MLLM, os embeddings visuais dos produtos podem ser indexados em um Vector Database eficiente (como FAISS ou Qdrant ). Isso permitiria que o Celery Worker executasse uma pesquisa de similaridade de imagem antes da inferência, recuperando metadados ou descrições templates de produtos já catalogados que são visualmente semelhantes ao produto de entrada. O MLLM então utilizaria essas informações recuperadas como contexto adicional no prompt, aumentando significativamente a confiabilidade e a precisão da categorização e da geração da descrição final. O crossingminds/shopping-queries-image-dataset é o recurso ideal para iniciar a prova de conceito dessa arquitetura de retrieval.
VII. Conclusões e Roadmap de Implementação
A. Síntese do Blueprint Arquitetônico para Produção
A arquitetura de produção deve ser rigorosamente assíncrona e otimizada para o runtime GGUF/llama.cpp.
Table VII.1: Resumo do Stack Tecnológico de Produção
Componente
	Ferramenta/Modelo Recomendado
	Requisito Crítico
	API Gateway
	FastAPI
	Asynchronous handling, retorno imediato de task_id.
	Worker de Inferência
	Celery Worker (Python/Docker)
	Instanciação Única do MLLM GGUF, Offloading otimizado (CPU/GPU).
	Modelo Multimodal
	BakLLaVA 1 - 7B (GGUF)
	Quantização Q4_K_M ou superior, atenção à licença comercial.
	Broker de Mensagens
	Redis
	Gerenciamento de filas de tarefas.
	Gestão de Arquivos
	Docker Volume Persistente
	Padrão Path/Storage ID para imagens grandes, evitando saturação do Redis.
	Output Quality
	Pydantic + llama-cpp-python
	Constrained Decoding para JSON validado, garantindo a integridade dos dados.
	B. Roadmap de Ações Críticas
Para a fase de desenvolvimento e implantação inicial, as seguintes ações são mandatadas para mitigar riscos e garantir a funcionalidade essencial:
1. Configuração da Infraestrutura (MLOps): Priorizar a implementação do ambiente Docker Compose, garantindo o volume persistente compartilhado. O endpoint FastAPI deve ser construído para salvar arquivos e enfileirar tarefas no Celery Worker, passando apenas o caminho do arquivo (ID).
2. Otimização do Runtime GGUF: Configurar o Celery Worker para a instalação do llama-cpp-python e a inicialização única do BakLLaVA GGUF (Q4_K_M). Em hardware com VRAM limitada (8 GB), a configuração imediata do offloading de camadas (n_gpu_layers) para a CPU é mandatório.
3. Implementação da Qualidade de Output: Definir o esquema Pydantic para a ficha técnica (Tabela IV.1) e integrar o constrained decoding na chamada de inferência do llama-cpp-python. Esta etapa garante que o produto do trabalho seja imediatamente consumível pelo sistema de catálogo.
4. Pré-processamento e Engenharia de Prompt: Implementar as bibliotecas OpenCV/Pillow no Celery Worker para realizar o pré-processamento obrigatório de imagem (normalização dimensional e adaptação de domínio). Desenvolver prompts que incorporem as restrições Pydantic e os requisitos de descrição mínima (150 palavras).
5. Monitoramento e Avaliação: Configurar o dashboard Flower para rastreamento de tarefas, permitindo o monitoramento contínuo da latência real (tokens/segundo) e a saúde dos workers. Utilizar o crossingminds/shopping-queries-image-dataset para benchmarking inicial da acurácia e precisão da extração de atributos.
Referências citadas
1. SkunkworksAI/BakLLaVA-1 - Hugging Face, https://huggingface.co/SkunkworksAI/BakLLaVA-1 2. advanced-stack/bakllava-mistral-v1-gguf - Hugging Face, https://huggingface.co/advanced-stack/bakllava-mistral-v1-gguf 3. openai/clip-vit-large-patch14 - Hugging Face, https://huggingface.co/openai/clip-vit-large-patch14 4. sentence-transformers/clip-ViT-L-14 - Hugging Face, https://huggingface.co/sentence-transformers/clip-ViT-L-14 5. laion/CLIP-ViT-L-14-laion2B-s32B-b82K - Hugging Face, https://huggingface.co/laion/CLIP-ViT-L-14-laion2B-s32B-b82K 6. ggml-org/llama.cpp: LLM inference in C/C++ - GitHub, https://github.com/ggml-org/llama.cpp 7. abetlen/BakLLaVA-1-GGUF - Hugging Face, https://huggingface.co/abetlen/BakLLaVA-1-GGUF 8. Using Llama-cpp with FastAPI to connect a html. #166 - GitHub, https://github.com/abetlen/llama-cpp-python/issues/166 9. Celery and Background Tasks. Using FastAPI with long running tasks | by Hitoruna | Medium, https://medium.com/@hitorunajp/celery-and-background-tasks-aebb234cae5d 10. openai/clip-vit-large-patch14-336 - Hugging Face, https://huggingface.co/openai/clip-vit-large-patch14-336 11. GGUF usage with llama.cpp - Hugging Face, https://huggingface.co/docs/hub/en/gguf-llamacpp 12. crossingminds/shopping-queries-image-dataset - Hugging Face, https://huggingface.co/datasets/crossingminds/shopping-queries-image-dataset 13. A Multimodal In-Context Tuning Approach for E-Commerce Product Description Generation, https://huggingface.co/papers/2402.13587 14. What is Image-to-Text? - Hugging Face, https://huggingface.co/tasks/image-to-text 15. Embedding multimodal data for similarity search using transformers, datasets and FAISS - Hugging Face Open-Source AI Cookbook, https://huggingface.co/learn/cookbook/en/faiss_with_hf_datasets_and_clip 16. 25 Top MLOps Tools You Need to Know in 2025 - DataCamp, https://www.datacamp.com/blog/top-mlops-tools