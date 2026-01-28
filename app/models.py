"""
Modelos de Dados da API
Autor: Ramon Alonso
Versão: 1.0.0

Este módulo define os schemas Pydantic para validação
de requisições e formatação de respostas da API.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class ResponseFormat(str, Enum):
    """
    Formatos de resposta suportados pela API.
    """
    URL = "url"           # Retorna apenas a URL do S3
    BASE64 = "base64"     # Retorna imagem em Base64
    BOTH = "both"         # Retorna URL e Base64


class ImageGenerateRequest(BaseModel):
    """
    Schema de requisição para geração de imagem.
    
    Attributes:
        html: Conteúdo HTML a ser renderizado (obrigatório)
        css: Estilos CSS a serem aplicados (opcional)
        width: Largura da imagem em pixels (padrão: 1024)
        height: Altura da imagem em pixels (padrão: 768)
        scale: Fator de escala do dispositivo (padrão: 1.0)
        full_page: Se True, captura a página inteira
        transparent: Se True, usa fundo transparente
        response_format: Formato da resposta (url, base64, both)
    """
    html: str = Field(
        ...,
        min_length=1,
        description="Conteúdo HTML a ser renderizado"
    )
    css: Optional[str] = Field(
        default=None,
        description="Estilos CSS a serem aplicados ao HTML"
    )
    width: int = Field(
        default=1024,
        ge=1,
        le=4096,
        description="Largura da imagem em pixels (1-4096)"
    )
    height: int = Field(
        default=768,
        ge=1,
        le=4096,
        description="Altura da imagem em pixels (1-4096)"
    )
    scale: float = Field(
        default=1.0,
        ge=0.1,
        le=3.0,
        description="Fator de escala do dispositivo (0.1-3.0)"
    )
    full_page: bool = Field(
        default=False,
        description="Se True, captura a página inteira incluindo scroll"
    )
    transparent: bool = Field(
        default=False,
        description="Se True, usa fundo transparente na imagem"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.URL,
        description="Formato da resposta: url, base64 ou both"
    )
    
    @field_validator('html')
    @classmethod
    def validate_html_content(cls, v: str) -> str:
        """
        Valida que o HTML não está vazio após strip.
        """
        if not v.strip():
            raise ValueError("O conteúdo HTML não pode estar vazio")
        return v
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "html": "<div style='padding: 20px; background: #4A90D9; color: white; font-family: Arial;'><h1>Olá Mundo!</h1><p>Esta é uma imagem gerada via API.</p></div>",
                    "css": "h1 { font-size: 32px; } p { font-size: 18px; }",
                    "width": 800,
                    "height": 600,
                    "scale": 1.0,
                    "full_page": False,
                    "transparent": False,
                    "response_format": "url"
                }
            ]
        }
    }


class ImageGenerateResponse(BaseModel):
    """
    Schema de resposta para geração de imagem bem-sucedida.
    
    Attributes:
        success: Indica se a operação foi bem-sucedida
        url: URL pública da imagem no S3 (se response_format inclui url)
        base64: Imagem codificada em Base64 (se response_format inclui base64)
        metadata: Informações adicionais sobre a imagem gerada
    """
    success: bool = Field(
        default=True,
        description="Indica se a operação foi bem-sucedida"
    )
    url: Optional[str] = Field(
        default=None,
        description="URL pública da imagem no S3"
    )
    base64: Optional[str] = Field(
        default=None,
        description="Imagem codificada em Base64"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadados da imagem gerada"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "url": "https://bucket.s3.us-east-1.amazonaws.com/images/2026/01/26/abc123.png",
                    "base64": None,
                    "metadata": {
                        "width": 800,
                        "height": 600,
                        "size_bytes": 45678,
                        "content_type": "image/png"
                    }
                }
            ]
        }
    }


class ErrorResponse(BaseModel):
    """
    Schema de resposta para erros.
    
    Attributes:
        success: Sempre False para erros
        error: Código do erro
        message: Mensagem descritiva do erro
        details: Detalhes adicionais (opcional)
    """
    success: bool = Field(
        default=False,
        description="Sempre False para erros"
    )
    error: str = Field(
        ...,
        description="Código do erro"
    )
    message: str = Field(
        ...,
        description="Mensagem descritiva do erro"
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Detalhes adicionais do erro"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": False,
                    "error": "VALIDATION_ERROR",
                    "message": "O conteúdo HTML não pode estar vazio",
                    "details": {"field": "html"}
                }
            ]
        }
    }


class HealthResponse(BaseModel):
    """
    Schema de resposta para health check.
    
    Attributes:
        status: Status da aplicação (healthy, unhealthy)
        version: Versão da API
        services: Status dos serviços dependentes
    """
    status: str = Field(
        ...,
        description="Status da aplicação"
    )
    version: str = Field(
        ...,
        description="Versão da API"
    )
    services: Dict[str, str] = Field(
        default_factory=dict,
        description="Status dos serviços dependentes"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "healthy",
                    "version": "1.0.0",
                    "services": {
                        "renderer": "ok",
                        "s3": "ok"
                    }
                }
            ]
        }
    }
