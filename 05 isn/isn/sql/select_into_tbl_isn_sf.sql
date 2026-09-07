-- Tarea 'SF\TBL_ISN_SF', conexión 162.CL_ISN.
-- Los parámetros posicionales originales del .dtsx (User Fecha_inicio y
-- User Fecha_fin) se pasan acá como parámetros nombrados en el WHERE de
-- más abajo -- ver isn/pipeline.py, db.run_sql_file(..., params={...}).
-- OJO: no repetir esos nombres de parámetro en comentarios de este archivo
-- con el prefijo de dos puntos ni usar el caracter de interrogación suelto:
-- SQLAlchemy los cuenta como referencias de parámetro reales aunque estén
-- dentro de un comentario SQL, y duplica/descuadra la lista de valores.
SELECT
	ROW_NUMBER() OVER(PARTITION BY x0.[Número del caso] ORDER BY x0.[Número del caso], x0.[ANI]) ORDEN
	,x0.*
	,CASE
		WHEN [RUT YA ENCUESTADO] IS NOT NULL THEN 'CLIENTE ENCUESTADO'
		WHEN SUB_SEGMENTO IS NULL THEN 'NO SE ENCUENTRA EN CARTERA'
		WHEN [ESTADO PRESENTACION] ='PRESENTACION SM' THEN 'PRESENTACION SM'
		WHEN SUB_SEGMENTO LIKE '%TRIADA%' THEN 'CLIENTE DE TRIADA'
		WHEN [Programa Responsable] NOT LIKE '%Carterizado%' THEN 'PROGRAMA RESPONSABLE DIFERENTE A CARTERIZADOS'
		WHEN [GRUPO DOMINIO] = 'INTERNO' THEN 'CORREO INTERNO'
		WHEN [CODIGO CIERRE ASEGURADO] IS NOT NULL THEN 'NO AMERITA CIERRE ASEGURADO'
		WHEN [RUT SM CARTERA] IS NULL THEN 'SM SIN RUT'
		--WHEN [DNI ASESOR<30 DIAS] IS NOT NULL THEN 'ASESOR MENOR A 30 DIAS DE GESTION'
		WHEN [Tipo del Caso Final] like '%PADRE%' THEN 'CASO PADRE'
		WHEN [OJT PLACE] IS NOT NULL THEN 'CONEXION OJT'
		WHEN Asunto LIKE '%PRUEBA%' THEN 'CASOS DE PRUEBA CALIDAD'
		--WHEN [CLIENTE CON RECLAMO] IS NOT NULL THEN 'CLIENTE DETRACTOR DEFINIDO POR CALIDAD'
		WHEN [Correo Electrónico Contacto] LIKE '%fractalia%' THEN 'CORREO DE CONTACTO FRACTALIA'
		WHEN ANI = '' OR ANI IS NULL  THEN  'SIN IV'
		ELSE NULL
	END [MOTIVO DE RETIRO]
INTO
	[CL_ISN].[dbo].[TBL_ISN_SF]
FROM
(
SELECT
	CASE
		WHEN x0.[Fecha/hora de resolución] IS NULL AND x0.[Fecha/Hora de cierre] IS NULL THEN CAST(x0.[Fecha/Hora de apertura] AS DATE )
		ELSE CAST(x0.[Fecha de cierre general] AS DATE )
	END [FECHA]
	,CASE
		WHEN x0.[Fecha/hora de resolución] IS NULL AND x0.[Fecha/Hora de cierre] IS NULL THEN CAST( CAST(x0.[Fecha/Hora de apertura] AS TIME ) AS varchar(8))
		ELSE CAST( CAST(x0.[Fecha de cierre general] AS TIME ) AS varchar(8))
	END [HORA]
	--	CAST(x0.[Fecha de cierre general] AS DATE ) [FECHA]
	--,CAST( CAST(x0.[Fecha de cierre general] AS TIME ) AS varchar(8)) [HORA]
	--,x3.[ID_GENESYS_SM_TITULAR] [LOGINID]
	,x3.[COD_DNI] [COD_DNI SM CARTERA]
	,x3.RUT_SM_TITULAR [RUT SM CARTERA]
	,x3.NOM_SM_TITULAR [NOMBRE SM CARTERA]
	,x0.[Fecha de cierre general]
	,x0.[Fecha/Hora de apertura]
	,x0.[Número del caso]
	,x0.[Estado]
	,x0.[Estado general]
	,x0.[No. identificación fiscal]
	,x0.[Vista final]
	,x0.Origen
	,x0.[Programa Responsable]
	,x0.[Asesor Responsable DNI]
	,x0.[Asesor responsable]
	,x0.[Coordinador responsable]
	,x0.[Correo Electrónico Contacto]
	,x0.[Teléfono Contacto]
	,x0.[Teléfono Móvil Contacto]
	,x0.[Correo Electronico Web]
	,x1.[MÓVIL] [Teléfono Móvil Correo electrónico web]
	,x2.[TELÉFONO] [Teléfono Fijo Correo electrónico web]
	,x0.Asunto
	--,CASE
	--	WHEN Origen = 'Email2case' and [Correo Electronico Web] = [Correo Electrónico Contacto] AND [Teléfono Móvil Contacto]<>'' THEN [Teléfono Móvil Contacto]
	--	WHEN Origen = 'Email2case' and [Correo Electronico Web] = [Correo Electrónico Contacto] AND [Teléfono Contacto]<>'' THEN [Teléfono Contacto]
	--	WHEN Origen = 'Email2case' and [Teléfono Contacto] = '' and [Teléfono Móvil Contacto] = '' AND x1.MÓVIL = x2.TELÉFONO THEN x1.MÓVIL
	--	WHEN Origen = 'Email2case' and [Teléfono Contacto] = '' and [Teléfono Móvil Contacto] = '' AND x1.MÓVIL <>'' THEN x1.MÓVIL
	--	WHEN Origen = 'Email2case' and [Teléfono Contacto] = '' and [Teléfono Móvil Contacto] = '' AND x2.TELÉFONO <>'' THEN x2.TELÉFONO
	--	WHEN [Teléfono Móvil Contacto] <> '' THEN [Teléfono Móvil Contacto]
	--	ELSE [Teléfono Contacto]
	--END [ANI]
	,CASE
		WHEN Origen = 'Email2case' and [Correo Electronico Web] = [Correo Electrónico Contacto] AND [Teléfono Móvil Contacto]<>'' THEN [Teléfono Móvil Contacto]
		WHEN Origen = 'Email2case' and [Correo Electronico Web] = [Correo Electrónico Contacto] AND [Teléfono Contacto]<>'' THEN [Teléfono Contacto]
		WHEN Origen = 'Email2case' AND x1.MÓVIL = x2.TELÉFONO THEN x1.MÓVIL
		WHEN Origen = 'Email2case' and x1.MÓVIL Is not null THEN x1.MÓVIL
		WHEN Origen = 'Email2case' and x2.TELÉFONO Is not null THEN x2.TELÉFONO
		WHEN Origen = 'Email2case' and x1.MÓVIL Is NULL and x2.TELÉFONO Is NULL  THEN ''
		WHEN [Teléfono Móvil Contacto] <> '' THEN [Teléfono Móvil Contacto]
		ELSE [Teléfono Contacto]
	END [ANI]
	,x3.[SUB_SEGMENTO]
	,x3.[NOMBRE_CLIENTE]
	,x3.[SEGMENTO]
	,x8.rut [RUT YA ENCUESTADO]
	,x9.cod_dni [DNI ASESOR<30 DIAS]
	,x10.PLACE_ID [OJT PLACE]
	,x11.[No. identificación fiscal] [CLIENTE CON PENDIENTE]
	--,x12.[RUT_ID_CUSTOMER] [CLIENTE CON RECLAMO]
	,'' [CLIENTE CON RECLAMO]
	,x13.RUT [CLIENTE DETRACTOR CALIDAD]
	,x0.Origen [BASE]
	,x0.[GRUPO DOMINIO]
	,x0.[ESTADO PRESENTACION]
	--Agregado 23-07-2024
	,x0.Sector
	,x0.[Segmento Global]
	,x0.[Subsegmento local]
	,x0.[Nombre de contacto]
	,x0.[Territorio]
	,CASE
		WHEN x14.[REPRESENTANTE LEGAL] IS NULL THEN 'False'
		ELSE 'True'
	END REPRESENTANTE_LEGAL
	,x15.[Id  del cliente]
	,x15.Subsector
	,x15.[Rango de trabajadores]
	,x15.[Categoria Heredada]
	,x15.[Descripción del negocio]
	,x16.[Id  de contacto]
	,x17.[ID Usuario] [ID_PROPIETARIO]
	,x17.Permisos [PERMISO_EJEC]
	,x17.Cargo [CARGO_EJEC]
	,x0.[Propietario del caso] [NOMBRE_EJEC]
	,x0.[Tipo del Caso Final]
	,x18.codigo [CODIGO CIERRE ASEGURADO]
FROM
	(
	SELECT
		 x0.[No. identificación fiscal]
		,x0.[Fecha/Hora de apertura]
		,x0.[Fecha de cierre general]
		,x0.[Número del caso]
		,x0.[Asesor Responsable DNI]
		,x0.[CREADO POR]
		,x0.[Vista final]
		,x0.[Programa Responsable]
		,x0.[Estado]
		,x0.[Estado general]
		,x0.[Asesor responsable]
		,x0.[Correo Electronico Web]
		,x0.[Correo Electrónico Contacto]
		,x0.[Teléfono Contacto]
		,x0.[Móvil Contacto] [Teléfono Móvil Contacto]
		,x0.[GRUPO DOMINIO]
		,x0.[Origen]
		,x3.[des_apellido_nombres] [Coordinador Responsable]
		,x0.[Tipología]
		,x0.[Subtipología]
		,x0.[Asunto]
		,x0.[ESTADO PRESENTACION]
		--Agregado 23-07-2024
		,x0.Sector
		,x0.[Segmento Global]
		,x0.[Subsegmento local]
		,x0.[Nombre de contacto]
		,x0.[Territorio]
		,x0.[Propietario del caso]
		,x0.[Fecha/hora de resolución]
		,x0.[Fecha/Hora de cierre]
		,x0.[Tipo del Caso Final]
	FROM
		[CL_VISTAS].[dbo].[VIEW_FACT_SEGUIMIENTO_VOL_GENERAL] x0
	LEFT JOIN
		[CL_VISTAS].[dbo].[VIEW_COD_DNI_UNICOS] x3
	ON
		x3.[cod_dni] = x0.[Coordinador Responsable DNI]
	WHERE
		cast(x0.[Fecha de cierre general] as date) BETWEEN :fecha_inicio AND :fecha_fin
		AND x0.[Vista final] = 'Carterizados'
		AND Origen IN ('Chat/WhatsApp','Email2case','Llamada','Correo')
		AND [Estado general] =  'Finalizado'
		--revisar
		--AND ([Fecha/hora de resolución] IS NOT NULL
		--OR [Fecha/Hora de cierre] IS NOT NULL)
	)x0
LEFT JOIN
	[CL_ANALISIS].[dbo].[VIEW_CONTACTOS_AUTORIZADOS_CHILE_RUC_CORREO_MOVIL] x1 WITH (NOLOCK)
ON
	x1.[RUC] = X0.[No. identificación fiscal]
	AND x1.[CORREO ELECTRÓNICO] = x0.[Correo Electronico Web]
LEFT JOIN
	[CL_ANALISIS].[dbo].[VIEW_CONTACTOS_AUTORIZADOS_CHILE_RUC_CORREO_TELÉFONO] x2 WITH (NOLOCK)
ON
	x2.[RUC] = X0.[No. identificación fiscal]
	AND x2.[CORREO ELECTRÓNICO] = x0.[Correo Electronico Web]
LEFT JOIN
	[CL_CARTERA].[dbo].[TBL_CARTERA_ACTUAL] x3 WITH (NOLOCK)
ON
	x3.[RUT_SIN_DV] = x0.[No. identificación fiscal]
LEFT JOIN
	[CL_CALIDAD].[dbo].[VIEW_ISN_ENVIOS_CONSOLIDADO_CLIENTES_ENCUESTADO_RANGO_MES] x8
ON
	x8.RUT = X0.[No. identificación fiscal]
LEFT JOIN
	[CL_VISTAS].[dbo].[VIEW_BASEGENERAL_CONSOLIDADO_ASESOR_MENOR_30DIAS] x9
ON
	x9.cod_dni = x0.[Asesor Responsable DNI]
LEFT JOIN
	[CL_ISN].[dbo].[TBL_ISN_OJT] x10
ON
	x10.PLACE_ID = x3.ID_GENESYS_SM_TITULAR
	and x10.FECHA = CAST(x0.[Fecha/Hora de apertura] AS DATE )
LEFT JOIN
	[CL_VISTAS].[dbo].[VIEW_CLIENTES_PENDIENTES_MAYOR_2_MESES] x11 WITH (NOLOCK)
ON
	x11.[No. identificación fiscal] = X0.[No. identificación fiscal]
--LEFT JOIN
--	[CL_MOVIL].[dbo].[VIEW_RECLAMOS_REITERADOS_CLIENTES_ULTIMO_PERIODO] x12
--ON
--	x12.RUT_ID_CUSTOMER = x0.[No. identificación fiscal]
LEFT JOIN
	[CL_ISN].[dbo].[TBL_CLIENTES_DETRACTORES_CALIDAD] x13
ON
	x13.[RUT] = X0.[No. identificación fiscal]
--AGREGDO 23-07-2024
LEFT JOIN
	[CL_ANALISIS].[dbo].[VIEW_SF_CCAA_REPRESENTANTE_LEGAL_UNICO] x14
ON
	x14.RUC = x0.[No. identificación fiscal]
	AND x14.[CORREO ELECTRÓNICO] = x0.[Correo Electrónico Contacto]
LEFT JOIN
	[CL_ISN].[dbo].[TBL_ISN_SF_AUX_CLIENTE] x15
ON
	x15.[Número del caso] = x0.[Número del caso]
LEFT JOIN
	[CL_ISN].[dbo].[TBL_ISN_SF_AUX_CONTACTO] x16
ON
	x16.[Número del caso] = x0.[Número del caso]
LEFT JOIN
	[BBDD_GENERAL].[dbo].[TBL_SALESFORCE_USUARIOS_UNICOS] x17
ON
	x17.[Usuario Salesforce] = x0.[Propietario del caso]
--AGREGADI 16-06-2024 PEDIDO KISSVHAN
LEFT JOIN
	(
	SELECT
		[Número del caso]
		,codigo
	FROM
		[CL_VISTAS].[dbo].[VIEW_MOTIVO_CIERRE_ASEGURADO]
	WHERE
	codigo IN ('[1173]','[1174]')
	)x18
ON
	x18.[Número del caso] = x0.[Número del caso]
)x0
