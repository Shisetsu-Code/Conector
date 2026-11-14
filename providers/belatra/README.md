# Belatra — conector de contrato offline

**Estado:** análisis y validación estructural del HAR de demo realizados. **No** hay ejecutor remoto ni serializador de apuestas operativo.

## Evidencia

La captura privada del 14 de noviembre de 2026 corresponde a `mr_ferret` (Mr. Ferret Heist), idioma `es`, y contiene:

| Paso | Método y ruta | Resultado |
|---|---|---|
| Lanzador público | `GET https://demo.bltrm.com/belatra/demo?game=<game>&language=<lang>` | 302 con `Location` oficial |
| Documento del juego | `GET https://demo.bltrm.com/?modification=...&sid=...` | 200 |
| Datos auxiliares | `POST https://demo.bltrm.com/user/datalist` | 200, JSON con `datatype` y `sid` |
| Transporte nativo | `POST https://demo.bltrm.com/game` | 9 respuestas 200; cuerpo `application/x-www-form-urlencoded` con `d` y `sid` |

La respuesta de `/game` es JSON `{"d":"<base64>"}`. El Base64 codifica datos binarios opacos. En los ejemplos guardados, los bytes 4–7 contienen un timestamp Unix little-endian coherente con el instante del envío. **No** se ha demostrado el esquema del resto del contenido.

El 302 del lanzador emite una cookie llamada `connect.sid`; los valores de sesión y cookies son privados y no se versionan. Los nueve `POST /game` y `/user/datalist` emplean el mismo `sid` que el documento de juego. El HAR también carga recursos de interfaz `buy_bonus`, pero esto **no acredita** que alguna llamada `/game` sea una compra de bonus.

## Implementación

`har_contract.py` comprueba offline:

- Host HTTPS oficial, ruta del lanzador y destino de la redirección observada.
- Coherencia exacta de la sesión del documento, `/user/datalist` y cada `/game`.
- Métodos, códigos de estado, Content-Type y formato de las envolturas de solicitud/respuesta.
- Base64 válido y timestamp binario de los paquetes con tolerancia de 5 minutos.
- Resumen estructural saneado, sin imprimir URLs autenticadas, cuerpos, tokens ni cookies.

Uso en la PC local, con el HAR **fuera del repositorio**:

```bash
python -m providers.belatra.har_contract "/ruta/privada/captura.har"
python -m unittest discover -s providers/belatra/tests -p "test_*.py" -v
```

No hace solicitudes de red ni genera giros. El validador no puede confirmar premios, cambios de saldo, clasificación de modos o liquidación mientras el protocolo binario nativo no esté interpretado y verificado con evidencia independiente.

## Pendiente

1. Identificar documentalmente el serializador nativo del cliente oficial y el contrato de `/game` (sin reutilizar sesiones de esta captura).
2. Clasificar de forma comprobable las operaciones de inicio, normal, apuesta especial, compra, continuación y cierre; no deducirlas por el tamaño del paquete.
3. Integrar bootstrap de sesión demo fresca con seguimiento de redirecciones y bloqueos, sin enviar acciones financieras en la prueba inicial.
4. Incorporar conciliación independiente de coste, premio, saldo y cierre; llevar journal durable y no repetir acciones inciertas.
5. Ejecutar pruebas remotas autorizadas solo después de verificar que el modo es de saldo ficticio.

Ver [diagnóstico de la captura](../../docs/belatra-har-observation.md).
