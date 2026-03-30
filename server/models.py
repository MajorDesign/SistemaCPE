"""
Modelos Pydantic para validação de dados da API.
"""
from pydantic import BaseModel, EmailStr

class UserLogin(BaseModel):
    """Modelo para os dados de entrada do login."""
    email: EmailStr  # Valida automaticamente se é um email válido
    password: str