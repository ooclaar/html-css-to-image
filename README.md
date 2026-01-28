> # API de Conversão de HTML/CSS para Imagem

**Autor**: Ramon Alonso
**Versão**: 1.0.0

## Visão Geral

Esta é uma API robusta e de alta performance para converter conteúdo **HTML e CSS** em imagens **PNG**. A solução foi desenvolvida em Python utilizando o framework **FastAPI** para a criação da API, **Playwright** para a renderização de alta fidelidade do conteúdo web em um navegador headless, e **boto3** para integração transparente com o **AWS S3**.

A ferramenta foi projetada para ser uma alternativa auto-hospedada a serviços como o `htmlcsstoimg.com`, oferecendo flexibilidade, controle e escalabilidade. O projeto está totalmente containerizado com **Docker**, facilitando o deploy em qualquer ambiente.

## Funcionalidades Principais

- **Conversão de Alta Fidelidade**: Utiliza o motor do Chromium via Playwright para garantir que o HTML e CSS sejam renderizados exatamente como em um navegador moderno.
- **API RESTful Completa**: Endpoints intuitivos para gerar imagens, com documentação interativa (Swagger e ReDoc) gerada automaticamente.
- **Upload para AWS S3**: As imagens geradas podem ser automaticamente enviadas para um bucket S3, retornando uma URL pública.
- **Flexibilidade de Resposta**: A API pode retornar a URL da imagem no S3, a imagem em formato Base64, ou ambos.
- **Parâmetros Customizáveis**: Controle total sobre as dimensões da imagem (largura, altura), fator de escala, captura de página inteira e fundo transparente.
- **Containerização com Docker**: Inclui `Dockerfile` e `docker-compose.yml` para um deploy rápido e consistente.
- **Estrutura de Projeto Profissional**: Código modular, documentado e com configurações centralizadas, seguindo as melhores práticas de desenvolvimento.

## Estrutura do Projeto

```
/home/ubuntu/html-to-image-api/
├── app/                    # Módulo principal da aplicação
│   ├── __init__.py         # Inicializador do módulo
│   ├── config.py           # Configurações da aplicação (AWS, Render)
│   ├── main.py             # Lógica da API FastAPI e endpoints
│   ├── models.py           # Modelos Pydantic para request/response
│   ├── renderer.py         # Lógica de renderização com Playwright
│   └── s3_service.py       # Lógica de upload para o AWS S3
├── logs/                   # Diretório para logs da aplicação
├── temp/                   # Diretório para arquivos temporários
├── .env.example            # Exemplo de arquivo de variáveis de ambiente
├── .gitignore              # Arquivos e diretórios a serem ignorados pelo Git
├── Dockerfile              # Instruções para build da imagem Docker
├── docker-compose.yml      # Orquestração de containers para deploy
├── README.md               # Documentação do projeto
└── requirements.txt        # Dependências Python
```

## Como Utilizar

### Pré-requisitos

- Docker e Docker Compose instalados.
- Credenciais da AWS (`AWS_ACCESS_KEY_ID` e `AWS_SECRET_ACCESS_KEY`) com permissão para escrita no bucket S3 desejado.

### 1. Configuração

1.  **Clone o repositório** (ou descompacte o arquivo .zip).
2.  **Crie o arquivo `.env`**: Copie o conteúdo de `.env.example` para um novo arquivo chamado `.env`.

    ```bash
    cp .env.example .env
    ```

3.  **Edite o arquivo `.env`** com suas credenciais da AWS e o nome do seu bucket S3:

    ```ini
    AWS_ACCESS_KEY_ID=sua_access_key_aqui
    AWS_SECRET_ACCESS_KEY=sua_secret_key_aqui
    AWS_REGION=us-east-1
    AWS_S3_BUCKET=seu-bucket-aqui
    DEBUG=false
    ```

### 2. Execução com Docker Compose

Com o Docker em execução, inicie a aplicação com um único comando:

```bash
docker-compose up --build -d
```

A API estará disponível em `http://localhost:8000`.

### 3. Acessando a Documentação da API

Após iniciar o container, você pode acessar a documentação interativa da API no seu navegador:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Endpoints da API

### `POST /api/v1/generate`

Gera uma imagem a partir de HTML/CSS e, por padrão, faz o upload para o S3.

**Exemplo de Requisição (cURL):**

```bash
curl -X POST "http://localhost:8000/api/v1/generate" \
-H "Content-Type: application/json" \
-d '{
  "html": "<div style=\'padding: 20px; background: #f06; color: white;\'><h1>Olá, Mundo!</h1></div>",
  "css": "h1 { font-family: Arial; text-align: center; }",
  "width": 800,
  "height": 400,
  "response_format": "url"
}'
```

**Exemplo de Resposta:**

```json
{
  "success": true,
  "url": "https://seu-bucket-aqui.s3.us-east-1.amazonaws.com/images/2026/01/26/seu_id_unico.png",
  "base64": null,
  "metadata": {
    "width": 800,
    "height": 400,
    "size_bytes": 12345,
    "content_type": "image/png"
  }
}
```

### `POST /api/v1/generate/preview`

Gera uma imagem e a retorna diretamente em formato **Base64**, sem fazer upload para o S3. Ideal para previews rápidos.

**Exemplo de Requisição (cURL):**

```bash
curl -X POST "http://localhost:8000/api/v1/generate/preview" \
-H "Content-Type: application/json" \
-d '{
  "html": "<h1>Preview Rápido</h1>",
  "width": 400,
  "height": 200
}'
```

### `GET /api/v1/health`

Verifica o status da API e de seus serviços dependentes (renderizador e conexão com S3).
