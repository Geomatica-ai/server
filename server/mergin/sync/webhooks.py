# Copyright (C) Geomatica.ai
# Webhook para notificar a la plataforma Atlas cuando un proyecto se sincroniza

import logging
import os
import requests
from .models import push_finished

logger = logging.getLogger(__name__)

WEBHOOK_URL = os.environ.get('WEBHOOK_PUSH_URL') # webhoook nofitication

def on_push_finished(sender, **kwargs):
    """Notifica a la plataforma cuando un proyecto se sincroniza."""
    try:
        project = sender.project
        payload = {
            "event": "push_finished",
            "project": project.name,
            "version": sender.name,
            "namespace": project.workspace.name,
        }
        logger.info(f"Notificando a la plataforma ({WEBHOOK_URL}): {payload}")
        resp = requests.post(WEBHOOK_URL, json=payload, timeout=10, verify=False)
        logger.info(f"Respuesta webhook: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"Error notificando a la plataforma ({WEBHOOK_URL}): {e}")

def register_webhooks():
    """Registra los handlers de webhook en las signals de Mergin."""
    if WEBHOOK_URL:
        push_finished.connect(on_push_finished)
        logger.info("Webhooks registrados correctamente")