"""
Módulo de Configuração da API HTML to Image
Autor: Ramon Alonso
Versão: 1.0.0

Este módulo contém todas as configurações necessárias para a aplicação,
incluindo credenciais AWS, configurações de renderização e parâmetros da API.
"""

import os
from pydantic import BaseModel
from typing import Optional


class AWSConfig(BaseModel):
    """
    Configurações para integração com AWS S3.
    As credenciais devem ser configuradas via variáveis de ambiente.
    """
    access_key_id: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    secret_access_key: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    region: str = os.getenv("AWS_REGION", "us-east-1")
    bucket_name: str = os.getenv("AWS_S3_BUCKET", "")
    endpoint_url: Optional[str] = os.getenv("AWS_ENDPOINT_URL", None)


class RenderConfig(BaseModel):
    """
    Configurações padrão para renderização de imagens.
    """
    default_width: int = 1024
    default_height: int = 768
    default_quality: int = 100
    default_scale: float = 1.0
    temp_dir: str = "/home/ubuntu/html-to-image-api/temp"
    max_width: int = 4096
    max_height: int = 4096


class AppConfig(BaseModel):
    """
    Configuração geral da aplicação.
    """
    app_name: str = "HTML to Image API"
    app_version: str = "1.0.0"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    log_dir: str = "/home/ubuntu/html-to-image-api/logs"
    

# Instâncias globais de configuração
aws_config = AWSConfig()
render_config = RenderConfig()
app_config = AppConfig()
