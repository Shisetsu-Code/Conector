# Belatra — observación saneada del HAR (14-11-2026)

Fuente: HAR privado aportado por el usuario; su contenido completo permanece fuera de Git.

- SHA-256 del HAR original: `940b964a3ef91ff628a35f9b2ef95ee55977672c63582dd0a26733f07f925011`
- Entradas totales: **432**; respuestas HTTP **200: 401**, **301: 11**, **302: 3**, **307: 1**, **204: 6**, **status 0: 10**.
- Solicitudes al host de demo `demo.bltrm.com`: **215** (la mayoría son recursos del cliente).
- Juego de la sesión observada: `mr_ferret`, cliente `/v3/games/mr_ferret/`, idioma `es`.
- Lanzador `/belatra/demo`: **302** a documento de juego en mismo host. `Location` incluye `modification` y `sid` privados. El 302 incluye `Set-Cookie: connect.sid` (solo se registra el nombre).
- Documento raíz: **200** con parámetros `modification` y `sid`.
- `POST /user/datalist`: **200**, JSON `datatype` y `sid`; su `sid` coincide con el del documento.
- `POST /game`: **9/9 HTTP 200** y el mismo `sid` en cada cuerpo. Formulario `d` + `sid`. Las respuestas tienen `d` en JSON. Todos los `d` observados son Base64 binario, no JSON legible tras la decodificación. Los 4 bytes con offset 4 forman un timestamp Unix LE coherente con cada registro.

### Distribución observada de tamaños binarios (no son clases de apuesta)

| Solicitud (bytes) | Respuesta (bytes) | Cantidad |
|---:|---:|---:|
| 70 | 98 | 3 |
| 86 | 728 | 2 |
| 173 | 3516 | 1 |
| 187 | 3440 | 1 |
| 207 | 3494 | 1 |
| 207 | 3727 | 1 |

**Alcance real:** se valida un contrato de transporte y pertenencia a una sesión, no el contrato de acciones, el RTP ni los saldos. El tamaño de un paquete no demuestra que sea `Spin`, `Buy Bonus` o `Free Spins`.

Los recursos estáticos mencionan `buy_bonus` y se carga la interfaz del juego, pero no hay datos descifrados que permitan asociar cada paquete a una acción. Tampoco se demuestra que una operación haya sido aceptada o cerrada solo por HTTP 200. No se publicaron cuerpos, cookies, tokens, URL con `sid`, capturas HAR ni credenciales.

### Estado del conector

`providers/belatra/har_contract.py` opera sin red, exige continuidad de sesión y no reproduce transacciones. En la captura recibida completó toda la validación de transporte; las once pruebas negativas/positivas sintéticas pasaron. La integración remota, clasificación de modalidades y conciliación contable siguen pendientes.
