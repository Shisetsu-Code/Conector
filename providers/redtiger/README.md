# Red Tiger

**Estado:** selector offline incorporado; conexión HTTP autónoma y ejecutor remoto **no validados**.

## Contenido

- `session_selector.py`: selecciona exactamente un bootstrap (config + settings) por ronda, con tableId, gameId, host HTTPS, usuario, token y sessionId opcional.
- `tests/test_session_selector.py`: pruebas sintéticas de sesiones distintas y errores de identidad.
- [Diagnóstico de acceso y conciliación](../../docs/redtiger-entry-diagnostic.md): alcance del 403/500, capturas y pendientes.

## Pruebas

Desde la raíz del repositorio:

```bash
python -m unittest discover -s providers/redtiger/tests -p "test_*.py" -v
```

No necesita paquetes de terceros ni acceso a red. Para integrar evidencia privada: normalizar cada `/config`, `/platform/game/settings` (solicitud y respuesta) y el envío financiero **original**; seleccionar el bootstrap de esa ronda; luego llamar al reconciliador nativo sin eliminar controles de saldo/premio/host/juego.

**Pendientes:** adaptador JSONL local, validación real offline del par Spin/FreeSpins:101 de Babylon Riches y resolución oficial del rechazo HTTP en `/entry`. No copiar sesiones históricas ni reanudar campañas.
