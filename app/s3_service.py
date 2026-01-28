"""
Módulo de Integração com AWS S3
Autor: Ramon Alonso
Versão: 1.0.0

Este módulo gerencia o upload de imagens para o Amazon S3,
incluindo configuração de permissões públicas e geração de URLs.
"""

import os
import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from app.config import aws_config

# Configuração de logging
logger = logging.getLogger(__name__)


class S3Service:
    """
    Serviço para gerenciamento de uploads de imagens no AWS S3.
    Suporta upload de arquivos e bytes diretamente, com geração
    automática de URLs públicas.
    """
    
    def __init__(self):
        """
        Inicializa o serviço S3 com as credenciais configuradas.
        """
        self._client = None
        self._bucket_name = aws_config.bucket_name
        self._region = aws_config.region
    
    def _get_client(self):
        """
        Obtém ou cria um cliente S3 boto3.
        
        Returns:
            boto3.client: Cliente S3 configurado
            
        Raises:
            NoCredentialsError: Se as credenciais não estiverem configuradas
        """
        if self._client is None:
            client_config = {
                "service_name": "s3",
                "region_name": self._region
            }
            
            # Adicionar credenciais se fornecidas explicitamente
            if aws_config.access_key_id and aws_config.secret_access_key:
                client_config["aws_access_key_id"] = aws_config.access_key_id
                client_config["aws_secret_access_key"] = aws_config.secret_access_key
            
            # Adicionar endpoint customizado se configurado (útil para LocalStack, MinIO, etc.)
            if aws_config.endpoint_url:
                client_config["endpoint_url"] = aws_config.endpoint_url
            
            self._client = boto3.client(**client_config)
            logger.info(f"Cliente S3 inicializado para região: {self._region}")
        
        return self._client
    
    def _generate_key(
        self, 
        prefix: str = "images",
        extension: str = "png"
    ) -> str:
        """
        Gera uma chave única para o objeto S3.
        
        Args:
            prefix: Prefixo do caminho (pasta virtual)
            extension: Extensão do arquivo
            
        Returns:
            str: Chave única no formato prefix/YYYY/MM/DD/uuid.extension
        """
        now = datetime.utcnow()
        unique_id = uuid.uuid4().hex
        
        key = f"{prefix}/{now.year}/{now.month:02d}/{now.day:02d}/{unique_id}.{extension}"
        
        return key
    
    def _get_public_url(self, key: str) -> str:
        """
        Gera a URL pública para um objeto S3.
        
        Args:
            key: Chave do objeto no S3
            
        Returns:
            str: URL pública do objeto
        """
        if aws_config.endpoint_url:
            # Para endpoints customizados (LocalStack, MinIO)
            return f"{aws_config.endpoint_url}/{self._bucket_name}/{key}"
        
        # URL padrão do S3
        return f"https://{self._bucket_name}.s3.{self._region}.amazonaws.com/{key}"
    
    async def upload_bytes(
        self,
        data: bytes,
        content_type: str = "image/png",
        prefix: str = "images",
        extension: str = "png",
        metadata: Optional[Dict[str, str]] = None,
        make_public: bool = True
    ) -> Dict[str, Any]:
        """
        Faz upload de dados binários para o S3.
        
        Args:
            data: Dados binários a serem enviados
            content_type: Tipo MIME do conteúdo
            prefix: Prefixo do caminho no S3
            extension: Extensão do arquivo
            metadata: Metadados adicionais (opcional)
            make_public: Se True, torna o objeto publicamente acessível
            
        Returns:
            Dict contendo:
                - key: Chave do objeto no S3
                - url: URL pública do objeto
                - bucket: Nome do bucket
                - size: Tamanho em bytes
                
        Raises:
            ClientError: Se houver erro no upload
            ValueError: Se o bucket não estiver configurado
        """
        if not self._bucket_name:
            raise ValueError(
                "Bucket S3 não configurado. "
                "Defina a variável de ambiente AWS_S3_BUCKET"
            )
        
        client = self._get_client()
        key = self._generate_key(prefix, extension)
        
        logger.info(f"Iniciando upload para s3://{self._bucket_name}/{key}")
        
        try:
            extra_args = {
                "ContentType": content_type
            }
            
            # Adicionar metadados se fornecidos
            if metadata:
                extra_args["Metadata"] = metadata
            
            # Configurar ACL para acesso público se solicitado
            if make_public:
                extra_args["ACL"] = "public-read"
            
            # Realizar upload
            client.put_object(
                Bucket=self._bucket_name,
                Key=key,
                Body=data,
                **extra_args
            )
            
            url = self._get_public_url(key)
            
            logger.info(f"Upload concluído: {url}")
            
            return {
                "key": key,
                "url": url,
                "bucket": self._bucket_name,
                "size": len(data),
                "content_type": content_type
            }
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(f"Erro no upload S3 ({error_code}): {str(e)}")
            raise
    
    async def upload_file(
        self,
        file_path: str,
        content_type: str = "image/png",
        prefix: str = "images",
        make_public: bool = True,
        delete_after: bool = False
    ) -> Dict[str, Any]:
        """
        Faz upload de um arquivo local para o S3.
        
        Args:
            file_path: Caminho do arquivo local
            content_type: Tipo MIME do conteúdo
            prefix: Prefixo do caminho no S3
            make_public: Se True, torna o objeto publicamente acessível
            delete_after: Se True, deleta o arquivo local após upload
            
        Returns:
            Dict com informações do upload (ver upload_bytes)
            
        Raises:
            FileNotFoundError: Se o arquivo não existir
            ClientError: Se houver erro no upload
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        
        # Extrair extensão do arquivo
        _, extension = os.path.splitext(file_path)
        extension = extension.lstrip(".")
        
        # Ler conteúdo do arquivo
        with open(file_path, "rb") as f:
            data = f.read()
        
        # Fazer upload
        result = await self.upload_bytes(
            data=data,
            content_type=content_type,
            prefix=prefix,
            extension=extension,
            make_public=make_public
        )
        
        # Deletar arquivo local se solicitado
        if delete_after:
            os.remove(file_path)
            logger.info(f"Arquivo local removido: {file_path}")
        
        return result
    
    async def delete_object(self, key: str) -> bool:
        """
        Remove um objeto do S3.
        
        Args:
            key: Chave do objeto a ser removido
            
        Returns:
            bool: True se removido com sucesso
        """
        client = self._get_client()
        
        try:
            client.delete_object(
                Bucket=self._bucket_name,
                Key=key
            )
            logger.info(f"Objeto removido: s3://{self._bucket_name}/{key}")
            return True
            
        except ClientError as e:
            logger.error(f"Erro ao remover objeto: {str(e)}")
            return False
    
    def check_connection(self) -> bool:
        """
        Verifica se a conexão com o S3 está funcionando.
        
        Returns:
            bool: True se a conexão está OK
        """
        try:
            client = self._get_client()
            client.head_bucket(Bucket=self._bucket_name)
            logger.info(f"Conexão com bucket {self._bucket_name} verificada")
            return True
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(f"Erro na verificação do bucket ({error_code}): {str(e)}")
            return False
        except NoCredentialsError:
            logger.error("Credenciais AWS não configuradas")
            return False


# Instância global do serviço S3
s3_service = S3Service()
