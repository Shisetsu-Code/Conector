# Red Tiger: reconciliación offline y frontera del launcher HTTP (2026-11-13)

## Alcance y límites

- Evidencia local de Babylon Riches: dos bootstraps de sesiones distintas y un journal con un Spin normal (líneas 1-2) y una compra FreeSpins:101 (líneas 3-4). El Spin corresponde a `bootstrap-9af25e2f-...`; la compra a `bootstrap-8086a853-...`. Ninguno de los archivos privados se publica.
- `node_family_replay.replay_case('netent', 'babylon-riches', 'Spin')` reportó `redtiger_native_game_or_session_request_changed` al aplicar un único bootstrap a todo el journal. El error de asociación **no demuestra** un fallo del contrato de la ronda.
- `provider-work/netent-root/http_modes.py`, `node_family_replay.py` y los JSONL de `netent-private-root/` no existen en el checkout publicado. El código adjunto aquí es una **pieza aislada para la futura integración local**, no una modificación de esos validadores privados.
- No se han reanudado campañas ni enviado nuevas apuestas para realizar esta corrección. Solo se validó con datos sintéticos.

## Asociación por ronda, sin relajar los controles

El módulo `providers/redtiger/session_selector.py` recibe una colección de pares de configuración y settings **previamente normalizados** y la identidad extraída del **envío real** de una ronda. Requiere coincidencia inequívoca de:

1. `table_id` del catálogo frente a `/config`.
2. `gameId` financiero frente a `base_game_id` y `gameId` de settings.
3. Host HTTPS del endpoint financiero frente a `wrappedLaunchParams.baseUrl`, y ruta exacta de settings.
4. Token nativo de la respuesta de settings frente al token del envío; nunca se usa el `token: null` de la solicitud de settings como token nativo.
5. `userId` nativo, `sessionId` cuando el protocolo lo lleve en el envío y `playMode: demo` confirmado con `success: true`.

Si no hay candidato, si hay dos candidatos o falta identidad, falla sin seleccionar nada. No se registran valores de tokens, sesiones o cookies.

**Integración local pendiente:** convertir cada par de los JSONL privados a las claves `config_response`, `settings_request` ({ `url`, `body` }) y `settings_response`. Extraer `gameId`, `userId`, `token` y `sessionId` opcional del envío financiero original. Elegir un settings por envío y, solo entonces, llamar el `reconcile_mode` original para ese par solicitud/respuesta. Mantener intactos los 11 controles, en especial saldo, premios, host y juego. No inventar un saldo inicial ni fusionar raíces de dos sesiones.

Prueba sintética portable:

```bash
python -m unittest discover -s providers/redtiger/tests -p "test_*.py" -v
```

Prueba pendiente en la PC original: los dos pares guardados deben conciliarse con sus respectivos settings; un bootstrap cruzado, incompleto o ambiguo debe fallar. No imprimir ni publicar los objetos enteros si contienen credenciales.

## Estado de acceso remoto

| Transporte/caso | Emisor | Primera entrada | Segunda entrada | Settings | Interpretación |
|---|---|---|---|---|---|
| HTTP nuevo, directo y relay | 200 | 403, sin Location ni Set-Cookie en el rechazo | No alcanzada | No alcanzado | Enlace emitido, acceso autónomo no confirmado |
| Electron nuevo aislado | 200 | 403 | No alcanzada | No alcanzado | Electron por sí solo no resuelve el acceso |
| Chromium visible, arranque exitoso | 200 | 302 | 302 hacia `/frontend/evo/r2/` | 200/demo/success | Ruta del frontend demostrada para esa sesión |
| Chromium visible, intentos posteriores | 200 | 302 (emite EVOSESSIONID) | 500 texto plano; EVOSESSIONID sí enviada | No alcanzado | Falla posterior, distinta del 403 inicial |
| Capturas HAR manuales previas | 200 | No incluido | No incluido | 200/demo/success | No se puede inferir cómo se originó la cookie |

En un HAR manual la sesión funcional también produjo un `Spin` remoto 200, pero esto no prueba que el HTTP autónomo haya funcionado. Los HAR de la sesión exitosa capturan `/setup`, `/config` y settings, pero no documentan el punto en que se emitió `EVOSESSIONID`; la ausencia de `/entry` no implica que la captura empezara tarde.

En la reproducción del 500, el segundo `/entry` recibió `EVOSESSIONID`; por tanto su ausencia no explica ese error en esa prueba. Los 403 históricos no conservan encabezados completos y no acreditan una regla concreta. No se debe simular `Location`, copiar tokens/cookies previos ni inferir el motivo de Akamai a partir de un estado HTTP.

## Siguiente ensayo permitido

Con una sesión **demo nueva**, registrar redirecciones de navegación de documento/iframe (sin el filtro `Game Only`), estado de cada salto, host, ruta, presencia de cookies por **nombre** y, si existen, `Location` y referencia de rechazo saneados. Seguir exclusivamente redirecciones reales de hosts oficiales.

El ensayo de arranque debe terminar en `POST /platform/game/settings`, exigir `playMode=demo`, `success=true`, `tableId` y `gameId` coherentes, y bloquear acciones financieras. Si hay 403 o 500, conservar etapa y estado con `remote_demo_bootstrap_http_<status>` y detenerse. La causa definitiva del acceso autónomo requiere evidencia adicional o respuesta de soporte del proveedor.
