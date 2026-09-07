-- OLE DB Source "Número local" del Data Flow "Números (Local)".
WITH
  numeros as
  (

  SELECT
    TELÉFONO [telefono]
  FROM
    [CL_ANALISIS].[dbo].[TBL_CONTACTOS_AUTORIZADOS_CHILE]
  WHERE
    TELÉFONO IS NOT NULL

    UNION

  SELECT
    MÓVIL [telefono]
  FROM
    [CL_ANALISIS].[dbo].[TBL_CONTACTOS_AUTORIZADOS_CHILE]
  WHERE
    MÓVIL IS NOT NULL
    )

SELECT
    telefono
FROM
    numeros
GROUP BY
    telefono
