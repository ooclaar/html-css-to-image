"""
Módulo de Renderização HTML para Imagem
Autor: Ramon Alonso
Versão: 1.0.0

Este módulo utiliza o Playwright para renderizar conteúdo HTML/CSS
em imagens PNG de alta qualidade usando um navegador headless.
"""

import asyncio
import os
import uuid
import logging
from typing import Optional, Tuple
from playwright.async_api import async_playwright, Browser, Page

from app.config import render_config

# Configuração de logging
logger = logging.getLogger(__name__)


class HTMLRenderer:
    """
    Classe responsável por renderizar HTML/CSS em imagens PNG.
    Utiliza Playwright com Chromium headless para garantir
    renderização fiel e suporte completo a CSS moderno.
    """
    
    def __init__(self):
        """
        Inicializa o renderizador com as configurações padrão.
        """
        self._browser: Optional[Browser] = None
        self._playwright = None
        self.temp_dir = render_config.temp_dir
        
        # Garantir que o diretório temporário existe
        os.makedirs(self.temp_dir, exist_ok=True)
    
    async def _get_browser(self) -> Browser:
        """
        Obtém ou cria uma instância do navegador Chromium.
        Reutiliza a mesma instância para melhor performance.
        
        Returns:
            Browser: Instância do navegador Chromium
        """
        if self._browser is None or not self._browser.is_connected():
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--font-render-hinting=none'
                ]
            )
            logger.info("Navegador Chromium iniciado com sucesso")
        return self._browser
    
    async def close(self):
        """
        Fecha o navegador e libera recursos.
        Deve ser chamado ao encerrar a aplicação.
        """
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("Navegador encerrado")
    
    def _validate_dimensions(
        self, 
        width: int, 
        height: int
    ) -> Tuple[int, int]:
        """
        Valida e ajusta as dimensões da imagem dentro dos limites permitidos.
        
        Args:
            width: Largura desejada em pixels
            height: Altura desejada em pixels
            
        Returns:
            Tuple[int, int]: Dimensões validadas (largura, altura)
        """
        validated_width = max(1, min(width, render_config.max_width))
        validated_height = max(1, min(height, render_config.max_height))
        
        if validated_width != width or validated_height != height:
            logger.warning(
                f"Dimensões ajustadas de {width}x{height} para "
                f"{validated_width}x{validated_height}"
            )
        
        return validated_width, validated_height
    
    def _build_html_document(
        self, 
        html_content: str, 
        css_content: Optional[str] = None
    ) -> str:
        """
        Constrói um documento HTML completo com o CSS incorporado.
        
        Args:
            html_content: Conteúdo HTML a ser renderizado
            css_content: Estilos CSS opcionais
            
        Returns:
            str: Documento HTML completo
        """
        css_block = ""
        if css_content:
            css_block = f"<style>{css_content}</style>"
        
        # Verificar se o HTML já é um documento completo
        if "<html" in html_content.lower() or "<!doctype" in html_content.lower():
            # Inserir CSS no head se já for documento completo
            if css_content:
                if "<head>" in html_content.lower():
                    html_content = html_content.replace(
                        "</head>", 
                        f"{css_block}</head>", 
                        1
                    )
                else:
                    html_content = html_content.replace(
                        "<html>", 
                        f"<html><head>{css_block}</head>", 
                        1
                    )
            return html_content
        
        # Construir documento HTML completo
        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    {css_block}
</head>
<body style="margin: 0; padding: 0;">
    {html_content}
</body>
</html>"""
    
    async def render_to_image(
        self,
        html_content: str,
        css_content: Optional[str] = None,
        width: int = None,
        height: int = None,
        scale: float = None,
        full_page: bool = False,
        transparent: bool = False
    ) -> bytes:
        """
        Renderiza conteúdo HTML/CSS em uma imagem PNG.
        
        Args:
            html_content: Conteúdo HTML a ser renderizado
            css_content: Estilos CSS opcionais
            width: Largura da viewport em pixels (padrão: 1024)
            height: Altura da viewport em pixels (padrão: 768)
            scale: Fator de escala do dispositivo (padrão: 1.0)
            full_page: Se True, captura a página inteira
            transparent: Se True, usa fundo transparente
            
        Returns:
            bytes: Dados da imagem PNG
            
        Raises:
            Exception: Se houver erro na renderização
        """
        # Aplicar valores padrão
        width = width or render_config.default_width
        height = height or render_config.default_height
        scale = scale or render_config.default_scale
        
        # Validar dimensões
        width, height = self._validate_dimensions(width, height)
        
        logger.info(
            f"Iniciando renderização: {width}x{height}, escala: {scale}, "
            f"full_page: {full_page}, transparent: {transparent}"
        )
        
        try:
            browser = await self._get_browser()
            
            # Criar nova página com as dimensões especificadas
            page = await browser.new_page(
                viewport={"width": width, "height": height},
                device_scale_factor=scale
            )
            
            # Construir documento HTML completo
            full_html = self._build_html_document(html_content, css_content)
            
            # Carregar o conteúdo HTML
            await page.set_content(full_html, wait_until="networkidle")
            
            # Aguardar um momento para garantir renderização completa
            await asyncio.sleep(0.1)
            
            # Capturar screenshot
            screenshot_options = {
                "type": "png",
                "full_page": full_page
            }
            
            if transparent:
                screenshot_options["omit_background"] = True
            
            image_bytes = await page.screenshot(**screenshot_options)
            
            # Fechar a página
            await page.close()
            
            logger.info(
                f"Renderização concluída: {len(image_bytes)} bytes"
            )
            
            return image_bytes
            
        except Exception as e:
            logger.error(f"Erro na renderização: {str(e)}")
            raise
    
    async def render_to_file(
        self,
        html_content: str,
        css_content: Optional[str] = None,
        output_path: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Renderiza conteúdo HTML/CSS e salva em um arquivo PNG.
        
        Args:
            html_content: Conteúdo HTML a ser renderizado
            css_content: Estilos CSS opcionais
            output_path: Caminho do arquivo de saída (opcional)
            **kwargs: Argumentos adicionais para render_to_image
            
        Returns:
            str: Caminho do arquivo gerado
        """
        # Gerar nome de arquivo se não fornecido
        if not output_path:
            filename = f"{uuid.uuid4().hex}.png"
            output_path = os.path.join(self.temp_dir, filename)
        
        # Renderizar imagem
        image_bytes = await self.render_to_image(
            html_content, 
            css_content, 
            **kwargs
        )
        
        # Salvar arquivo
        with open(output_path, "wb") as f:
            f.write(image_bytes)
        
        logger.info(f"Imagem salva em: {output_path}")
        
        return output_path


# Instância global do renderizador
renderer = HTMLRenderer()
