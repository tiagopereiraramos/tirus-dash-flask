"""
Service para upload de arquivos no MinIO S3
"""

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
import logging
import json
import os
from datetime import datetime
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)


class MinIOService:
    """Service para gerenciar uploads no MinIO S3"""
    
    def __init__(self):
        """Inicializa conexão com MinIO usando variáveis de ambiente"""
        try:
            # Carregar credenciais de variáveis de ambiente
            access_key = os.environ.get('MINIO_ACCESS_KEY')
            secret_key = os.environ.get('MINIO_SECRET_KEY')
            endpoint_url = os.environ.get('MINIO_ENDPOINT', 'https://tirus-minio.cqojac.easypanel.host')
            
            # Validar credenciais
            if not access_key or not secret_key:
                raise ValueError(
                    "Credenciais do MinIO não configuradas. "
                    "Configure as variáveis de ambiente MINIO_ACCESS_KEY e MINIO_SECRET_KEY"
                )
            
            # Configurar cliente S3 para MinIO
            self.s3_client = boto3.client(
                's3',
                endpoint_url=endpoint_url,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=Config(signature_version='s3v4'),
                region_name='us-east-1'  # MinIO não usa region, mas boto3 requer
            )
            
            self.bucket_name = 'beg'
            self.pdf_folder = 'pdfs'
            
            logger.info(f"MinIO S3 client inicializado com endpoint: {endpoint_url}")
            
        except ValueError as e:
            logger.error(f"Erro de configuração do MinIO: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Erro ao inicializar MinIO client: {str(e)}")
            raise
    
    def upload_fatura(self, file, processo):
        """
        Faz upload de fatura para o MinIO S3
        
        Args:
            file: FileStorage object do Flask
            processo: Objeto Processo do banco de dados
            
        Returns:
            dict: Informações do upload (url, key, bucket)
        """
        try:
            # Gerar nome único para o arquivo
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = secure_filename(file.filename)
            
            # Padrão: pdfs/{operadora}/{cliente}_{ano}_{mes}_{timestamp}_{filename}
            object_key = f"{self.pdf_folder}/{processo.operadora.nome_operadora}/{processo.cliente.nome_cliente}_{processo.ano}_{processo.mes:02d}_{timestamp}_{filename}"
            
            # Upload para MinIO
            self.s3_client.upload_fileobj(
                file,
                self.bucket_name,
                object_key,
                ExtraArgs={
                    'ContentType': 'application/pdf',
                    'Metadata': {
                        'processo_id': str(processo.id_processo),
                        'cliente_id': str(processo.id_cliente),
                        'operadora_id': str(processo.id_operadora),
                        'ano': str(processo.ano),
                        'mes': str(processo.mes),
                        'uploaded_at': datetime.now().isoformat()
                    }
                }
            )
            
            # Gerar URL do arquivo
            file_url = f"{self.s3_client.meta.endpoint_url}/{self.bucket_name}/{object_key}"
            
            logger.info(f"Fatura uploaded com sucesso: {object_key}")
            
            return {
                'success': True,
                'url': file_url,
                'key': object_key,
                'bucket': self.bucket_name,
                'filename': filename
            }
            
        except ClientError as e:
            logger.error(f"Erro ao fazer upload para MinIO: {str(e)}")
            return {
                'success': False,
                'error': f"Erro no upload S3: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Erro inesperado no upload: {str(e)}")
            return {
                'success': False,
                'error': f"Erro no upload: {str(e)}"
            }
    
    def get_fatura_url(self, object_key):
        """
        Gera URL assinada para download de fatura
        
        Args:
            object_key: Chave do objeto no S3
            
        Returns:
            str: URL assinada (válida por 1 hora)
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key
                },
                ExpiresIn=3600  # 1 hora
            )
            return url
        except Exception as e:
            logger.error(f"Erro ao gerar URL assinada: {str(e)}")
            return None
    
    def delete_fatura(self, object_key):
        """
        Remove fatura do MinIO
        
        Args:
            object_key: Chave do objeto no S3
            
        Returns:
            bool: True se removido com sucesso
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            logger.info(f"Fatura removida: {object_key}")
            return True
        except Exception as e:
            logger.error(f"Erro ao remover fatura: {str(e)}")
            return False
    
    def list_faturas_processo(self, processo):
        """
        Lista todas as faturas de um processo específico
        
        Args:
            processo: Objeto Processo
            
        Returns:
            list: Lista de objetos encontrados
        """
        try:
            prefix = f"{self.pdf_folder}/{processo.operadora.nome_operadora}/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' in response:
                return response['Contents']
            return []
            
        except Exception as e:
            logger.error(f"Erro ao listar faturas: {str(e)}")
            return []
