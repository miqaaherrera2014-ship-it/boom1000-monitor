# Monitor Boom 1000 — lectura automática de Deriv

Este proyecto contiene un **monitor sin MetaTrader** que consulta el **Boom 1000 Index** exacto a través de la API pública oficial de Deriv. Tiene un panel web que puede conectarse a ticks y velas y un recolector de GitHub Actions que publica `docs/data/latest.json` cada 15 minutos. La publicación permite que ChatGPT pueda consultar el JSON público **sin que tengas que enviar capturas**.

**Estado de verificación:** código terminado y probado con pruebas locales; la conexión real con Deriv no pudo ejecutarse desde el entorno de creación porque no tiene acceso DNS/internet. La primera ejecución en tu navegador o GitHub es la prueba real. No hay precios falsos.

## Cómo ponerlo en marcha una sola vez

1. Entrá a **https://github.com/new** con tu cuenta de GitHub. Creá un repositorio **público** llamado `boom1000-monitor` (o el nombre que elijas).
2. Subí **el contenido de esta carpeta** al repositorio manteniendo los subdirectorios `.github/workflows/`, `src/` y `docs/`. Subir el ZIP sin descomprimir no funciona.
3. En GitHub, abrí **Settings → Actions → General → Workflow permissions**, elegí **Read and write permissions** y guardá.
4. Entrá en **Actions → Actualizar Boom 1000 desde Deriv → Run workflow**, así comprobás el primer chequeo. Si falla, abrí el registro; ninguna cifra inventada se publicará.
5. En **Settings → Pages**, elegí **Deploy from a branch**, tu rama principal y directorio **/docs**. Guardá.
6. Abrí `https://TU_USUARIO.github.io/boom1000-monitor/` (cambiá `TU_USUARIO` y el nombre si corresponde). Para que yo consulte las velas a diario, mandame **una sola vez** la dirección pública `https://TU_USUARIO.github.io/boom1000-monitor/data/latest.json`.

A partir de ese momento, GitHub Actions intenta consultar la API cada **15 minutos**. No hay coste obligatorio ni contraseñas de Deriv; está sujeto a las cuotas y disponibilidad de GitHub Actions. Una tarea programada no se ejecuta exactamente a la misma hora siempre. Si el repositorio pasa a inactivo o el cron se desactiva, los datos quedarán antiguos y el panel lo indicará.

**Atención:** no subas claves privadas, contraseñas de Binance ni credenciales de Deriv. La API de datos de mercado pública no requiere tokens.

## Archivos

- `docs/index.html`: monitor visual. Abre directamente la API WebSocket en el navegador, muestra precio/hora, velas de Diario, 4H y 1H y referencias de zonas. Si falla la conexión, informa el error.
- `src/deriv_snapshot.py`: conecta al WebSocket público de Deriv, verifica que `active_symbols` corresponda **exactamente a Boom 1000 Index** y descarga hasta 140 velas por temporalidad. Descarta errores de precio/velas; si falla, no sustituye el snapshot anterior por datos inventados.
- `.github/workflows/update.yml`: ejecuta el recolector automáticamente cada 15 minutos y publica resultados con `git push`.
- `tests/test_snapshot.py`: pruebas de detección de instrumento y validación de OHLC.

## Comprobar que funciona

Cuando el sitio esté publicado, abrí `https://TU_USUARIO.github.io/boom1000-monitor/data/latest.json`. Debe contener:

- `instrument`: `Boom 1000 Index`
- `symbol`: código obtenido del listado oficial `active_symbols` (no asumido a ciegas)
- `generated_at`: hora UTC de captura
- `last_tick`: `price`, `epoch`, `utc`, si llegó un tick real
- `candles.H1`, `candles.H4`, `candles.D1`: velas OHLC con timestamp UNIX

**Hay que verificar dos tiempos**: que `generated_at` sea reciente (idealmente <40 minutos) y que `last_tick.epoch` sea reciente (idealmente <3 minutos al consultar un snapshot recién generado). El archivo puede seguir siendo accesible durante un fallo del servicio; eso **no** significa que sus precios sean actuales.

## Probar en computadora sin GitHub

Si tenés Python instalado, dentro de la carpeta del proyecto ejecutá:

```bash
python -m pip install 'websockets>=13,<17'
python -m http.server 8000 --directory docs
```

Abrí http://localhost:8000 en el navegador. El panel intenta obtener precios y velas en directo. Para generar un snapshot desde tu equipo: `python src/deriv_snapshot.py`.

## Limitaciones importantes

- **No opera**, no deposita ni retira dinero, y no da órdenes automáticas.
- Las alertas de zonas en el panel funcionan **solo con la página abierta**; los envíos push requerirían una integración adicional (por ejemplo AlertBolt o Telegram).
- Los horarios de apertura de las velas son UTC; la última vela puede estar en formación. No se debe confirmar un BOS/CDC basándose en una vela abierta.
- Los niveles son **referencias históricas** que requieren validación; la metodología IPDA/SMC se interpreta críticamente para índices sintéticos.
- Esta solución no permite a ChatGPT conectarse directamente a una red bloqueada: usa una **publicación HTTP intermedia** que sí puede leer una búsqueda web cuando esté desplegada. El enlace público debe existir antes de afirmar que la automatización funciona de extremo a extremo.
- Si Deriv cambia sus APIs, el código puede necesitar actualización.

Documentación: https://developers.deriv.com/docs/intro/api-overview/ y https://developers.deriv.com/docs/data/ticks-history/
