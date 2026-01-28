"""
Aplicação Principal - HTML to Image API
Autor: Ramon Alonso
Versão: 1.0.0

Este módulo define a aplicação FastAPI com todos os endpoints
para conversão de HTML/CSS em imagens PNG e upload para S3.
"""

import base64
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Union

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import app_config, aws_config
from app.models import (
    ImageGenerateRequest,
    ImageGenerateResponse,
    ErrorResponse,
    HealthResponse,
    ResponseFormat
)
from app.renderer import renderer
from app.s3_service import s3_service


# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"{app_config.log_dir}/api.log")
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação.
    Inicializa recursos na startup e limpa na shutdown.
    """
    # Startup
    logger.info(f"Iniciando {app_config.app_name} v{app_config.app_version}")
    yield
    # Shutdown
    logger.info("Encerrando aplicação...")
    await renderer.close()
    logger.info("Aplicação encerrada")


# Criar aplicação FastAPI
app = FastAPI(
    title=app_config.app_name,
    description="""
## API para Conversão de HTML/CSS em Imagens PNG

Esta API permite converter conteúdo HTML e CSS em imagens PNG de alta qualidade,
com upload automático para AWS S3.

### Funcionalidades

- **Renderização HTML/CSS**: Suporte completo a HTML5 e CSS3
- **Dimensões Customizáveis**: Defina largura, altura e escala
- **Upload Automático**: Imagens são armazenadas no AWS S3
- **Múltiplos Formatos de Resposta**: URL, Base64 ou ambos
- **Fundo Transparente**: Suporte a imagens com transparência

### Autor
Ramon Alonso
    """,
    version=app_config.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handler global para exceções HTTP.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="HTTP_ERROR",
            message=str(exc.detail)
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handler global para exceções não tratadas.
    """
    logger.error(f"Erro não tratado: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="INTERNAL_ERROR",
            message="Ocorreu um erro interno no servidor"
        ).model_dump()
    )


@app.get(
    "/",
    summary="Página Inicial",
    description="Retorna informações básicas sobre a API",
    tags=["Geral"]
)
async def root():
    """
    Endpoint raiz com informações da API.
    """
    return {
        "name": app_config.app_name,
        "version": app_config.app_version,
        "author": "Ramon Alonso",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


@app.get(
    "/api/v1/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Verifica o status da API e serviços dependentes",
    tags=["Monitoramento"]
)
async def health_check():
    """
    Verifica a saúde da aplicação e serviços dependentes.
    
    Returns:
        HealthResponse: Status da aplicação e serviços
    """
    services = {
        "renderer": "ok",
        "s3": "not_configured"
    }
    
    # Verificar configuração do S3
    if aws_config.bucket_name:
        try:
            if s3_service.check_connection():
                services["s3"] = "ok"
            else:
                services["s3"] = "error"
        except Exception:
            services["s3"] = "error"
    
    # Determinar status geral
    status = "healthy"
    if services["s3"] == "error":
        status = "degraded"
    
    return HealthResponse(
        status=status,
        version=app_config.app_version,
        services=services
    )


@app.post(
    "/api/v1/generate",
    response_model=Union[ImageGenerateResponse, ErrorResponse],
    summary="Gerar Imagem",
    description="""
Gera uma imagem PNG a partir de conteúdo HTML e CSS.

### Parâmetros

- **html** (obrigatório): Conteúdo HTML a ser renderizado
- **css** (opcional): Estilos CSS adicionais
- **width** (opcional): Largura em pixels (padrão: 1024, máx: 4096)
- **height** (opcional): Altura em pixels (padrão: 768, máx: 4096)
- **scale** (opcional): Fator de escala (padrão: 1.0, máx: 3.0)
- **full_page** (opcional): Capturar página inteira (padrão: false)
- **transparent** (opcional): Fundo transparente (padrão: false)
- **response_format** (opcional): Formato da resposta (url, base64, both)

### Exemplo de Requisição

```json
{
    "html": "<div style='padding: 20px; background: #4A90D9;'><h1>Olá!</h1></div>",
    "css": "h1 { color: white; }",
    "width": 800,
    "height": 600
}
```
    """,
    tags=["Geração de Imagem"],
    responses={
        200: {"model": ImageGenerateResponse, "description": "Imagem gerada com sucesso"},
        400: {"model": ErrorResponse, "description": "Erro de validação"},
        500: {"model": ErrorResponse, "description": "Erro interno"}
    }
)
async def generate_image(request: ImageGenerateRequest):
    """
    Gera uma imagem PNG a partir de HTML/CSS e faz upload para S3.
    
    Args:
        request: Dados da requisição com HTML, CSS e opções
        
    Returns:
        ImageGenerateResponse: URL e/ou Base64 da imagem gerada
        
    Raises:
        HTTPException: Se houver erro na renderização ou upload
    """
    logger.info(
        f"Requisição recebida: {request.width}x{request.height}, "
        f"format: {request.response_format}"
    )
    
    try:
        # Renderizar HTML para imagem
        image_bytes = await renderer.render_to_image(
            html_content=request.html,
            css_content=request.css,
            width=request.width,
            height=request.height,
            scale=request.scale,
            full_page=request.full_page,
            transparent=request.transparent
        )
        
        response_data = {
            "success": True,
            "metadata": {
                "width": request.width,
                "height": request.height,
                "scale": request.scale,
                "size_bytes": len(image_bytes),
                "content_type": "image/png",
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
        # Incluir Base64 se solicitado
        if request.response_format in [ResponseFormat.BASE64, ResponseFormat.BOTH]:
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            response_data["base64"] = f"data:image/png;base64,{image_base64}"
        
        # Fazer upload para S3 se solicitado
        if request.response_format in [ResponseFormat.URL, ResponseFormat.BOTH]:
            if not aws_config.bucket_name:
                raise HTTPException(
                    status_code=500,
                    detail="Bucket S3 não configurado. Configure a variável AWS_S3_BUCKET"
                )
            
            upload_result = await s3_service.upload_bytes(
                data=image_bytes,
                content_type="image/png",
                prefix="images",
                extension="png",
                metadata={
                    "width": str(request.width),
                    "height": str(request.height)
                }
            )
            
            response_data["url"] = upload_result["url"]
            response_data["metadata"]["s3_key"] = upload_result["key"]
            response_data["metadata"]["s3_bucket"] = upload_result["bucket"]
        
        logger.info(f"Imagem gerada com sucesso: {len(image_bytes)} bytes")
        
        return ImageGenerateResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao gerar imagem: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar imagem: {str(e)}"
        )


@app.post(
    "/api/v1/generate/preview",
    summary="Gerar Preview (Base64)",
    description="""
Gera uma imagem PNG e retorna apenas em Base64, sem fazer upload para S3.
Útil para previews rápidos antes de confirmar a geração final.
    """,
    tags=["Geração de Imagem"],
    responses={
        200: {"model": ImageGenerateResponse, "description": "Preview gerado com sucesso"},
        400: {"model": ErrorResponse, "description": "Erro de validação"},
        500: {"model": ErrorResponse, "description": "Erro interno"}
    }
)
async def generate_preview(request: ImageGenerateRequest):
    """
    Gera uma imagem PNG e retorna em Base64 sem fazer upload para S3.
    
    Args:
        request: Dados da requisição com HTML, CSS e opções
        
    Returns:
        ImageGenerateResponse: Imagem em Base64
    """
    # Forçar formato Base64 para preview
    request.response_format = ResponseFormat.BASE64
    
    try:
        image_bytes = await renderer.render_to_image(
            html_content=request.html,
            css_content=request.css,
            width=request.width,
            height=request.height,
            scale=request.scale,
            full_page=request.full_page,
            transparent=request.transparent
        )
        
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        return ImageGenerateResponse(
            success=True,
            base64=f"data:image/png;base64,{image_base64}",
            metadata={
                "width": request.width,
                "height": request.height,
                "scale": request.scale,
                "size_bytes": len(image_bytes),
                "content_type": "image/png",
                "generated_at": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Erro ao gerar preview: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar preview: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=app_config.debug
    )
