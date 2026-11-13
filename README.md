# Conector

Conectores independientes por proveedor para investigación, reproducción **offline** y pruebas de integración autorizadas en entornos demo.

El repositorio se organiza por proveedor. **Red Tiger** es el primer módulo; cada proveedor mantendrá su propio protocolo, normalización, casos de prueba y diagnósticos, sin compartir identidades de sesión.

```text
Conector/
├── providers/
│   ├── README.md                  # Contrato común y reglas por proveedor
│   └── redtiger/
│       ├── session_selector.py    # Asociación offline ronda → bootstrap
│       ├── README.md              # Estado, uso y límites
│       └── tests/
│           └── test_session_selector.py
├── docs/
│   └── redtiger-entry-diagnostic.md
└── .github/workflows/
    └── offline-tests.yml
```

## Estado

| Proveedor | Módulo | Cobertura |
|---|---|---|
| Red Tiger | `providers/redtiger` | Asociación de sesiones y rondas offline; launcher HTTP autónomo **no validado** |

### Pruebas locales

Requiere Python 3.11+; para el selector offline no hacen falta dependencias adicionales ni acceso a red.

```bash
python -m unittest discover -s providers/redtiger/tests -p "test_*.py" -v
```

## Reglas

- Solo demos públicas/autorizadas y saldos ficticios. No reutilizar capturas, cookies, tokens ni sesiones históricas.
- Cada proveedor es dueño de sus contratos y tests; el código común no interpreta estados específicos de un proveedor.
- Separar bootstrap, validación de identidad, ejecución de rondas y conciliación de premios/saldos.
- No dar por finalizada una ronda por un simple HTTP 200. Nunca repetir automáticamente una operación incierta.
- No almacenar datos sensibles en Git: HAR, capturas crudas, URLs autenticadas, perfiles de navegador, credenciales o tokens.
- Integraciones sin navegador solo se consideran funcionales con evidencia reciente del flujo completo. No eludir restricciones de acceso del proveedor.

Este repositorio no contiene un ejecutor remoto de apuestas activo.
