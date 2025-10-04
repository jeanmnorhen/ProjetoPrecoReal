# Plano de Transição: Substituição do Gemini API por LLM Local no "Alimentador de Catálogo com IA"

*Documento adaptado para as necessidades do projeto "Preço Real".*

## I. Sumário Executivo e Escolha Estratégica de Modelos

O presente relatório técnico detalha a seleção, otimização e implantação de modelos de linguagem grandes (LLMs) locais para substituir a dependência da API do Google Gemini no `servico-agentes-ia`. O objetivo é replicar a funcionalidade do "Alimentador de Catálogo com IA" — análise de imagens e geração de dados de produtos — utilizando uma arquitetura de microsserviços (Docker, FastAPI, Celery) em um ambiente com recursos computacionais estritamente limitados: o processador **Intel Xeon E5-2673 v3** e **16 GB de RAM**.

### 1.1. Estratégia de Mitigação de Risco e Recomendação de Modelos

A restrição de 16 GB de RAM é o principal gargalo operacional. A inferência de LLMs em CPU exige que o modelo, o cache de contexto e a sobrecarga do sistema residam na memória principal. Exceder a RAM disponível levaria a um estado de *swapping* (uso de disco como memória), tornando a latência inaceitável.

Para atender às duas necessidades distintas (análise de imagem e geração de texto), a recomendação é uma **abordagem híbrida com dois modelos especializados**:

1.  **Para Geração de Texto (a partir de texto):** O modelo escolhido é o **`Meta-Llama-3-8B-Instruct.Q4_K_M.gguf`**.
    *   **Justificativa:** Este modelo oferece um excelente equilíbrio entre qualidade de geração de texto e consumo de recursos (~5.15 GB de RAM). É vastamente superior ao `CodeLlama` (proposto no plano original) para tarefas de conversação e geração de descrições criativas.

2.  **Para Análise de Imagem (Imagem para Texto):** O modelo escolhido é o **`llava-v1.5-7b-Q4_K_M.gguf`**.
    *   **Justificativa:** LLaVA (Large Language and Vision Assistant) é o padrão-ouro para modelos de visão de código aberto. É a única opção viável para substituir a capacidade do `gemini-pro-vision` de analisar imagens. Seu consumo de RAM (~4.86 GB) é gerenciável, mas a inferência de visão em CPU terá **alta latência**, reforçando a necessidade de uma arquitetura assíncrona.

**Mitigação de Qualidade e Erros:** Para garantir a consistência e a qualidade da saída, é indispensável o uso de **Engenharia de Prompt** avançada e a restrição da saída do modelo a um formato **JSON bem definido**, validado via **Pydantic** (conhecido como *Structured Output*). Isso transforma a tarefa de uma geração de texto livre para o preenchimento de um formulário estruturado, aumentando drasticamente a confiabilidade.

### 1.2. Visão Geral das Otimizações Críticas

O desempenho do sistema depende da execução rigorosa de três otimizações:

1.  **Aceleração de Baixo Nível (AVX2):** O runtime `llama-cpp-python` deve ser compilado dentro do Docker, ativando a biblioteca **OpenBLAS** para usar as instruções vetoriais AVX2 do processador Xeon.
2.  **Gerenciamento de Recursos (`n_threads`):** O número de threads de inferência deve ser ajustado para usar os 12 Cores Físicos de forma eficiente, evitando a saturação dos Hyper-Threads.
3.  **Arquitetura Assíncrona (Celery):** A alta latência da inferência em CPU deve ser isolada do frontend. O uso do **Celery** garante que a API (FastAPI) permaneça responsiva, processando as solicitações de IA em segundo plano.

## II. Análise de Hardware e Otimização de Runtime

*(Esta seção permanece relevante, apenas recontextualizada para os novos modelos)*

O processador **Intel Xeon E5-2673 v3** (12 Cores / 24 Threads) com suporte a **AVX2** é o pilar do desempenho. A compilação do `llama-cpp-python` com OpenBLAS é um requisito não-negociável para acelerar as operações de matrizes, que são o coração da inferência. A gestão de threads via workers Celery (ex: 2 workers com `n_threads=6` cada) garantirá o uso ótimo dos 12 cores físicos.

## III. Plano de Implementação Detalhado

A transição será feita modificando o `servico-agentes-ia` e o `frontend-tester`.

### Fase 1: Refatoração do `servico-agentes-ia`

1.  **Atualizar `requirements.txt`**: Adicionar `fastapi`, `uvicorn`, `celery`, `redis`, `llama-cpp-python`, e `instructor`.
2.  **Modificar `Dockerfile`**:
    *   Instalar `libopenblas-dev` e `build-essential`.
    *   Adicionar as variáveis de ambiente `FORCE_CMAKE=1` e `CMAKE_ARGS="-DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS"`.
    *   Modificar o `pip install` para forçar a recompilação do `llama-cpp-python`.
    *   Adicionar um script que baixa os modelos GGUF (`Llama-3-8B` e `llava-v1.5-7b`) para dentro da imagem Docker durante o build.
3.  **Estruturar o Novo Serviço:**
    *   Criar um arquivo para a aplicação **FastAPI** que servirá como gateway.
    *   Criar um arquivo para a configuração do **Celery** e a definição dos workers.
    *   Usar **Redis** (adicionado ao `docker-compose.yml`) como broker para o Celery.

### Fase 2: Implementação da Lógica de IA Local

1.  **Definir o Schema de Saída com Pydantic:**
    ```python
    # Em um arquivo de schemas
    from pydantic import BaseModel, Field
    from typing import List

    class ProductData(BaseModel):
        name: str = Field(description="Nome completo e conciso do produto, incluindo marca e volume/peso se aplicável.")
        categories: List[str] = Field(description="Uma lista de 3 categorias, da mais genérica para a mais específica.")
        description: str = Field(description="Uma descrição técnica e de marketing para o produto.")
    ```

2.  **Criar as Tarefas Celery:**
    *   **`generate_product_from_text(text_query: str) -> ProductData`**:
        *   Carrega o modelo `Llama-3-8B-Instruct`.
        *   Usa a biblioteca `instructor` para aplicar o schema `ProductData` à saída do LLM.
        *   Retorna o objeto Pydantic validado.
    *   **`generate_product_from_image(image_b64: str) -> ProductData`**:
        *   Carrega o modelo `llava-v1.5-7b`.
        *   Usa `instructor` e o mesmo schema `ProductData`.
        *   Retorna o objeto Pydantic validado.

3.  **Adaptar o Endpoint `catalog-intake`:**
    *   Reescrever o endpoint `POST /api/agents/catalog-intake` (agora em FastAPI).
    *   Em vez de chamar a API do Gemini, ele irá despachar a tarefa apropriada para o Celery:
        *   Se receber `text_query`, chama `generate_product_from_text.delay(text_query)`.
        *   Se receber `image_base64`, chama `generate_product_from_image.delay(image_b64)`.
    *   O endpoint deve retornar imediatamente uma resposta **HTTP 202 Accepted** com o `task_id` da tarefa Celery.

4.  **Criar Endpoint de Status da Tarefa:**
    *   Criar um novo endpoint `GET /api/agents/task-status/{task_id}`.
    *   Este endpoint verificará o status da tarefa no backend do Celery.
    *   Se pendente, retorna `{"status": "PENDING"}`.
    *   Se concluída, retorna `{"status": "SUCCESS", "result": ...}` com os dados do produto gerado.
    *   Se falhou, retorna `{"status": "FAILURE", "error": ...}`.

### Fase 3: Integração com o Frontend (`frontend-tester`)

1.  **Modificar a Página "Alimentador de Catálogo" (`/admin/canonicos/page.tsx`):**
    *   A função `handleSubmit` agora receberá um `task_id` na resposta da chamada a `/api/agents/catalog-intake`.
    *   Armazenar este `task_id` no estado do componente.
2.  **Implementar Polling de Status:**
    *   Usar uma biblioteca como **SWR** ou **React Query** (ou um `useEffect` com `setInterval`) para chamar periodicamente o novo endpoint `/api/agents/task-status/{task_id}`.
    *   O polling deve ser condicional (só acontece quando há um `task_id` ativo).
    *   Quando o status da tarefa for `SUCCESS`, exibir o resultado. Se for `FAILURE`, exibir o erro. Enquanto for `PENDING`, continuar exibindo a mensagem "Processando...".

## IV. Conclusão da Transição

Ao final deste plano, o `servico-agentes-ia` será totalmente autônomo e não dependerá mais de APIs externas para sua funcionalidade principal. A arquitetura assíncrona garantirá que a experiência do usuário no frontend permaneça fluida, apesar da maior latência da inferência local em CPU, e o uso de structured output garantirá a qualidade e a consistência dos dados gerados para o catálogo de produtos.
