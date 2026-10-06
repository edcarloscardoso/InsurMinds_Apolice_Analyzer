"""Módulo de Perfis de Trabalho (Personas) do InsurMinds.
Implementa a adaptação da experiência visual do usuário conforme seu perfil profissional.
"""
from ui.persona.profiles import (
    PROFILES,
    ProfileConfig,
    get_active_profile,
    set_active_profile,
    get_profile_metadata,
    filter_and_sort_differences_for_profile
)

__all__ = [
    "PROFILES",
    "ProfileConfig",
    "get_active_profile",
    "set_active_profile",
    "get_profile_metadata",
    "filter_and_sort_differences_for_profile"
]
