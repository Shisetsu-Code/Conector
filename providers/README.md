# Contrato de conectores por proveedor

Cada integración reside en `providers/<slug>/` y tiene propiedad exclusiva sobre su protocolo. Un proveedor nuevo no puede reutilizar los tokens, cookies, saldos, juegos o sesiones de otro proveedor.

## Responsabilidades

1. **Catálogo:** identificar el juego mediante la clave oficial de catálogo y los modos publicados. Sin códigos generados por suposición.
2. **Bootstrap:** abrir una sesión *demo nueva* por el flujo público autorizado; validar host y cada redirección real. Registrar el estado del acceso sin intentar saltar restricciones.
3. **Identidad:** vincular cada ronda a la respuesta de `settings`/configuración de su propia sesión. Fallar si faltan campos o existen dos candidatos.
4. **Modos:** distinguir normal, ante, compra de bonus y continuaciones. Usar solamente opciones anunciadas por el protocolo.
5. **Ejecución:** persistir la intención antes de una acción con efectos; no repetir una solicitud de resultado incierto.
6. **Conciliación:** comprobar juego, sesión, coste, premios nativos, saldo y estado de cierre. El transport/HTTP 200 no es liquidación.
7. **Diagnóstico:** exponer errores de etapa y respuesta saneados, nunca tokens, cookies ni URLs autenticadas.

## Convenciones de directorios

```text
providers/<slug>/
  README.md                   # Estado real y comandos de prueba
  ...                         # Adaptador/protocolo específicos del proveedor
  tests/                      # Fixtures sintéticos u offline sin secretos
```

El *selector offline* de Red Tiger es un componente de validación, no un launcher operativo. No tiene red y debe integrarse más tarde con el reconciliador nativo. Preferir Rust para nuevos ejecutores cuando aporte valor, manteniendo las interfaces específicas de cada proveedor explícitas.
