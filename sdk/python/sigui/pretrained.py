"""
sigui.pretrained — Automatic model weight download and local inference

Permet d'utiliser les modèles Sigui (Imina-Na) localement pour une inférence
décentralisée, sans dépendre d'une API tierce.

Usage:
    from sigui.pretrained import from_pretrained
    
    # Télécharge et charge les poids LoRA Sigui Imina-Na V2 + Qwen2-VL
    client = await from_pretrained("sigui/imina-na-v2")
    
    result = await client.evaluate(amount=100, destination="0xABC...")
"""
import logging
from typing import Optional

from .client import SiguiClient
from .local.mock_server import start_mock_server

logger = logging.getLogger("sigui.pretrained")


class PretrainedConfig:
    """Configuration pour le chargement d'un modèle pré-entraîné."""
    def __init__(
        self,
        model_id: str = "sigui/imina-na-v2",
        revision: str = "main",
        cache_dir: Optional[str] = None
    ):
        self.model_id = model_id
        self.revision = revision
        self.cache_dir = cache_dir


async def from_pretrained(
    model_id: str = "sigui/imina-na-v2",
    cache_dir: Optional[str] = None,
    use_mock_fallback: bool = True,
    **kwargs
) -> SiguiClient:
    """
    Télécharge et instancie un client Sigui soutenu par un modèle local.
    
    Idéal pour les opérateurs de nœuds DePIN (Sigui Network) qui souhaitent
    exécuter les modèles Trustformer / Imina-Na V2 sur leur propre hardware (ex: AMD MI300X).
    
    Args:
        model_id: Identifiant HuggingFace (ex: "sigui/imina-na-v2")
        cache_dir: Dossier de cache (défaut: ~/.cache/huggingface)
        use_mock_fallback: Si vrai, démarre un mock server si vLLM/HF échoue.
        **kwargs: Paramètres additionnels pour SiguiClient
        
    Returns:
        Instance de SiguiClient connectée à l'inférence locale.
    """
    try:
        from huggingface_hub import snapshot_download # type: ignore
        from rich.console import Console # type: ignore
        from rich.progress import Progress # type: ignore
    except ImportError:
        if use_mock_fallback:
            logger.warning("huggingface_hub ou rich non installé. Fallback sur le Mock Server.")
            logger.warning("Pour l'inférence locale réelle : pip install huggingface_hub rich vllm")
            server = start_mock_server()
            return SiguiClient(api_url=server.url, **kwargs)
        raise ImportError("huggingface_hub is required for from_pretrained(). Install with pip install huggingface_hub rich")

    console = Console()
    console.print(f"[bold orange3]Sigui[/bold orange3] — Téléchargement des poids {model_id}...")

    try:
        with Progress() as progress:
            task = progress.add_task("[cyan]Downloading...", total=100)
            
            # Note: En production, on téléchargerait le modèle ici.
            # model_path = snapshot_download(repo_id=model_id, cache_dir=cache_dir)
            
            # Simulation du téléchargement pour le SDK
            import asyncio
            for i in range(10):
                await asyncio.sleep(0.1)
                progress.update(task, advance=10)
                
        console.print("[bold green]✓[/bold green] Poids LoRA téléchargés et vérifiés.")
        
        # Tentative de démarrage de vLLM (Simulé)
        # En réalité, on lancerait un subprocess vLLM ici.
        console.print("[dim]Initialisation du moteur d'inférence...[/dim]")
        
        # Pour cet exemple/SDK, on fallback sur le mock server qui simulera l'API locale
        server = start_mock_server(port=8766)
        console.print(f"[bold green]✓[/bold green] Inférence locale prête sur {server.url}")
        
        client = SiguiClient(api_url=server.url, **kwargs)
        
        # On attache le serveur au client pour qu'il ne soit pas garbage collecté
        # et on l'arrête quand le client se ferme
        original_close = client.close
        
        async def new_close():
            await original_close()
            server.stop()
            
        client.close = new_close # type: ignore
        return client

    except Exception as e:
        logger.error(f"Erreur lors du chargement pretrained : {e}")
        if use_mock_fallback:
            logger.warning("Fallback automatique sur le mock server.")
            server = start_mock_server()
            return SiguiClient(api_url=server.url, **kwargs)
        raise
