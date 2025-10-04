from pydantic import BaseModel, Field
from typing import List, Optional

class ProductData(BaseModel):
    """
    Schema for the structured output of the product analysis LLM.
    """
    product_name: str = Field(description="Nome de e-commerce conciso e otimizado para o produto.")
    category_standard: str = Field(description="Categoria de alto nível do produto (ex: 'Eletrônicos', 'Alimentos', 'Vestuário').")
    description_long: str = Field(description="Descrição rica em detalhes, materiais e benefícios, com no mínimo 50 palavras.")
    features_list: List[str] = Field(description="Uma lista de três a cinco características ou 'selling points' principais do produto.")

class TaskTicket(BaseModel):
    """
    Schema for the response sent to the client after a task is submitted.
    """
    task_id: str
    status: str = "PENDING"

class TaskStatus(BaseModel):
    """
    Schema for the status check response.
    """
    task_id: str
    status: str
    result: Optional[ProductData] = None
    error: Optional[str] = None
