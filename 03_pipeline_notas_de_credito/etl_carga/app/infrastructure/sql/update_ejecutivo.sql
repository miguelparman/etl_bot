-- Homologación de nombres de EJECUTIVO en TBL_NC_DB para un período dado.
-- Migrado literalmente desde la tarea 'UPDATE' de SSIS_CL_NC.dtsx: mismo
-- mapeo y mismas condiciones por fecha, sin cambios de negocio.
-- Parámetros posicionales (pyodbc): 1) año, 2) mes.
UPDATE [CL_FACTURACION].[dbo].[TBL_NC_DB]
SET EJECUTIVO = CASE
    WHEN EJECUTIVO = 'ALICIA DEL VALLE SANCHEZ NAMIAS' THEN 'Namias Alicia Del Valle Sanchez'
    WHEN EJECUTIVO = 'KATHIA JACKELINE APOLAYA MAGALLANES' THEN 'Kathia Apolaya Magallanes'
    WHEN EJECUTIVO = 'IBETH BRENDA SOTELO CORDOVA' THEN 'Ibeth Sotelo Sotelo Cordova'
    -- Deshabilitado ya en el paquete original (comentario en el SqlStatementSource):
    -- WHEN EJECUTIVO = 'HÉCTOR GUILLERMO FERNANDO OHIGGINS ARROSPIDE' THEN 'Hector Guillermo Fernando O''Higgins Arrospide'
    WHEN EJECUTIVO = 'LUIS MIGUEL LA CHIRA NEGRON' THEN 'Negronluis Miguel La Chira'
    WHEN EJECUTIVO = 'DAYANA JULIA TORREALVA RODRIGUE' THEN 'Dayana Julia Torrealva Rodriguez'
    WHEN EJECUTIVO = 'DAMARIS ARANGUREN ARANGUREN SEQUERA' THEN 'Damaris Aranguren Sequera'
    WHEN EJECUTIVO = 'BUENO JULIO BACA DEL BUENO' THEN 'Julio Anderson Baca del Bueno'
    WHEN EJECUTIVO = 'ALICIA LEON CRUZ' THEN 'Alicia Alejandrina Leon Cruz'
    WHEN EJECUTIVO = 'JEAN PIERRE VASQUEZ BELLEZA' THEN 'Jean Pierre Antoni Vasquez Belleza'
    WHEN EJECUTIVO = 'JESUS ALEJANDRO SOMAZA MARTINEZ' THEN 'jesus somaza'
    WHEN EJECUTIVO = 'DARYAN FIGUEROA LA SERNA' THEN 'Daryan Alexandra Figueroa La Serna'
    WHEN EJECUTIVO = 'MERILYN SARMIENTO BARAZORDA' THEN 'Mérilyn Sarmiento Barazorda'
    WHEN EJECUTIVO = 'MARIA VILLASANTE ANTONLUZ' THEN 'Luz Maria Villasante Anton'
    WHEN EJECUTIVO = 'DANIELA ALEJANDRA BRICEÑO KOUKOU' THEN 'Daniela Alejandra Briceño de Kou Kou'
    WHEN EJECUTIVO = 'JJHON EDDY MORALES PEÑA' THEN 'Jhon Morales Peña'
    WHEN EJECUTIVO = 'JHON EDDY MORALES PEÑA' THEN 'Jhon Morales Peña'
    WHEN EJECUTIVO = 'EVELYN MABEL BELLIDO ESTELO' THEN 'Mabel Bellido Estelo'
    -- Deshabilitado ya en el paquete original:
    -- WHEN EJECUTIVO = 'ALEXANDRA VELÁSQUEZ RAMÓN' THEN 'ALEXANDRA RITA LUZ VELASQUEZ RAMON'
    WHEN EJECUTIVO = 'ALEXANDRA RITA LUZ VELÁSQUEZ RAMÓN' AND YEAR(FECHA_NC) >= 2025 AND MONTH(FECHA_NC) > 3 THEN 'Alexandra Velásquez Ramón'
    WHEN EJECUTIVO = 'GABRIELA RAMIREZ ARZOLA' AND YEAR(FECHA_NC) >= 2025 AND MONTH(FECHA_NC) > 3 THEN 'Dayana Gabriela Ramirez Arzola'
    WHEN EJECUTIVO = 'GABRIELA RAMIREZ ARZOLA' AND YEAR(FECHA_NC) <= 2025 AND MONTH(FECHA_NC) <= 3 THEN 'Gabriela Ramirez Arzola'
    WHEN EJECUTIVO = 'JOHANA NUÑEZ CENTENO' THEN 'Johana Nunez Centeno'
    ELSE EJECUTIVO
END
WHERE YEAR(FECHA_NC) = ?
  AND MONTH(FECHA_NC) = ?;
